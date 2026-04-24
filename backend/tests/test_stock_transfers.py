from app.models import (
    AuditLog,
    Inventory,
    InventoryMovement,
    Product,
    StockTransfer,
    Warehouse,
    WarehouseLocation,
)


def get_seed_transfer_context(app):
    with app.app_context():
        source_warehouse = Warehouse.query.filter_by(warehouse_code="WH001").first()
        target_warehouse = Warehouse.query.filter_by(warehouse_code="WH002").first()
        product = Product.query.filter_by(product_code="PRD001").first()
        source_location = WarehouseLocation.query.filter_by(
            warehouse_id=source_warehouse.id,
            location_code="A-01",
        ).first()
        target_location = WarehouseLocation.query.filter_by(
            warehouse_id=target_warehouse.id,
            location_code="A-01",
        ).first()
        source_inventory = Inventory.query.filter_by(
            warehouse_id=source_warehouse.id,
            location_id=source_location.id,
            product_id=product.id,
        ).first()
        target_inventory = Inventory.query.filter_by(
            warehouse_id=target_warehouse.id,
            location_id=target_location.id,
            product_id=product.id,
        ).first()
        return {
            "source_warehouse_id": source_warehouse.id,
            "target_warehouse_id": target_warehouse.id,
            "product_id": product.id,
            "source_location_id": source_location.id,
            "target_location_id": target_location.id,
            "starting_source_quantity": source_inventory.quantity,
            "starting_target_quantity": target_inventory.quantity,
            "starting_total": product.quantity_total,
        }


def test_seed_demo_contains_draft_stock_transfer(app):
    with app.app_context():
        transfer = StockTransfer.query.filter_by(transfer_code="TRF-DEMO-001").first()

        assert transfer is not None
        assert transfer.status == "draft"
        assert len(transfer.details) == 1


def test_staff_can_create_and_confirm_stock_transfer_between_warehouses(client, auth_headers, app):
    context = get_seed_transfer_context(app)

    create_response = client.post(
        "/stock-transfers",
        headers=auth_headers("staff", "Staff@123"),
        json={
            "source_warehouse_id": context["source_warehouse_id"],
            "target_warehouse_id": context["target_warehouse_id"],
            "note": "Dieu chuyen may quet sang kho mien nam",
            "items": [
                {
                    "product_id": context["product_id"],
                    "source_location_id": context["source_location_id"],
                    "target_location_id": context["target_location_id"],
                    "quantity": 4,
                },
            ],
        },
    )

    assert create_response.status_code == 201
    transfer_id = create_response.get_json()["item"]["id"]
    assert create_response.get_json()["item"]["status"] == "draft"

    confirm_response = client.post(
        f"/stock-transfers/{transfer_id}/confirm",
        headers=auth_headers("staff", "Staff@123"),
    )

    assert confirm_response.status_code == 200
    assert confirm_response.get_json()["item"]["status"] == "confirmed"

    with app.app_context():
        source_inventory = Inventory.query.filter_by(
            warehouse_id=context["source_warehouse_id"],
            location_id=context["source_location_id"],
            product_id=context["product_id"],
        ).first()
        target_inventory = Inventory.query.filter_by(
            warehouse_id=context["target_warehouse_id"],
            location_id=context["target_location_id"],
            product_id=context["product_id"],
        ).first()
        product = Product.query.filter_by(id=context["product_id"]).first()
        movements = InventoryMovement.query.filter_by(
            reference_type="stock_transfer",
            reference_id=transfer_id,
        ).order_by(InventoryMovement.id.asc()).all()

        assert source_inventory.quantity == context["starting_source_quantity"] - 4
        assert target_inventory.quantity == context["starting_target_quantity"] + 4
        assert product.quantity_total == context["starting_total"]
        assert len(movements) == 2
        assert movements[0].movement_type == "transfer_out"
        assert movements[0].quantity_change == -4
        assert movements[1].movement_type == "transfer_in"
        assert movements[1].quantity_change == 4


def test_draft_stock_transfer_can_be_updated_before_confirm(client, auth_headers, app):
    context = get_seed_transfer_context(app)

    create_response = client.post(
        "/stock-transfers",
        headers=auth_headers("staff", "Staff@123"),
        json={
            "source_warehouse_id": context["source_warehouse_id"],
            "target_warehouse_id": context["target_warehouse_id"],
            "note": "Phieu dieu chuyen can sua",
            "items": [
                {
                    "product_id": context["product_id"],
                    "source_location_id": context["source_location_id"],
                    "target_location_id": context["target_location_id"],
                    "quantity": 2,
                },
            ],
        },
    )
    assert create_response.status_code == 201
    transfer_id = create_response.get_json()["item"]["id"]

    update_response = client.put(
        f"/stock-transfers/{transfer_id}",
        headers=auth_headers("staff", "Staff@123"),
        json={
            "source_warehouse_id": context["source_warehouse_id"],
            "target_warehouse_id": context["target_warehouse_id"],
            "note": "Phieu dieu chuyen da sua so luong",
            "items": [
                {
                    "product_id": context["product_id"],
                    "source_location_id": context["source_location_id"],
                    "target_location_id": context["target_location_id"],
                    "quantity": 5,
                },
            ],
        },
    )

    assert update_response.status_code == 200
    assert update_response.get_json()["item"]["note"] == "Phieu dieu chuyen da sua so luong"
    assert update_response.get_json()["item"]["total_quantity"] == 5

    confirm_response = client.post(
        f"/stock-transfers/{transfer_id}/confirm",
        headers=auth_headers("staff", "Staff@123"),
    )
    assert confirm_response.status_code == 200

    with app.app_context():
        source_inventory = Inventory.query.filter_by(
            warehouse_id=context["source_warehouse_id"],
            location_id=context["source_location_id"],
            product_id=context["product_id"],
        ).first()
        target_inventory = Inventory.query.filter_by(
            warehouse_id=context["target_warehouse_id"],
            location_id=context["target_location_id"],
            product_id=context["product_id"],
        ).first()
        movements = InventoryMovement.query.filter_by(
            reference_type="stock_transfer",
            reference_id=transfer_id,
        ).order_by(InventoryMovement.id.asc()).all()
        actions = {
            log.action
            for log in AuditLog.query.filter(
                AuditLog.entity_type == "stock_transfer",
                AuditLog.entity_id == transfer_id,
            ).all()
        }

        assert source_inventory.quantity == context["starting_source_quantity"] - 5
        assert target_inventory.quantity == context["starting_target_quantity"] + 5
        assert len(movements) == 2
        assert movements[0].quantity_change == -5
        assert movements[1].quantity_change == 5
        assert "stock_transfers.updated" in actions


def test_draft_stock_transfer_can_be_cancelled_without_changing_inventory(client, auth_headers, app):
    context = get_seed_transfer_context(app)

    create_response = client.post(
        "/stock-transfers",
        headers=auth_headers("staff", "Staff@123"),
        json={
            "source_warehouse_id": context["source_warehouse_id"],
            "target_warehouse_id": context["target_warehouse_id"],
            "note": "Phieu dieu chuyen can huy",
            "items": [
                {
                    "product_id": context["product_id"],
                    "source_location_id": context["source_location_id"],
                    "target_location_id": context["target_location_id"],
                    "quantity": 2,
                },
            ],
        },
    )
    assert create_response.status_code == 201
    transfer_id = create_response.get_json()["item"]["id"]

    cancel_response = client.post(
        f"/stock-transfers/{transfer_id}/cancel",
        headers=auth_headers("staff", "Staff@123"),
    )

    assert cancel_response.status_code == 200
    assert cancel_response.get_json()["item"]["status"] == "cancelled"

    with app.app_context():
        source_inventory = Inventory.query.filter_by(
            warehouse_id=context["source_warehouse_id"],
            location_id=context["source_location_id"],
            product_id=context["product_id"],
        ).first()
        target_inventory = Inventory.query.filter_by(
            warehouse_id=context["target_warehouse_id"],
            location_id=context["target_location_id"],
            product_id=context["product_id"],
        ).first()
        transfer = StockTransfer.query.filter_by(id=transfer_id).first()
        movement = InventoryMovement.query.filter_by(
            reference_type="stock_transfer",
            reference_id=transfer_id,
        ).first()
        actions = {
            log.action
            for log in AuditLog.query.filter(
                AuditLog.entity_type == "stock_transfer",
                AuditLog.entity_id == transfer_id,
            ).all()
        }

        assert source_inventory.quantity == context["starting_source_quantity"]
        assert target_inventory.quantity == context["starting_target_quantity"]
        assert transfer.status == "cancelled"
        assert movement is None
        assert "stock_transfers.cancelled" in actions


def test_stock_transfer_permission_matrix(client, auth_headers):
    manager_response = client.get("/stock-transfers", headers=auth_headers("manager", "Manager@123"))
    staff_response = client.get("/stock-transfers", headers=auth_headers("staff", "Staff@123"))
    accountant_response = client.get("/stock-transfers", headers=auth_headers("accountant", "Accountant@123"))
    shipper_response = client.get("/stock-transfers", headers=auth_headers("shipper", "Shipper@123"))

    assert manager_response.status_code == 200
    assert staff_response.status_code == 200
    assert accountant_response.status_code == 403
    assert shipper_response.status_code == 403


def test_stock_transfer_rejects_same_source_and_target_warehouse(client, auth_headers, app):
    context = get_seed_transfer_context(app)

    response = client.post(
        "/stock-transfers",
        headers=auth_headers("admin", "Admin@123"),
        json={
            "source_warehouse_id": context["source_warehouse_id"],
            "target_warehouse_id": context["source_warehouse_id"],
            "items": [
                {
                    "product_id": context["product_id"],
                    "source_location_id": context["source_location_id"],
                    "target_location_id": context["source_location_id"],
                    "quantity": 1,
                },
            ],
        },
    )

    assert response.status_code == 400


def test_stock_transfer_rejects_target_location_outside_target_warehouse(client, auth_headers, app):
    context = get_seed_transfer_context(app)

    response = client.post(
        "/stock-transfers",
        headers=auth_headers("admin", "Admin@123"),
        json={
            "source_warehouse_id": context["source_warehouse_id"],
            "target_warehouse_id": context["target_warehouse_id"],
            "items": [
                {
                    "product_id": context["product_id"],
                    "source_location_id": context["source_location_id"],
                    "target_location_id": context["source_location_id"],
                    "quantity": 1,
                },
            ],
        },
    )

    assert response.status_code == 400


def test_stock_transfer_confirm_blocks_when_source_stock_is_not_enough(client, auth_headers, app):
    context = get_seed_transfer_context(app)
    requested_quantity = context["starting_source_quantity"] + 1

    create_response = client.post(
        "/stock-transfers",
        headers=auth_headers("admin", "Admin@123"),
        json={
            "source_warehouse_id": context["source_warehouse_id"],
            "target_warehouse_id": context["target_warehouse_id"],
            "items": [
                {
                    "product_id": context["product_id"],
                    "source_location_id": context["source_location_id"],
                    "target_location_id": context["target_location_id"],
                    "quantity": requested_quantity,
                },
            ],
        },
    )
    transfer_id = create_response.get_json()["item"]["id"]

    confirm_response = client.post(
        f"/stock-transfers/{transfer_id}/confirm",
        headers=auth_headers("admin", "Admin@123"),
    )

    assert confirm_response.status_code == 400

    with app.app_context():
        source_inventory = Inventory.query.filter_by(
            warehouse_id=context["source_warehouse_id"],
            location_id=context["source_location_id"],
            product_id=context["product_id"],
        ).first()
        target_inventory = Inventory.query.filter_by(
            warehouse_id=context["target_warehouse_id"],
            location_id=context["target_location_id"],
            product_id=context["product_id"],
        ).first()
        transfer = StockTransfer.query.filter_by(id=transfer_id).first()
        movement = InventoryMovement.query.filter_by(
            reference_type="stock_transfer",
            reference_id=transfer_id,
        ).first()

        assert source_inventory.quantity == context["starting_source_quantity"]
        assert target_inventory.quantity == context["starting_target_quantity"]
        assert transfer.status == "draft"
        assert movement is None


def test_stock_transfer_list_supports_pagination_search_and_status(client, auth_headers):
    response = client.get(
        "/stock-transfers?page=1&page_size=10&search=TRF-DEMO-001&status=draft",
        headers=auth_headers("admin", "Admin@123"),
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["page"] == 1
    assert payload["page_size"] == 10
    assert payload["total"] >= 1
    assert any(item["transfer_code"] == "TRF-DEMO-001" for item in payload["items"])


def test_confirmed_stock_transfer_cannot_be_confirmed_again(client, auth_headers, app):
    context = get_seed_transfer_context(app)

    create_response = client.post(
        "/stock-transfers",
        headers=auth_headers("admin", "Admin@123"),
        json={
            "source_warehouse_id": context["source_warehouse_id"],
            "target_warehouse_id": context["target_warehouse_id"],
            "items": [
                {
                    "product_id": context["product_id"],
                    "source_location_id": context["source_location_id"],
                    "target_location_id": context["target_location_id"],
                    "quantity": 2,
                },
            ],
        },
    )
    transfer_id = create_response.get_json()["item"]["id"]

    first_confirm = client.post(
        f"/stock-transfers/{transfer_id}/confirm",
        headers=auth_headers("admin", "Admin@123"),
    )
    second_confirm = client.post(
        f"/stock-transfers/{transfer_id}/confirm",
        headers=auth_headers("admin", "Admin@123"),
    )
    update_response = client.put(
        f"/stock-transfers/{transfer_id}",
        headers=auth_headers("admin", "Admin@123"),
        json={
            "source_warehouse_id": context["source_warehouse_id"],
            "target_warehouse_id": context["target_warehouse_id"],
            "items": [
                {
                    "product_id": context["product_id"],
                    "source_location_id": context["source_location_id"],
                    "target_location_id": context["target_location_id"],
                    "quantity": 3,
                },
            ],
        },
    )

    assert first_confirm.status_code == 200
    assert second_confirm.status_code == 400
    assert update_response.status_code == 400


def test_cancelled_stock_transfer_cannot_be_confirmed_or_updated_again(client, auth_headers, app):
    context = get_seed_transfer_context(app)

    create_response = client.post(
        "/stock-transfers",
        headers=auth_headers("admin", "Admin@123"),
        json={
            "source_warehouse_id": context["source_warehouse_id"],
            "target_warehouse_id": context["target_warehouse_id"],
            "items": [
                {
                    "product_id": context["product_id"],
                    "source_location_id": context["source_location_id"],
                    "target_location_id": context["target_location_id"],
                    "quantity": 2,
                },
            ],
        },
    )
    transfer_id = create_response.get_json()["item"]["id"]

    cancel_response = client.post(
        f"/stock-transfers/{transfer_id}/cancel",
        headers=auth_headers("admin", "Admin@123"),
    )
    confirm_response = client.post(
        f"/stock-transfers/{transfer_id}/confirm",
        headers=auth_headers("admin", "Admin@123"),
    )
    update_response = client.put(
        f"/stock-transfers/{transfer_id}",
        headers=auth_headers("admin", "Admin@123"),
        json={
            "source_warehouse_id": context["source_warehouse_id"],
            "target_warehouse_id": context["target_warehouse_id"],
            "items": [
                {
                    "product_id": context["product_id"],
                    "source_location_id": context["source_location_id"],
                    "target_location_id": context["target_location_id"],
                    "quantity": 3,
                },
            ],
        },
    )

    assert cancel_response.status_code == 200
    assert confirm_response.status_code == 400
    assert update_response.status_code == 400


def test_stock_transfer_create_confirm_write_audit_log(client, auth_headers, app):
    context = get_seed_transfer_context(app)

    create_response = client.post(
        "/stock-transfers",
        headers=auth_headers("admin", "Admin@123"),
        json={
            "source_warehouse_id": context["source_warehouse_id"],
            "target_warehouse_id": context["target_warehouse_id"],
            "note": "Phieu dieu chuyen audit",
            "items": [
                {
                    "product_id": context["product_id"],
                    "source_location_id": context["source_location_id"],
                    "target_location_id": context["target_location_id"],
                    "quantity": 3,
                },
            ],
        },
    )
    assert create_response.status_code == 201
    transfer_id = create_response.get_json()["item"]["id"]

    confirm_response = client.post(
        f"/stock-transfers/{transfer_id}/confirm",
        headers=auth_headers("admin", "Admin@123"),
    )
    assert confirm_response.status_code == 200

    with app.app_context():
        actions = {
            log.action
            for log in AuditLog.query.filter(
                AuditLog.entity_type == "stock_transfer",
                AuditLog.entity_id == transfer_id,
            ).all()
        }

    assert actions == {
        "stock_transfers.created",
        "stock_transfers.confirmed",
    }
