from app.models import (
    AuditLog,
    ImportReceipt,
    ImportReceiptDetail,
    Inventory,
    InventoryMovement,
    Product,
    Supplier,
    Warehouse,
    WarehouseLocation,
)


def get_seed_import_context(app):
    with app.app_context():
        warehouse = Warehouse.query.filter_by(warehouse_code="WH001").first()
        supplier = Supplier.query.filter_by(supplier_code="SUP001").first()
        product = Product.query.filter_by(product_code="PRD002").first()
        other_location = WarehouseLocation.query.filter_by(
            warehouse_id=warehouse.id,
            location_code="B-01",
        ).first()
        foreign_location = WarehouseLocation.query.join(Warehouse).filter(
            Warehouse.warehouse_code == "WH002",
            WarehouseLocation.location_code == "A-01",
        ).first()
        inventory_row = Inventory.query.filter_by(
            warehouse_id=warehouse.id,
            location_id=other_location.id,
            product_id=product.id,
        ).first()
        return {
            "warehouse_id": warehouse.id,
            "supplier_id": supplier.id,
            "product_id": product.id,
            "location_id": other_location.id,
            "foreign_location_id": foreign_location.id,
            "starting_quantity": inventory_row.quantity,
            "starting_total": product.quantity_total,
        }


def test_seed_demo_contains_draft_import_receipt(app):
    with app.app_context():
        receipt = ImportReceipt.query.filter_by(receipt_code="IMP-DEMO-001").first()

        assert receipt is not None
        assert receipt.status == "draft"
        assert len(receipt.details) == 2


def test_staff_can_create_and_confirm_import_receipt_and_inventory_increases(client, auth_headers, app):
    context = get_seed_import_context(app)

    create_response = client.post(
        "/import-receipts",
        headers=auth_headers("staff", "Staff@123"),
        json={
            "warehouse_id": context["warehouse_id"],
            "supplier_id": context["supplier_id"],
            "note": "Nhap them may in nhiet",
            "items": [
                {
                    "product_id": context["product_id"],
                    "location_id": context["location_id"],
                    "quantity": 5,
                },
            ],
        },
    )

    assert create_response.status_code == 201
    receipt_id = create_response.get_json()["item"]["id"]
    assert create_response.get_json()["item"]["status"] == "draft"

    confirm_response = client.post(
        f"/import-receipts/{receipt_id}/confirm",
        headers=auth_headers("staff", "Staff@123"),
    )

    assert confirm_response.status_code == 200
    assert confirm_response.get_json()["item"]["status"] == "confirmed"

    with app.app_context():
        inventory_row = Inventory.query.filter_by(
            warehouse_id=context["warehouse_id"],
            location_id=context["location_id"],
            product_id=context["product_id"],
        ).first()
        product = Product.query.filter_by(id=context["product_id"]).first()
        movement = InventoryMovement.query.filter_by(
            reference_type="import_receipt",
            reference_id=receipt_id,
        ).first()

        assert inventory_row.quantity == context["starting_quantity"] + 5
        assert product.quantity_total == context["starting_total"] + 5
        assert movement is not None
        assert movement.movement_type == "import"
        assert movement.quantity_change == 5
        assert movement.quantity_after == context["starting_quantity"] + 5


def test_import_receipt_permission_matrix(client, auth_headers):
    manager_response = client.get("/import-receipts", headers=auth_headers("manager", "Manager@123"))
    staff_response = client.get("/import-receipts", headers=auth_headers("staff", "Staff@123"))
    accountant_response = client.get("/import-receipts", headers=auth_headers("accountant", "Accountant@123"))
    shipper_response = client.get("/import-receipts", headers=auth_headers("shipper", "Shipper@123"))

    assert manager_response.status_code == 200
    assert staff_response.status_code == 200
    assert accountant_response.status_code == 403
    assert shipper_response.status_code == 403


def test_import_receipt_rejects_location_outside_warehouse(client, auth_headers, app):
    context = get_seed_import_context(app)

    response = client.post(
        "/import-receipts",
        headers=auth_headers("admin", "Admin@123"),
        json={
            "warehouse_id": context["warehouse_id"],
            "supplier_id": context["supplier_id"],
            "items": [
                {
                    "product_id": context["product_id"],
                    "location_id": context["foreign_location_id"],
                    "quantity": 3,
                },
            ],
        },
    )

    assert response.status_code == 400


def test_import_receipt_list_supports_pagination_search_and_status(client, auth_headers):
    response = client.get(
        "/import-receipts?page=1&page_size=10&search=IMP-DEMO-001&status=draft",
        headers=auth_headers("admin", "Admin@123"),
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["page"] == 1
    assert payload["page_size"] == 10
    assert payload["total"] >= 1
    assert any(item["receipt_code"] == "IMP-DEMO-001" for item in payload["items"])


def test_confirmed_import_receipt_cannot_be_confirmed_or_edited_again(client, auth_headers, app):
    context = get_seed_import_context(app)

    create_response = client.post(
        "/import-receipts",
        headers=auth_headers("admin", "Admin@123"),
        json={
            "warehouse_id": context["warehouse_id"],
            "supplier_id": context["supplier_id"],
            "items": [
                {
                    "product_id": context["product_id"],
                    "location_id": context["location_id"],
                    "quantity": 2,
                },
            ],
        },
    )
    receipt_id = create_response.get_json()["item"]["id"]

    first_confirm = client.post(
        f"/import-receipts/{receipt_id}/confirm",
        headers=auth_headers("admin", "Admin@123"),
    )
    second_confirm = client.post(
        f"/import-receipts/{receipt_id}/confirm",
        headers=auth_headers("admin", "Admin@123"),
    )
    update_response = client.put(
        f"/import-receipts/{receipt_id}",
        headers=auth_headers("admin", "Admin@123"),
        json={
            "warehouse_id": context["warehouse_id"],
            "supplier_id": context["supplier_id"],
            "items": [
                {
                    "product_id": context["product_id"],
                    "location_id": context["location_id"],
                    "quantity": 9,
                },
            ],
        },
    )

    assert first_confirm.status_code == 200
    assert second_confirm.status_code == 400
    assert update_response.status_code == 400


def test_draft_import_receipt_can_be_cancelled_without_inventory_change(client, auth_headers, app):
    context = get_seed_import_context(app)

    create_response = client.post(
        "/import-receipts",
        headers=auth_headers("admin", "Admin@123"),
        json={
            "warehouse_id": context["warehouse_id"],
            "supplier_id": context["supplier_id"],
            "note": "Phieu nhap sai can huy",
            "items": [
                {
                    "product_id": context["product_id"],
                    "location_id": context["location_id"],
                    "quantity": 7,
                },
            ],
        },
    )
    assert create_response.status_code == 201
    receipt_id = create_response.get_json()["item"]["id"]

    cancel_response = client.post(
        f"/import-receipts/{receipt_id}/cancel",
        headers=auth_headers("admin", "Admin@123"),
    )
    confirm_response = client.post(
        f"/import-receipts/{receipt_id}/confirm",
        headers=auth_headers("admin", "Admin@123"),
    )
    update_response = client.put(
        f"/import-receipts/{receipt_id}",
        headers=auth_headers("admin", "Admin@123"),
        json={
            "warehouse_id": context["warehouse_id"],
            "supplier_id": context["supplier_id"],
            "items": [
                {
                    "product_id": context["product_id"],
                    "location_id": context["location_id"],
                    "quantity": 9,
                },
            ],
        },
    )

    assert cancel_response.status_code == 200
    assert cancel_response.get_json()["item"]["status"] == "cancelled"
    assert confirm_response.status_code == 400
    assert update_response.status_code == 400

    with app.app_context():
        inventory_row = Inventory.query.filter_by(
            warehouse_id=context["warehouse_id"],
            location_id=context["location_id"],
            product_id=context["product_id"],
        ).first()
        product = Product.query.filter_by(id=context["product_id"]).first()
        movement = InventoryMovement.query.filter_by(
            reference_type="import_receipt",
            reference_id=receipt_id,
        ).first()
        audit_log = AuditLog.query.filter_by(
            action="import_receipts.cancelled",
            entity_id=receipt_id,
        ).first()

        assert inventory_row.quantity == context["starting_quantity"]
        assert product.quantity_total == context["starting_total"]
        assert movement is None
        assert audit_log is not None


def test_import_receipt_create_update_confirm_write_audit_log(client, auth_headers, app):
    context = get_seed_import_context(app)

    create_response = client.post(
        "/import-receipts",
        headers=auth_headers("admin", "Admin@123"),
        json={
            "warehouse_id": context["warehouse_id"],
            "supplier_id": context["supplier_id"],
            "note": "Phieu nhap audit",
            "items": [
                {
                    "product_id": context["product_id"],
                    "location_id": context["location_id"],
                    "quantity": 4,
                },
            ],
        },
    )
    assert create_response.status_code == 201
    receipt_id = create_response.get_json()["item"]["id"]

    update_response = client.put(
        f"/import-receipts/{receipt_id}",
        headers=auth_headers("admin", "Admin@123"),
        json={
            "warehouse_id": context["warehouse_id"],
            "supplier_id": context["supplier_id"],
            "note": "Phieu nhap audit cap nhat",
            "items": [
                {
                    "product_id": context["product_id"],
                    "location_id": context["location_id"],
                    "quantity": 6,
                },
            ],
        },
    )
    assert update_response.status_code == 200

    confirm_response = client.post(
        f"/import-receipts/{receipt_id}/confirm",
        headers=auth_headers("admin", "Admin@123"),
    )
    assert confirm_response.status_code == 200

    with app.app_context():
        actions = {
            log.action
            for log in AuditLog.query.filter(
                AuditLog.action.in_(
                    [
                        "import_receipts.created",
                        "import_receipts.updated",
                        "import_receipts.confirmed",
                    ]
                )
            ).all()
        }

    assert actions == {
        "import_receipts.created",
        "import_receipts.updated",
        "import_receipts.confirmed",
    }
