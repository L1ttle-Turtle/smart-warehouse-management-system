def test_reports_endpoints_return_business_data(client, auth_headers):
    headers = auth_headers("manager", "Manager@123")

    summary_response = client.get("/reports/summary", headers=headers)
    inventory_response = client.get("/reports/inventory-by-warehouse", headers=headers)
    movement_response = client.get("/reports/stock-movement", headers=headers)
    top_products_response = client.get("/reports/top-products", headers=headers)
    shipments_response = client.get("/reports/shipment-performance", headers=headers)
    revenue_response = client.get("/reports/revenue", headers=headers)

    assert summary_response.status_code == 200
    assert inventory_response.status_code == 200
    assert movement_response.status_code == 200
    assert top_products_response.status_code == 200
    assert shipments_response.status_code == 200
    assert revenue_response.status_code == 200

    summary_payload = summary_response.get_json()
    assert {item["key"] for item in summary_payload["metrics"]} == {
        "total_inventory_quantity",
        "stock_alert_lines",
        "draft_documents",
        "active_shipments",
        "total_revenue",
        "outstanding_amount",
    }
    assert summary_payload["summary"]["total_inventory_quantity"] > 0
    assert summary_payload["summary"]["total_revenue"] >= summary_payload["summary"]["paid_amount"]
    assert any(item.get("format") == "currency" for item in summary_payload["metrics"])

    assert any(
        item["warehouse_name"] == "Kho Trung Tam"
        for item in inventory_response.get_json()["items"]
    )
    assert "import_quantity" in movement_response.get_json()["items"][0]
    assert top_products_response.get_json()["items"]

    shipment_items = shipments_response.get_json()["items"]
    assert {item["status"] for item in shipment_items} == {
        "assigned",
        "in_transit",
        "delivered",
        "cancelled",
    }
    assert all("status_label" in item for item in shipment_items)

    revenue_payload = revenue_response.get_json()
    assert revenue_payload["revenue"]
    assert any(item["status"] == "unpaid" for item in revenue_payload["payment_status"])


def test_reports_require_reports_view_permission(client, auth_headers):
    response = client.get(
        "/reports/summary",
        headers=auth_headers("staff", "Staff@123"),
    )

    assert response.status_code == 403


def test_accountant_can_view_revenue_report(client, auth_headers):
    response = client.get(
        "/reports/revenue",
        headers=auth_headers("accountant", "Accountant@123"),
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert "revenue" in payload
    assert "payment_status" in payload
