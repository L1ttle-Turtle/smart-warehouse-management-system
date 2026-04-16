from app.models import Permission, Role, User


def test_admin_can_view_role_matrix(client, auth_headers):
    response = client.get("/roles", headers=auth_headers("admin", "Admin@123"))

    assert response.status_code == 200
    payload = response.get_json()
    assert len(payload["items"]) == 5
    admin_role = next(item for item in payload["items"] if item["role_name"] == "admin")
    assert "roles.view" in admin_role["effective_permissions"]
    assert "delegations.manage" in admin_role["effective_permissions"]


def test_non_privileged_user_cannot_view_role_matrix(client, auth_headers):
    response = client.get("/roles", headers=auth_headers("manager", "Manager@123"))

    assert response.status_code == 403


def test_admin_can_delegate_roles_view_to_manager(client, auth_headers, app):
    with app.app_context():
        manager_user = User.query.filter_by(username="manager").first()
        roles_view = Permission.query.filter_by(permission_name="roles.view").first()
        manager_id = manager_user.id
        permission_id = roles_view.id

    response = client.post(
        "/delegations",
        headers=auth_headers("admin", "Admin@123"),
        json={"target_user_id": manager_id, "permission_id": permission_id, "note": "Cho phép xem ma trận quyền"},
    )

    assert response.status_code == 201
    payload = response.get_json()["item"]
    assert payload["target_username"] == "manager"
    assert payload["permission_name"] == "roles.view"
    assert payload["grantor_user_name"] == "Admin"

    manager_roles_response = client.get("/roles", headers=auth_headers("manager", "Manager@123"))
    assert manager_roles_response.status_code == 200


def test_user_cannot_delegate_permission_they_do_not_have(client, auth_headers, app):
    with app.app_context():
        staff_user = User.query.filter_by(username="staff").first()
        roles_view = Permission.query.filter_by(permission_name="roles.view").first()
        target_user_id = staff_user.id
        permission_id = roles_view.id

    response = client.post(
        "/delegations",
        headers=auth_headers("manager", "Manager@123"),
        json={"target_user_id": target_user_id, "permission_id": permission_id},
    )

    assert response.status_code == 403
    assert "ủy quyền những quyền mà mình đang có" in response.get_json()["message"]


def test_cannot_delegate_delegation_manage_to_lowest_role_user(client, auth_headers, app):
    with app.app_context():
        staff_user = User.query.filter_by(username="staff").first()
        delegation_manage = Permission.query.filter_by(permission_name="delegations.manage").first()

    response = client.post(
        "/delegations",
        headers=auth_headers("admin", "Admin@123"),
        json={"target_user_id": staff_user.id, "permission_id": delegation_manage.id},
    )

    assert response.status_code == 400
    assert "không thể nhận quyền ủy quyền" in response.get_json()["message"]


def test_admin_can_revoke_delegation(client, auth_headers, app):
    with app.app_context():
        manager_user = User.query.filter_by(username="manager").first()
        roles_view = Permission.query.filter_by(permission_name="roles.view").first()

    create_response = client.post(
        "/delegations",
        headers=auth_headers("admin", "Admin@123"),
        json={"target_user_id": manager_user.id, "permission_id": roles_view.id},
    )
    delegation_id = create_response.get_json()["item"]["id"]

    delete_response = client.delete(
        f"/delegations/{delegation_id}",
        headers=auth_headers("admin", "Admin@123"),
    )

    assert delete_response.status_code == 200
    assert delete_response.get_json()["message"] == "Thu hồi ủy quyền thành công."

    manager_roles_response = client.get("/roles", headers=auth_headers("manager", "Manager@123"))
    assert manager_roles_response.status_code == 403


def test_meta_returns_manageable_roles_for_manager(client, auth_headers):
    response = client.get("/delegations/meta", headers=auth_headers("manager", "Manager@123"))

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["grantor"]["role_name"] == "manager"
    target_role_names = {role["role_name"] for role in payload["target_roles"]}
    assert target_role_names == {"shipper", "staff"}


def test_delegation_audit_returns_selected_user_history(client, auth_headers, app):
    with app.app_context():
        manager_user = User.query.filter_by(username="manager").first()
        roles_view = Permission.query.filter_by(permission_name="roles.view").first()

    create_response = client.post(
        "/delegations",
        headers=auth_headers("admin", "Admin@123"),
        json={"target_user_id": manager_user.id, "permission_id": roles_view.id},
    )
    assert create_response.status_code == 201

    response = client.get(
        f"/delegations?target_user_id={manager_user.id}",
        headers=auth_headers("admin", "Admin@123"),
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["items"][0]["target_username"] == "manager"
    assert payload["items"][0]["permission_name"] == "roles.view"


def test_delegation_user_search_filters_by_role_and_keyword(client, auth_headers, app):
    with app.app_context():
        manager_role = Role.query.filter_by(role_name="manager").first()

    response = client.get(
        f"/delegations/users?role_id={manager_role.id}&search=manager&page=1&page_size=10",
        headers=auth_headers("admin", "Admin@123"),
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["total"] == 1
    assert payload["items"][0]["username"] == "manager"
    assert payload["items"][0]["role_name"] == "manager"


def test_delegation_user_search_blocks_unmanageable_role(client, auth_headers, app):
    with app.app_context():
        admin_role = Role.query.filter_by(role_name="admin").first()

    response = client.get(
        f"/delegations/users?role_id={admin_role.id}",
        headers=auth_headers("manager", "Manager@123"),
    )

    assert response.status_code == 403
    assert "vai trò cấp dưới" in response.get_json()["message"]
