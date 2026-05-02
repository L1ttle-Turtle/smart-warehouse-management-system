from app.models import AuditLog, Inventory, InventoryMovement, Product, Warehouse, WarehouseLocation


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
        return {
            "source_warehouse_id": source_warehouse.id,
            "target_warehouse_id": target_warehouse.id,
            "product_id": product.id,
            "source_location_id": source_location.id,
            "target_location_id": target_location.id,
        }


def test_inventory_list_returns_seeded_inventory_rows(client, auth_headers):
    response = client.get("/inventory", headers=auth_headers("admin", "Admin@123"))

    assert response.status_code == 200
    payload = response.get_json()
    assert len(payload["items"]) >= 2
    assert any(item["warehouse_name"] == "Kho Trung Tam" for item in payload["items"])
    assert any(item["location_name"] == "Ke A-01" for item in payload["items"])
    assert any(item["product_name"] == "May quet ma vach" for item in payload["items"])
    assert any(item["quantity"] == 24 for item in payload["items"])


def test_inventory_list_includes_stock_status_fields(client, auth_headers):
    response = client.get("/inventory", headers=auth_headers("admin", "Admin@123"))

    assert response.status_code == 200
    payload = response.get_json()

    low_stock_item = next(
        item
        for item in payload["items"]
        if item["product_code"] == "PRD001" and item["warehouse_code"] == "WH002"
    )
    out_of_stock_item = next(
        item
        for item in payload["items"]
        if item["product_code"] == "PRD004" and item["warehouse_code"] == "WH001"
    )

    assert low_stock_item["stock_status"] == "low_stock"
    assert low_stock_item["stock_status_label"] == "Tồn thấp"
    assert low_stock_item["is_low_stock"] is True
    assert low_stock_item["shortage_quantity"] == 2

    assert out_of_stock_item["stock_status"] == "out_of_stock"
    assert out_of_stock_item["stock_status_label"] == "Hết hàng"
    assert out_of_stock_item["is_low_stock"] is True
    assert out_of_stock_item["shortage_quantity"] == 12


def test_inventory_list_can_filter_low_stock_only(client, auth_headers):
    response = client.get(
        "/inventory?low_stock_only=true",
        headers=auth_headers("manager", "Manager@123"),
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["total"] >= 1
    assert all(item["stock_status"] in {"low_stock", "out_of_stock"} for item in payload["items"])
    assert any(item["stock_status"] == "out_of_stock" for item in payload["items"])


def test_inventory_list_can_filter_out_of_stock(client, auth_headers):
    response = client.get(
        "/inventory?stock_status=out_of_stock",
        headers=auth_headers("manager", "Manager@123"),
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["items"]
    assert all(item["stock_status"] == "out_of_stock" for item in payload["items"])
    assert all(item["product_code"] == "PRD004" for item in payload["items"])


def test_inventory_list_rejects_invalid_filter_ids(client, auth_headers):
    invalid_warehouse = client.get(
        "/inventory?warehouse_id=abc",
        headers=auth_headers("admin", "Admin@123"),
    )
    invalid_location = client.get(
        "/inventory?location_id=99999",
        headers=auth_headers("admin", "Admin@123"),
    )

    assert invalid_warehouse.status_code == 400
    assert invalid_location.status_code == 400


def test_inventory_list_allows_large_lookup_page_size(client, auth_headers):
    response = client.get(
        "/inventory?page=1&per_page=500&sort_by=updated_at&sort_order=desc",
        headers=auth_headers("admin", "Admin@123"),
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["page_size"] == 500
    assert payload["per_page"] == 500
    assert len(payload["items"]) >= 1


def test_inventory_movements_returns_seeded_history(client, auth_headers):
    response = client.get("/inventory/movements", headers=auth_headers("manager", "Manager@123"))

    assert response.status_code == 200
    payload = response.get_json()
    assert len(payload["items"]) >= 2
    assert any(item["movement_type"] == "adjustment" for item in payload["items"])
    assert any(item["reference_type"] == "seed" for item in payload["items"])
    assert any(item["quantity_after"] == 24 for item in payload["items"])


def test_inventory_movements_can_be_filtered_by_stock_transfer_reference(client, auth_headers, app):
    context = get_seed_transfer_context(app)

    create_response = client.post(
        "/stock-transfers",
        headers=auth_headers("admin", "Admin@123"),
        json={
            "source_warehouse_id": context["source_warehouse_id"],
            "target_warehouse_id": context["target_warehouse_id"],
            "note": "Loc movement theo phiếu điều chuyển",
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

    confirm_response = client.post(
        f"/stock-transfers/{transfer_id}/confirm",
        headers=auth_headers("admin", "Admin@123"),
    )
    assert confirm_response.status_code == 200

    response = client.get(
        f"/inventory/movements?reference_type=stock_transfer&reference_id={transfer_id}",
        headers=auth_headers("manager", "Manager@123"),
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert len(payload["items"]) == 2
    assert all(item["reference_type"] == "stock_transfer" for item in payload["items"])
    assert all(item["reference_id"] == transfer_id for item in payload["items"])
    assert {item["movement_type"] for item in payload["items"]} == {"transfer_out", "transfer_in"}


def test_inventory_movements_rejects_invalid_reference_id(client, auth_headers):
    response = client.get(
        "/inventory/movements?reference_type=stock_transfer&reference_id=abc",
        headers=auth_headers("manager", "Manager@123"),
    )

    assert response.status_code == 400
    assert "reference_id" in response.get_json()["message"]


def test_inventory_routes_require_inventory_view_permission(client, auth_headers):
    staff_response = client.get("/inventory", headers=auth_headers("staff", "Staff@123"))
    accountant_response = client.get("/inventory", headers=auth_headers("accountant", "Accountant@123"))

    assert staff_response.status_code == 200
    assert accountant_response.status_code == 403


def test_inventory_adjustment_updates_stock_and_creates_movement(client, auth_headers, app):
    context = get_seed_transfer_context(app)

    response = client.post(
        "/inventory/adjustments",
        headers=auth_headers("admin", "Admin@123"),
        json={
            "warehouse_id": context["source_warehouse_id"],
            "location_id": context["source_location_id"],
            "product_id": context["product_id"],
            "actual_quantity": 20,
            "note": "Dieu chinh sau kiem ke demo",
        },
    )

    assert response.status_code == 201
    payload = response.get_json()
    assert payload["inventory"]["quantity"] == 20
    assert payload["movement"]["movement_type"] == "adjustment"
    assert payload["movement"]["reference_type"] == "inventory_adjustment"
    assert payload["movement"]["quantity_before"] == 24
    assert payload["movement"]["quantity_change"] == -4
    assert payload["movement"]["quantity_after"] == 20

    with app.app_context():
        inventory_row = Inventory.query.filter_by(
            warehouse_id=context["source_warehouse_id"],
            location_id=context["source_location_id"],
            product_id=context["product_id"],
        ).first()
        assert inventory_row is not None
        assert inventory_row.quantity == 20

        movement = InventoryMovement.query.filter_by(reference_type="inventory_adjustment").first()
        assert movement is not None
        assert movement.quantity_after == 20

        audit_log = AuditLog.query.filter_by(action="inventory.adjusted").first()
        assert audit_log is not None


def test_inventory_adjustment_rejects_invalid_location_for_selected_warehouse(client, auth_headers, app):
    context = get_seed_transfer_context(app)

    response = client.post(
        "/inventory/adjustments",
        headers=auth_headers("manager", "Manager@123"),
        json={
            "warehouse_id": context["source_warehouse_id"],
            "location_id": context["target_location_id"],
            "product_id": context["product_id"],
            "actual_quantity": 18,
            "note": "Sai vi tri kho",
        },
    )

    assert response.status_code == 400


def test_inventory_adjustment_requires_inventory_manage_permission(client, auth_headers, app):
    context = get_seed_transfer_context(app)
    payload = {
        "warehouse_id": context["source_warehouse_id"],
        "location_id": context["source_location_id"],
        "product_id": context["product_id"],
        "actual_quantity": 21,
        "note": "Kiem tra phan quyen",
    }

    staff_response = client.post(
        "/inventory/adjustments",
        headers=auth_headers("staff", "Staff@123"),
        json=payload,
    )
    accountant_response = client.post(
        "/inventory/adjustments",
        headers=auth_headers("accountant", "Accountant@123"),
        json=payload,
    )
    shipper_response = client.post(
        "/inventory/adjustments",
        headers=auth_headers("shipper", "Shipper@123"),
        json=payload,
    )

    assert staff_response.status_code == 201
    assert accountant_response.status_code == 403
    assert shipper_response.status_code == 403
