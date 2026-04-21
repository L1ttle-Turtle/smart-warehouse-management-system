import pytest

from app.extensions import db
from app.models import Permission, User, UserPermissionDelegation


@pytest.mark.parametrize(
    ("username", "password", "expected_role"),
    [
        ("admin", "Admin@123", "admin"),
        ("manager", "Manager@123", "manager"),
        ("staff", "Staff@123", "staff"),
        ("accountant", "Accountant@123", "accountant"),
        ("shipper", "Shipper@123", "shipper"),
    ],
)
def test_login_returns_token_and_user_by_role(client, username, password, expected_role):
    response = client.post(
        "/auth/login",
        json={"username": username, "password": password},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["access_token"]
    assert payload["user"]["username"] == username
    assert payload["user"]["role"] == expected_role


def test_login_rejects_invalid_credentials(client):
    response = client.post(
        "/auth/login",
        json={"username": "admin", "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.get_json()["message"] == "Sai tên đăng nhập hoặc mật khẩu."


def test_me_returns_current_user(client, auth_headers):
    response = client.get("/auth/me", headers=auth_headers())

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["user"]["role"] == "admin"
    assert "roles.view" in payload["user"]["permissions"]


def test_me_requires_token(client):
    response = client.get("/auth/me")

    assert response.status_code == 401


def test_profile_updates_contact_information(client, auth_headers, app):
    response = client.patch(
        "/auth/profile",
        headers=auth_headers("staff", "Staff@123"),
        json={"email": "staff.updated@example.com", "phone": "0911222333"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["user"]["email"] == "staff.updated@example.com"
    assert payload["user"]["phone"] == "0911222333"

    with app.app_context():
        staff_user = User.query.filter_by(username="staff").first()
        assert staff_user.email == "staff.updated@example.com"
        assert staff_user.phone == "0911222333"


def test_profile_can_change_password_with_current_password(client, auth_headers):
    response = client.patch(
        "/auth/profile",
        headers=auth_headers("staff", "Staff@123"),
        json={"current_password": "Staff@123", "new_password": "Staff@456!"},
    )

    assert response.status_code == 200
    assert response.get_json()["user"]["must_change_password"] is False

    login_response = client.post(
        "/auth/login",
        json={"username": "staff", "password": "Staff@456!"},
    )
    assert login_response.status_code == 200


def test_profile_rejects_wrong_current_password(client, auth_headers):
    response = client.patch(
        "/auth/profile",
        headers=auth_headers("staff", "Staff@123"),
        json={"current_password": "Wrong@123", "new_password": "Staff@456!"},
    )

    assert response.status_code == 400
    assert response.get_json()["message"] == "Mật khẩu hiện tại không chính xác."


def test_profile_rejects_weak_password(client, auth_headers):
    response = client.patch(
        "/auth/profile",
        headers=auth_headers("staff", "Staff@123"),
        json={"current_password": "Staff@123", "new_password": "weak"},
    )

    assert response.status_code == 422


def test_lowest_role_cannot_effectively_receive_delegation_manage_permission(client, auth_headers, app):
    with app.app_context():
        admin_user = User.query.filter_by(username="admin").first()
        staff_user = User.query.filter_by(username="staff").first()
        delegation_manage = Permission.query.filter_by(permission_name="delegations.manage").first()
        forced_delegation = UserPermissionDelegation(
            grantor_user_id=admin_user.id,
            grantor_role_id=admin_user.role_id,
            target_user_id=staff_user.id,
            target_role_id=staff_user.role_id,
            permission_id=delegation_manage.id,
        )
        db.session.add(forced_delegation)
        db.session.commit()

    response = client.post(
        "/auth/login",
        json={"username": "staff", "password": "Staff@123"},
    )

    assert response.status_code == 200
    assert "delegations.manage" not in response.get_json()["user"]["permissions"]
