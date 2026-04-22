def test_inventory_list_returns_seeded_inventory_rows(client, auth_headers):
    response = client.get("/inventory", headers=auth_headers("admin", "Admin@123"))

    assert response.status_code == 200
    payload = response.get_json()
    assert len(payload["items"]) >= 2
    assert any(item["warehouse_name"] == "Kho Trung Tam" for item in payload["items"])
    assert any(item["location_name"] == "Ke A-01" for item in payload["items"])
    assert any(item["product_name"] == "May quet ma vach" for item in payload["items"])
    assert any(item["quantity"] == 24 for item in payload["items"])


def test_inventory_movements_returns_seeded_history(client, auth_headers):
    response = client.get("/inventory/movements", headers=auth_headers("manager", "Manager@123"))

    assert response.status_code == 200
    payload = response.get_json()
    assert len(payload["items"]) >= 2
    assert any(item["movement_type"] == "adjustment" for item in payload["items"])
    assert any(item["reference_type"] == "seed" for item in payload["items"])
    assert any(item["quantity_after"] == 24 for item in payload["items"])


def test_inventory_routes_require_inventory_view_permission(client, auth_headers):
    staff_response = client.get("/inventory", headers=auth_headers("staff", "Staff@123"))
    accountant_response = client.get("/inventory", headers=auth_headers("accountant", "Accountant@123"))

    assert staff_response.status_code == 200
    assert accountant_response.status_code == 403
