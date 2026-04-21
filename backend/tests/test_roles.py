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


def test_admin_can_create_custom_role_and_use_it_for_user(client, auth_headers):
    role_response = client.post(
        "/roles",
        headers=auth_headers("admin", "Admin@123"),
        json={"role_name": "Giám sát kho"},
    )

    assert role_response.status_code == 201
    role_payload = role_response.get_json()["item"]
    assert role_payload["role_name"] == "Giám sát kho"
    assert "dashboard.view" in role_payload["effective_permissions"]

    user_response = client.post(
        "/users",
        headers=auth_headers("admin", "Admin@123"),
        json={
            "username": "giam_sat_kho",
            "password": "Custom@123",
            "full_name": "Giám sát kho",
            "email": "giam_sat_kho@warehouse.local",
            "role_id": role_payload["id"],
            "status": "active",
        },
    )

    assert user_response.status_code == 201
    assert user_response.get_json()["item"]["role"] == "Giám sát kho"

    login_response = client.post(
        "/auth/login",
        json={"username": "giam_sat_kho", "password": "Custom@123"},
    )
    assert login_response.status_code == 200


def test_create_custom_role_rejects_duplicate_name(client, auth_headers):
    headers = auth_headers("admin", "Admin@123")
    first_response = client.post("/roles", headers=headers, json={"role_name": "Giám sát kho"})
    duplicate_response = client.post("/roles", headers=headers, json={"role_name": " giám sát kho "})

    assert first_response.status_code == 201
    assert duplicate_response.status_code == 409


def test_manager_cannot_create_custom_role(client, auth_headers):
    response = client.post(
        "/roles",
        headers=auth_headers("manager", "Manager@123"),
        json={"role_name": "Điều phối ca"},
    )

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
    assert payload["status"] == "active"

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
    assert delete_response.get_json()["item"]["status"] == "revoked"

    manager_roles_response = client.get("/roles", headers=auth_headers("manager", "Manager@123"))
    assert manager_roles_response.status_code == 403


def test_admin_can_delegate_with_expiration(client, auth_headers, app):
    with app.app_context():
        manager_user = User.query.filter_by(username="manager").first()
        roles_view = Permission.query.filter_by(permission_name="roles.view").first()

    response = client.post(
        "/delegations",
        headers=auth_headers("admin", "Admin@123"),
        json={
            "target_user_id": manager_user.id,
            "permission_id": roles_view.id,
            "expires_at": "2099-01-01T10:00:00",
        },
    )

    assert response.status_code == 201
    assert response.get_json()["item"]["expires_at"] is not None


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


def test_expired_or_revoked_delegation_can_be_reactivated(client, auth_headers, app):
    with app.app_context():
        manager_user = User.query.filter_by(username="manager").first()
        roles_view = Permission.query.filter_by(permission_name="roles.view").first()

    create_response = client.post(
        "/delegations",
        headers=auth_headers("admin", "Admin@123"),
        json={"target_user_id": manager_user.id, "permission_id": roles_view.id},
    )
    delegation_id = create_response.get_json()["item"]["id"]

    revoke_response = client.delete(
        f"/delegations/{delegation_id}",
        headers=auth_headers("admin", "Admin@123"),
    )
    assert revoke_response.status_code == 200

    reactivate_response = client.post(
        "/delegations",
        headers=auth_headers("admin", "Admin@123"),
        json={"target_user_id": manager_user.id, "permission_id": roles_view.id},
    )

    assert reactivate_response.status_code == 201
    assert reactivate_response.get_json()["item"]["id"] == delegation_id
    assert reactivate_response.get_json()["item"]["status"] == "active"


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
