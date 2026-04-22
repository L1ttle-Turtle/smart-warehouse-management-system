from app.models import AuditLog, Category


def get_category_id(app, category_name="Dien tu"):
    with app.app_context():
        category = Category.query.filter_by(category_name=category_name).first()
        return category.id


def test_admin_can_list_products(client, auth_headers):
    response = client.get("/products", headers=auth_headers("admin", "Admin@123"))

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["page"] == 1
    assert payload["page_size"] == 10
    assert payload["total"] >= 2
    assert isinstance(payload["items"], list)


def test_admin_can_create_update_delete_product(client, auth_headers, app):
    category_id = get_category_id(app)

    create_response = client.post(
        "/products",
        headers=auth_headers("admin", "Admin@123"),
        json={
            "product_code": "PRD099",
            "product_name": "May doc test",
            "category_id": category_id,
            "min_stock": 7,
            "status": "active",
            "description": "San pham dung cho test product module",
        },
    )
    assert create_response.status_code == 201
    item_id = create_response.get_json()["item"]["id"]

    update_response = client.put(
        f"/products/{item_id}",
        headers=auth_headers("admin", "Admin@123"),
        json={
            "product_name": "May doc test cap nhat",
            "status": "inactive",
            "min_stock": 3,
        },
    )
    assert update_response.status_code == 200

    delete_response = client.delete(
        f"/products/{item_id}",
        headers=auth_headers("admin", "Admin@123"),
    )
    assert delete_response.status_code == 200


def test_manager_can_manage_products_but_staff_only_views(client, auth_headers, app):
    category_id = get_category_id(app)

    manager_create = client.post(
        "/products",
        headers=auth_headers("manager", "Manager@123"),
        json={
            "product_code": "PRD120",
            "product_name": "San pham manager tao",
            "category_id": category_id,
            "min_stock": 4,
            "status": "active",
        },
    )
    staff_list = client.get("/products", headers=auth_headers("staff", "Staff@123"))
    staff_create = client.post(
        "/products",
        headers=auth_headers("staff", "Staff@123"),
        json={
            "product_code": "PRD121",
            "product_name": "Staff khong duoc tao",
            "category_id": category_id,
            "min_stock": 2,
            "status": "active",
        },
    )
    accountant_list = client.get("/products", headers=auth_headers("accountant", "Accountant@123"))
    shipper_list = client.get("/products", headers=auth_headers("shipper", "Shipper@123"))

    assert manager_create.status_code == 201
    assert staff_list.status_code == 200
    assert staff_create.status_code == 403
    assert accountant_list.status_code == 403
    assert shipper_list.status_code == 403


def test_product_list_supports_search_status_and_category_filter(client, auth_headers, app):
    category_id = get_category_id(app, "Van phong pham")

    client.post(
        "/products",
        headers=auth_headers("admin", "Admin@123"),
        json={
            "product_code": "PRD130",
            "product_name": "Giay in kho",
            "category_id": category_id,
            "min_stock": 12,
            "status": "inactive",
            "description": "Vat tu danh cho kho van phong pham",
        },
    )

    response = client.get(
        f"/products?page=1&page_size=10&search=Giay in kho&status=inactive&category_id={category_id}&sort_by=product_code&sort_order=asc",
        headers=auth_headers("admin", "Admin@123"),
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["total"] >= 1
    assert any(item["product_code"] == "PRD130" for item in payload["items"])
    assert all(item["status"] == "inactive" for item in payload["items"])
    assert all(item["category_id"] == category_id for item in payload["items"])


def test_product_duplicate_code_and_invalid_category_return_error(client, auth_headers):
    duplicate_response = client.post(
        "/products",
        headers=auth_headers("admin", "Admin@123"),
        json={
            "product_code": "PRD001",
            "product_name": "Bi trung ma",
            "category_id": 1,
            "min_stock": 1,
            "status": "active",
        },
    )
    invalid_category_response = client.post(
        "/products",
        headers=auth_headers("admin", "Admin@123"),
        json={
            "product_code": "PRD140",
            "product_name": "Sai nhom hang",
            "category_id": 9999,
            "min_stock": 1,
            "status": "active",
        },
    )

    assert duplicate_response.status_code == 409
    assert invalid_category_response.status_code == 400


def test_product_create_update_delete_writes_audit_log(client, auth_headers, app):
    category_id = get_category_id(app)

    create_response = client.post(
        "/products",
        headers=auth_headers("admin", "Admin@123"),
        json={
            "product_code": "PRD150",
            "product_name": "San pham audit",
            "category_id": category_id,
            "min_stock": 8,
            "status": "active",
        },
    )
    assert create_response.status_code == 201
    item_id = create_response.get_json()["item"]["id"]

    update_response = client.put(
        f"/products/{item_id}",
        headers=auth_headers("admin", "Admin@123"),
        json={"product_name": "San pham audit cap nhat"},
    )
    assert update_response.status_code == 200

    delete_response = client.delete(
        f"/products/{item_id}",
        headers=auth_headers("admin", "Admin@123"),
    )
    assert delete_response.status_code == 200

    with app.app_context():
        actions = {
            log.action
            for log in AuditLog.query.filter(
                AuditLog.action.in_(
                    [
                        "products.created",
                        "products.updated",
                        "products.deleted",
                    ]
                )
            ).all()
        }

    assert actions == {
        "products.created",
        "products.updated",
        "products.deleted",
    }
