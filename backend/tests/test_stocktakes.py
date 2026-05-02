from app.models import AuditLog, Inventory, InventoryMovement, Product, Stocktake, Warehouse, WarehouseLocation


def get_stocktake_context(app):
    with app.app_context():
        warehouse = Warehouse.query.filter_by(warehouse_code="WH001").first()
        other_warehouse = Warehouse.query.filter_by(warehouse_code="WH002").first()
        printer = Product.query.filter_by(product_code="PRD002").first()
        trolley = Product.query.filter_by(product_code="PRD005").first()
        radio = Product.query.filter_by(product_code="PRD004").first()
        primary_location = WarehouseLocation.query.filter_by(
            warehouse_id=warehouse.id,
            location_code="B-01",
        ).first()
        empty_location = WarehouseLocation.query.filter_by(
            warehouse_id=warehouse.id,
            location_code="A-01",
        ).first()
        wrong_location = WarehouseLocation.query.filter_by(
            warehouse_id=other_warehouse.id,
            location_code="A-01",
        ).first()
        printer_inventory = Inventory.query.filter_by(
            warehouse_id=warehouse.id,
            location_id=primary_location.id,
            product_id=printer.id,
        ).first()
        trolley_inventory = Inventory.query.filter_by(
            warehouse_id=warehouse.id,
            location_id=primary_location.id,
            product_id=trolley.id,
        ).first()
        radio_inventory = Inventory.query.filter_by(
            warehouse_id=warehouse.id,
            location_id=empty_location.id,
            product_id=radio.id,
        ).first()
        return {
            "warehouse_id": warehouse.id,
            "other_warehouse_id": other_warehouse.id,
            "printer_id": printer.id,
            "trolley_id": trolley.id,
            "radio_id": radio.id,
            "primary_location_id": primary_location.id,
            "empty_location_id": empty_location.id,
            "wrong_location_id": wrong_location.id,
            "starting_printer_quantity": float(printer_inventory.quantity if printer_inventory else 0),
            "starting_trolley_quantity": float(trolley_inventory.quantity if trolley_inventory else 0),
            "starting_radio_quantity": float(radio_inventory.quantity if radio_inventory else 0),
        }


def test_seed_demo_contains_draft_stocktake(app):
    with app.app_context():
        stocktake = Stocktake.query.filter_by(stocktake_code="STK-DEMO-001").first()

        assert stocktake is not None
        assert stocktake.status == "draft"
        assert len(stocktake.details) == 2


def test_create_stocktake_draft_does_not_change_inventory(client, auth_headers, app):
    context = get_stocktake_context(app)

    response = client.post(
        "/stocktakes",
        headers=auth_headers("staff", "Staff@123"),
        json={
            "warehouse_id": context["warehouse_id"],
            "note": "Kiem ke nhap truoc khi xac nhan",
            "details": [
                {
                    "product_id": context["printer_id"],
                    "location_id": context["primary_location_id"],
                    "actual_quantity": context["starting_printer_quantity"] + 1,
                    "note": "Lech mot may sau ca lam viec",
                },
            ],
        },
    )

    assert response.status_code == 201
    payload = response.get_json()["item"]
    assert payload["status"] == "draft"
    assert payload["details"][0]["system_quantity"] == context["starting_printer_quantity"]
    assert payload["details"][0]["difference_quantity"] == 1

    with app.app_context():
        inventory_row = Inventory.query.filter_by(
            warehouse_id=context["warehouse_id"],
            location_id=context["primary_location_id"],
            product_id=context["printer_id"],
        ).first()
        movement = InventoryMovement.query.filter_by(reference_type="stocktake").first()

        assert inventory_row.quantity == context["starting_printer_quantity"]
        assert movement is None


def test_create_stocktake_rejects_duplicate_product_location(client, auth_headers, app):
    context = get_stocktake_context(app)

    response = client.post(
        "/stocktakes",
        headers=auth_headers("manager", "Manager@123"),
        json={
            "warehouse_id": context["warehouse_id"],
            "details": [
                {
                    "product_id": context["printer_id"],
                    "location_id": context["primary_location_id"],
                    "actual_quantity": 7,
                },
                {
                    "product_id": context["printer_id"],
                    "location_id": context["primary_location_id"],
                    "actual_quantity": 8,
                },
            ],
        },
    )

    assert response.status_code == 422


def test_confirm_stocktake_updates_inventory_and_creates_movements(client, auth_headers, app):
    context = get_stocktake_context(app)

    create_response = client.post(
        "/stocktakes",
        headers=auth_headers("staff", "Staff@123"),
        json={
            "warehouse_id": context["warehouse_id"],
            "note": "Kiem ke cuoi ngay",
            "details": [
                {
                    "product_id": context["printer_id"],
                    "location_id": context["primary_location_id"],
                    "actual_quantity": 9,
                    "note": "Bo sung sau khi kiem dem lai",
                },
                {
                    "product_id": context["radio_id"],
                    "location_id": context["empty_location_id"],
                    "actual_quantity": 2,
                    "note": "Tim thay them 2 bo dam tai ke A-01",
                },
            ],
        },
    )
    assert create_response.status_code == 201
    stocktake_id = create_response.get_json()["item"]["id"]

    confirm_response = client.post(
        f"/stocktakes/{stocktake_id}/confirm",
        headers=auth_headers("staff", "Staff@123"),
    )

    assert confirm_response.status_code == 200
    assert confirm_response.get_json()["item"]["status"] == "confirmed"

    with app.app_context():
        printer_inventory = Inventory.query.filter_by(
            warehouse_id=context["warehouse_id"],
            location_id=context["primary_location_id"],
            product_id=context["printer_id"],
        ).first()
        radio_inventory = Inventory.query.filter_by(
            warehouse_id=context["warehouse_id"],
            location_id=context["empty_location_id"],
            product_id=context["radio_id"],
        ).first()
        stocktake = Stocktake.query.filter_by(id=stocktake_id).first()
        movements = InventoryMovement.query.filter_by(
            reference_type="stocktake",
            reference_id=stocktake_id,
        ).order_by(InventoryMovement.id.asc()).all()
        audit_actions = {
            log.action
            for log in AuditLog.query.filter(
                AuditLog.entity_type == "stocktake",
                AuditLog.entity_id == stocktake_id,
            ).all()
        }

        assert printer_inventory.quantity == 9
        assert radio_inventory.quantity == 2
        assert stocktake.status == "confirmed"
        assert len(movements) == 2
        assert all(movement.reference_type == "stocktake" for movement in movements)
        assert {movement.movement_type for movement in movements} == {"stocktake_adjustment"}
        assert audit_actions == {"stocktakes.created", "stocktakes.confirmed"}


def test_cancel_stocktake_draft_does_not_change_inventory(client, auth_headers, app):
    context = get_stocktake_context(app)

    create_response = client.post(
        "/stocktakes",
        headers=auth_headers("manager", "Manager@123"),
        json={
            "warehouse_id": context["warehouse_id"],
            "details": [
                {
                    "product_id": context["trolley_id"],
                    "location_id": context["primary_location_id"],
                    "actual_quantity": 2,
                },
            ],
        },
    )
    assert create_response.status_code == 201
    stocktake_id = create_response.get_json()["item"]["id"]

    cancel_response = client.post(
        f"/stocktakes/{stocktake_id}/cancel",
        headers=auth_headers("manager", "Manager@123"),
    )

    assert cancel_response.status_code == 200
    assert cancel_response.get_json()["item"]["status"] == "cancelled"

    with app.app_context():
        inventory_row = Inventory.query.filter_by(
            warehouse_id=context["warehouse_id"],
            location_id=context["primary_location_id"],
            product_id=context["trolley_id"],
        ).first()
        movement = InventoryMovement.query.filter_by(
            reference_type="stocktake",
            reference_id=stocktake_id,
        ).first()

        assert inventory_row.quantity == context["starting_trolley_quantity"]
        assert movement is None


def test_confirmed_stocktake_cannot_be_updated_or_confirmed_again(client, auth_headers, app):
    context = get_stocktake_context(app)

    create_response = client.post(
        "/stocktakes",
        headers=auth_headers("admin", "Admin@123"),
        json={
            "warehouse_id": context["warehouse_id"],
            "details": [
                {
                    "product_id": context["printer_id"],
                    "location_id": context["primary_location_id"],
                    "actual_quantity": 8,
                },
            ],
        },
    )
    stocktake_id = create_response.get_json()["item"]["id"]

    first_confirm = client.post(
        f"/stocktakes/{stocktake_id}/confirm",
        headers=auth_headers("admin", "Admin@123"),
    )
    second_confirm = client.post(
        f"/stocktakes/{stocktake_id}/confirm",
        headers=auth_headers("admin", "Admin@123"),
    )
    update_response = client.put(
        f"/stocktakes/{stocktake_id}",
        headers=auth_headers("admin", "Admin@123"),
        json={
            "warehouse_id": context["warehouse_id"],
            "details": [
                {
                    "product_id": context["printer_id"],
                    "location_id": context["primary_location_id"],
                    "actual_quantity": 7,
                },
            ],
        },
    )

    assert first_confirm.status_code == 200
    assert second_confirm.status_code == 400
    assert update_response.status_code == 400


def test_stocktake_rejects_negative_actual_quantity_and_wrong_location(client, auth_headers, app):
    context = get_stocktake_context(app)

    negative_response = client.post(
        "/stocktakes",
        headers=auth_headers("staff", "Staff@123"),
        json={
            "warehouse_id": context["warehouse_id"],
            "details": [
                {
                    "product_id": context["printer_id"],
                    "location_id": context["primary_location_id"],
                    "actual_quantity": -1,
                },
            ],
        },
    )
    wrong_location_response = client.post(
        "/stocktakes",
        headers=auth_headers("staff", "Staff@123"),
        json={
            "warehouse_id": context["warehouse_id"],
            "details": [
                {
                    "product_id": context["printer_id"],
                    "location_id": context["wrong_location_id"],
                    "actual_quantity": 4,
                },
            ],
        },
    )

    assert negative_response.status_code == 422
    assert wrong_location_response.status_code == 400


def test_stocktake_permission_matrix(client, auth_headers, app):
    context = get_stocktake_context(app)
    payload = {
        "warehouse_id": context["warehouse_id"],
        "details": [
            {
                "product_id": context["printer_id"],
                "location_id": context["primary_location_id"],
                "actual_quantity": 6,
            },
        ],
    }

    admin_list = client.get("/stocktakes", headers=auth_headers("admin", "Admin@123"))
    staff_create = client.post("/stocktakes", headers=auth_headers("staff", "Staff@123"), json=payload)
    accountant_list = client.get("/stocktakes", headers=auth_headers("accountant", "Accountant@123"))
    shipper_create = client.post("/stocktakes", headers=auth_headers("shipper", "Shipper@123"), json=payload)

    assert admin_list.status_code == 200
    assert staff_create.status_code == 201
    assert accountant_list.status_code == 403
    assert shipper_create.status_code == 403
