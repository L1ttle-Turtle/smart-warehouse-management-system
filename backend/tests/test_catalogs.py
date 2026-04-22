import pytest

from app.extensions import db
from app.models import AuditLog, BankAccount, Category, Customer, Supplier


RESOURCE_FIXTURES = {
    "/categories": {
        "payload": {
            "category_name": "Linh kien",
            "description": "Danh muc linh kien may tinh",
        },
        "update": {
            "category_name": "Linh kien cap nhat",
            "description": "Danh muc cap nhat",
        },
        "duplicate_payload": {
            "category_name": "Dien tu",
            "description": "Bi trung",
        },
        "audit_prefix": "categories",
        "model": Category,
        "label_field": "category_name",
    },
    "/suppliers": {
        "payload": {
            "supplier_code": "SUP099",
            "supplier_name": "Nha cung cap Moi",
            "email": "supplier.new@example.com",
            "phone": "0903333333",
            "address": "99 Ly Thuong Kiet",
            "status": "active",
        },
        "update": {
            "supplier_name": "Nha cung cap Moi Cap Nhat",
            "status": "inactive",
        },
        "duplicate_payload": {
            "supplier_code": "SUP001",
            "supplier_name": "Bi trung",
            "status": "active",
        },
        "audit_prefix": "suppliers",
        "model": Supplier,
        "label_field": "supplier_name",
    },
    "/customers": {
        "payload": {
            "customer_code": "CUS099",
            "customer_name": "Khach hang Moi",
            "email": "customer.new@example.com",
            "phone": "0913333333",
            "address": "10 Nguyen Hue",
            "status": "active",
        },
        "update": {
            "customer_name": "Khach hang Moi Cap Nhat",
            "status": "inactive",
        },
        "duplicate_payload": {
            "customer_code": "CUS001",
            "customer_name": "Bi trung",
            "status": "active",
        },
        "audit_prefix": "customers",
        "model": Customer,
        "label_field": "customer_name",
    },
    "/bank-accounts": {
        "payload": {
            "bank_name": "Techcombank",
            "account_number": "1122334455",
            "account_holder": "Cong ty ABC",
            "branch": "Chi nhanh Binh Thanh",
            "status": "active",
        },
        "update": {
            "branch": "Chi nhanh Thu Duc",
            "status": "inactive",
        },
        "duplicate_payload": {
            "bank_name": "VCB",
            "account_number": "0123456789",
            "account_holder": "Bi trung",
            "status": "active",
        },
        "audit_prefix": "bank_accounts",
        "model": BankAccount,
        "label_field": "account_number",
    },
}


@pytest.mark.parametrize("endpoint", ["/categories", "/suppliers", "/customers", "/bank-accounts"])
def test_admin_can_list_catalog_resources(client, auth_headers, endpoint):
    response = client.get(endpoint, headers=auth_headers("admin", "Admin@123"))

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["page"] == 1
    assert payload["page_size"] == 10
    assert payload["total"] >= 1
    assert isinstance(payload["items"], list)


@pytest.mark.parametrize("endpoint", ["/categories", "/suppliers", "/customers", "/bank-accounts"])
def test_admin_can_create_update_delete_catalog_resources(client, auth_headers, endpoint):
    fixture = RESOURCE_FIXTURES[endpoint]

    create_response = client.post(
        endpoint,
        headers=auth_headers("admin", "Admin@123"),
        json=fixture["payload"],
    )
    assert create_response.status_code == 201
    item_id = create_response.get_json()["item"]["id"]

    update_response = client.put(
        f"{endpoint}/{item_id}",
        headers=auth_headers("admin", "Admin@123"),
        json=fixture["update"],
    )
    assert update_response.status_code == 200

    delete_response = client.delete(
        f"{endpoint}/{item_id}",
        headers=auth_headers("admin", "Admin@123"),
    )
    assert delete_response.status_code == 200


@pytest.mark.parametrize(
    ("username", "password", "endpoint", "expected_status"),
    [
        ("manager", "Manager@123", "/categories", 200),
        ("manager", "Manager@123", "/suppliers", 200),
        ("manager", "Manager@123", "/customers", 200),
        ("manager", "Manager@123", "/bank-accounts", 403),
        ("accountant", "Accountant@123", "/customers", 200),
        ("accountant", "Accountant@123", "/bank-accounts", 200),
        ("accountant", "Accountant@123", "/categories", 403),
        ("accountant", "Accountant@123", "/suppliers", 403),
        ("staff", "Staff@123", "/customers", 403),
        ("shipper", "Shipper@123", "/suppliers", 403),
    ],
)
def test_catalog_permissions_match_role_matrix(client, auth_headers, username, password, endpoint, expected_status):
    response = client.get(endpoint, headers=auth_headers(username, password))
    assert response.status_code == expected_status


@pytest.mark.parametrize(
    ("username", "password", "endpoint"),
    [
        ("manager", "Manager@123", "/bank-accounts"),
        ("accountant", "Accountant@123", "/categories"),
        ("accountant", "Accountant@123", "/suppliers"),
        ("staff", "Staff@123", "/customers"),
        ("shipper", "Shipper@123", "/bank-accounts"),
    ],
)
def test_unauthorized_roles_cannot_create_catalog_record(client, auth_headers, username, password, endpoint):
    response = client.post(
        endpoint,
        headers=auth_headers(username, password),
        json=RESOURCE_FIXTURES[endpoint]["payload"],
    )

    assert response.status_code == 403


def test_supplier_list_supports_server_side_pagination_search_and_status_filter(client, auth_headers, app):
    with app.app_context():
        for index in range(3):
            db.session.add(
                Supplier(
                    supplier_code=f"SUP1{index}",
                    supplier_name=f"Loc Supplier {index}",
                    email=f"loc-supplier-{index}@example.com",
                    phone=f"09055555{index}",
                    address="Test address",
                    status="active" if index < 2 else "inactive",
                )
            )
        db.session.commit()

    response = client.get(
        "/suppliers?page=1&page_size=2&search=Loc Supplier&status=active&sort_by=supplier_code&sort_order=asc",
        headers=auth_headers("admin", "Admin@123"),
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["page"] == 1
    assert payload["page_size"] == 2
    assert payload["total"] == 2
    assert len(payload["items"]) == 2
    assert all(item["status"] == "active" for item in payload["items"])


@pytest.mark.parametrize("endpoint", ["/categories", "/suppliers", "/customers", "/bank-accounts"])
def test_catalog_unique_fields_return_conflict(client, auth_headers, endpoint):
    response = client.post(
        endpoint,
        headers=auth_headers("admin", "Admin@123"),
        json=RESOURCE_FIXTURES[endpoint]["duplicate_payload"],
    )

    assert response.status_code == 409


@pytest.mark.parametrize("endpoint", ["/categories", "/suppliers", "/customers", "/bank-accounts"])
def test_catalog_create_update_delete_writes_audit_log(client, auth_headers, app, endpoint):
    fixture = RESOURCE_FIXTURES[endpoint]

    create_response = client.post(
        endpoint,
        headers=auth_headers("admin", "Admin@123"),
        json=fixture["payload"],
    )
    assert create_response.status_code == 201
    item = create_response.get_json()["item"]
    item_id = item["id"]

    update_response = client.put(
        f"{endpoint}/{item_id}",
        headers=auth_headers("admin", "Admin@123"),
        json=fixture["update"],
    )
    assert update_response.status_code == 200

    delete_response = client.delete(
        f"{endpoint}/{item_id}",
        headers=auth_headers("admin", "Admin@123"),
    )
    assert delete_response.status_code == 200

    with app.app_context():
        actions = {
            log.action
            for log in AuditLog.query.filter(
                AuditLog.action.in_(
                    [
                        f"{fixture['audit_prefix']}.created",
                        f"{fixture['audit_prefix']}.updated",
                        f"{fixture['audit_prefix']}.deleted",
                    ]
                )
            ).all()
        }

    assert actions == {
        f"{fixture['audit_prefix']}.created",
        f"{fixture['audit_prefix']}.updated",
        f"{fixture['audit_prefix']}.deleted",
    }
