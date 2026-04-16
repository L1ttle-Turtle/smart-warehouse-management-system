from app.extensions import db
from app.models import Employee, Role, User


def test_admin_can_list_users(client, auth_headers):
    response = client.get("/users", headers=auth_headers("admin", "Admin@123"))

    assert response.status_code == 200
    payload = response.get_json()
    assert len(payload["items"]) >= 5
    assert any(item["username"] == "admin" for item in payload["items"])


def test_admin_can_create_user(client, auth_headers, app):
    with app.app_context():
        manager_role = Role.query.filter_by(role_name="manager").first()

    response = client.post(
        "/users",
        headers=auth_headers("admin", "Admin@123"),
        json={
            "username": "manager2",
            "full_name": "Manager Two",
            "email": "manager2@example.com",
            "phone": "0901234567",
            "role_id": manager_role.id,
            "status": "active",
            "password": "Manager2@123",
        },
    )

    assert response.status_code == 201
    payload = response.get_json()["item"]
    assert payload["username"] == "manager2"
    assert payload["role"] == "manager"


def test_manager_cannot_create_user(client, auth_headers, app):
    with app.app_context():
        staff_role = Role.query.filter_by(role_name="staff").first()

    response = client.post(
        "/users",
        headers=auth_headers("manager", "Manager@123"),
        json={
            "username": "staff2",
            "full_name": "Staff Two",
            "email": "staff2@example.com",
            "role_id": staff_role.id,
        },
    )

    assert response.status_code == 403


def test_manager_can_create_employee_with_unlinked_user(client, auth_headers, app):
    with app.app_context():
        shipper_user = User.query.filter_by(username="shipper").first()
        shipper_employee = Employee.query.filter_by(user_id=shipper_user.id).first()

    unlink_response = client.put(
        f"/employees/{shipper_employee.id}",
        headers=auth_headers("admin", "Admin@123"),
        json={"user_id": None},
    )
    assert unlink_response.status_code == 200

    response = client.post(
        "/employees",
        headers=auth_headers("manager", "Manager@123"),
        json={
            "employee_code": "EMP999",
            "user_id": shipper_user.id,
            "full_name": "Shipper Support",
            "department": "Van hanh",
            "position": "Shipper",
            "email": "shipper-support@example.com",
            "status": "active",
        },
    )

    assert response.status_code == 201
    payload = response.get_json()["item"]
    assert payload["employee_code"] == "EMP999"
    assert payload["username"] == "shipper"


def test_cannot_link_one_user_to_multiple_employees(client, auth_headers, app):
    with app.app_context():
        admin_user = User.query.filter_by(username="admin").first()

    response = client.post(
        "/employees",
        headers=auth_headers("admin", "Admin@123"),
        json={
            "employee_code": "EMP777",
            "user_id": admin_user.id,
            "full_name": "Admin Clone",
            "department": "Quan tri",
            "position": "Admin",
            "status": "active",
        },
    )

    assert response.status_code == 409
    assert "đã được liên kết" in response.get_json()["message"]


def test_cannot_delete_user_when_employee_is_linked(client, auth_headers, app):
    with app.app_context():
        manager_user = User.query.filter_by(username="manager").first()

    response = client.delete(f"/users/{manager_user.id}", headers=auth_headers("admin", "Admin@123"))

    assert response.status_code == 400
    assert "đang liên kết với hồ sơ nhân sự" in response.get_json()["message"]


def test_directory_users_returns_active_accounts(client, auth_headers):
    response = client.get("/directory/users", headers=auth_headers("manager", "Manager@123"))

    assert response.status_code == 200
    payload = response.get_json()
    assert any(item["username"] == "staff" for item in payload["items"])


def test_employee_delete_removes_record_only(client, auth_headers, app):
    with app.app_context():
        shipper_user = User.query.filter_by(username="shipper").first()
        shipper_employee = Employee.query.filter_by(user_id=shipper_user.id).first()

    response = client.delete(f"/employees/{shipper_employee.id}", headers=auth_headers("admin", "Admin@123"))
    assert response.status_code == 200

    with app.app_context():
        deleted_employee = db.session.get(Employee, shipper_employee.id)
        shipper_user = User.query.filter_by(username="shipper").first()
        assert deleted_employee is None
        assert shipper_user is not None
