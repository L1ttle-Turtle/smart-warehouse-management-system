from app.models import AuditLog, Warehouse, WarehouseLocation


def get_warehouse_id(app, warehouse_code="WH001"):
    with app.app_context():
        warehouse = Warehouse.query.filter_by(warehouse_code=warehouse_code).first()
        return warehouse.id


def get_location_id(app, warehouse_code="WH001", location_code="A-01"):
    with app.app_context():
        warehouse = Warehouse.query.filter_by(warehouse_code=warehouse_code).first()
        location = WarehouseLocation.query.filter_by(
            warehouse_id=warehouse.id,
            location_code=location_code,
        ).first()
        return location.id


def test_admin_can_list_warehouses_and_locations(client, auth_headers):
    warehouse_response = client.get("/warehouses", headers=auth_headers("admin", "Admin@123"))
    location_response = client.get("/locations", headers=auth_headers("admin", "Admin@123"))

    assert warehouse_response.status_code == 200
    assert location_response.status_code == 200

    warehouse_payload = warehouse_response.get_json()
    location_payload = location_response.get_json()

    assert warehouse_payload["total"] >= 2
    assert location_payload["total"] >= 3
    assert any(item["warehouse_code"] == "WH001" for item in warehouse_payload["items"])
    assert any(item["location_code"] == "A-01" for item in location_payload["items"])


def test_admin_can_create_update_delete_warehouse(client, auth_headers):
    create_response = client.post(
        "/warehouses",
        headers=auth_headers("admin", "Admin@123"),
        json={
            "warehouse_code": "WH099",
            "warehouse_name": "Kho test moi",
            "address": "99 Tran Phu",
            "status": "active",
        },
    )
    assert create_response.status_code == 201
    warehouse_id = create_response.get_json()["item"]["id"]

    update_response = client.put(
        f"/warehouses/{warehouse_id}",
        headers=auth_headers("admin", "Admin@123"),
        json={"warehouse_name": "Kho test cap nhat", "status": "inactive"},
    )
    assert update_response.status_code == 200
    assert update_response.get_json()["item"]["warehouse_name"] == "Kho test cap nhat"

    delete_response = client.delete(
        f"/warehouses/{warehouse_id}",
        headers=auth_headers("admin", "Admin@123"),
    )
    assert delete_response.status_code == 200


def test_admin_can_create_update_delete_location(client, auth_headers, app):
    warehouse_id = get_warehouse_id(app, "WH002")

    create_response = client.post(
        "/locations",
        headers=auth_headers("admin", "Admin@123"),
        json={
            "warehouse_id": warehouse_id,
            "location_code": "Z-99",
            "location_name": "Ke test moi",
            "status": "active",
        },
    )
    assert create_response.status_code == 201
    location_id = create_response.get_json()["item"]["id"]

    update_response = client.put(
        f"/locations/{location_id}",
        headers=auth_headers("admin", "Admin@123"),
        json={"location_name": "Ke test cap nhat", "status": "inactive"},
    )
    assert update_response.status_code == 200
    assert update_response.get_json()["item"]["location_name"] == "Ke test cap nhat"

    delete_response = client.delete(
        f"/locations/{location_id}",
        headers=auth_headers("admin", "Admin@123"),
    )
    assert delete_response.status_code == 200


def test_warehouse_permission_matrix(client, auth_headers):
    manager_response = client.get("/warehouses", headers=auth_headers("manager", "Manager@123"))
    staff_response = client.get("/warehouses", headers=auth_headers("staff", "Staff@123"))
    staff_create = client.post(
        "/warehouses",
        headers=auth_headers("staff", "Staff@123"),
        json={
            "warehouse_code": "WH150",
            "warehouse_name": "Kho staff tao",
            "status": "active",
        },
    )
    accountant_response = client.get("/warehouses", headers=auth_headers("accountant", "Accountant@123"))
    shipper_response = client.get("/warehouses", headers=auth_headers("shipper", "Shipper@123"))

    assert manager_response.status_code == 200
    assert staff_response.status_code == 200
    assert staff_create.status_code == 403
    assert accountant_response.status_code == 403
    assert shipper_response.status_code == 403


def test_location_permission_matrix(client, auth_headers, app):
    warehouse_id = get_warehouse_id(app)

    manager_create = client.post(
        "/locations",
        headers=auth_headers("manager", "Manager@123"),
        json={
            "warehouse_id": warehouse_id,
            "location_code": "M-01",
            "location_name": "Vi tri manager tao",
            "status": "active",
        },
    )
    staff_list = client.get("/locations", headers=auth_headers("staff", "Staff@123"))
    staff_create = client.post(
        "/locations",
        headers=auth_headers("staff", "Staff@123"),
        json={
            "warehouse_id": warehouse_id,
            "location_code": "S-01",
            "location_name": "Vi tri staff tao",
            "status": "active",
        },
    )
    accountant_list = client.get("/locations", headers=auth_headers("accountant", "Accountant@123"))

    assert manager_create.status_code == 201
    assert staff_list.status_code == 200
    assert staff_create.status_code == 403
    assert accountant_list.status_code == 403


def test_warehouse_list_supports_search_status_and_pagination(client, auth_headers):
    response = client.get(
        "/warehouses?page=1&page_size=1&search=Kho&status=active&sort_by=warehouse_code&sort_order=asc",
        headers=auth_headers("admin", "Admin@123"),
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["page"] == 1
    assert payload["page_size"] == 1
    assert payload["total"] >= 2
    assert len(payload["items"]) == 1


def test_location_list_supports_search_status_warehouse_and_pagination(client, auth_headers, app):
    warehouse_id = get_warehouse_id(app, "WH001")

    response = client.get(
        f"/locations?page=1&page_size=2&search=A-01&status=active&warehouse_id={warehouse_id}&sort_by=location_code&sort_order=asc",
        headers=auth_headers("admin", "Admin@123"),
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["page"] == 1
    assert payload["page_size"] == 2
    assert payload["total"] >= 1
    assert all(item["warehouse_id"] == warehouse_id for item in payload["items"])
    assert any(item["location_code"] == "A-01" for item in payload["items"])


def test_duplicate_codes_and_invalid_warehouse_return_error(client, auth_headers, app):
    warehouse_id = get_warehouse_id(app)

    duplicate_warehouse = client.post(
        "/warehouses",
        headers=auth_headers("admin", "Admin@123"),
        json={
            "warehouse_code": "WH001",
            "warehouse_name": "Kho trung ma",
            "status": "active",
        },
    )
    duplicate_location = client.post(
        "/locations",
        headers=auth_headers("admin", "Admin@123"),
        json={
            "warehouse_id": warehouse_id,
            "location_code": "A-01",
            "location_name": "Vi tri trung ma",
            "status": "active",
        },
    )
    invalid_warehouse = client.post(
        "/locations",
        headers=auth_headers("admin", "Admin@123"),
        json={
            "warehouse_id": 9999,
            "location_code": "X-01",
            "location_name": "Vi tri sai kho",
            "status": "active",
        },
    )

    assert duplicate_warehouse.status_code == 409
    assert duplicate_location.status_code == 409
    assert invalid_warehouse.status_code == 400


def test_seeded_warehouse_and_location_cannot_be_deleted_when_referenced(client, auth_headers, app):
    warehouse_id = get_warehouse_id(app, "WH001")
    location_id = get_location_id(app, "WH001", "A-01")

    warehouse_delete = client.delete(
        f"/warehouses/{warehouse_id}",
        headers=auth_headers("admin", "Admin@123"),
    )
    location_delete = client.delete(
        f"/locations/{location_id}",
        headers=auth_headers("admin", "Admin@123"),
    )

    assert warehouse_delete.status_code == 409
    assert location_delete.status_code == 409


def test_referenced_location_cannot_move_to_other_warehouse(client, auth_headers, app):
    source_location_id = get_location_id(app, "WH001", "A-01")
    target_warehouse_id = get_warehouse_id(app, "WH002")

    response = client.put(
        f"/locations/{source_location_id}",
        headers=auth_headers("admin", "Admin@123"),
        json={"warehouse_id": target_warehouse_id},
    )

    assert response.status_code == 409


def test_warehouse_and_location_crud_write_audit_log(client, auth_headers, app):
    create_warehouse = client.post(
        "/warehouses",
        headers=auth_headers("admin", "Admin@123"),
        json={
            "warehouse_code": "WH188",
            "warehouse_name": "Kho audit",
            "address": "188 Le Loi",
            "status": "active",
        },
    )
    assert create_warehouse.status_code == 201
    warehouse_id = create_warehouse.get_json()["item"]["id"]

    update_warehouse = client.put(
        f"/warehouses/{warehouse_id}",
        headers=auth_headers("admin", "Admin@123"),
        json={"warehouse_name": "Kho audit cap nhat"},
    )
    assert update_warehouse.status_code == 200

    warehouse_delete = client.delete(
        f"/warehouses/{warehouse_id}",
        headers=auth_headers("admin", "Admin@123"),
    )
    assert warehouse_delete.status_code == 200

    existing_warehouse_id = get_warehouse_id(app, "WH002")
    create_location = client.post(
        "/locations",
        headers=auth_headers("admin", "Admin@123"),
        json={
            "warehouse_id": existing_warehouse_id,
            "location_code": "L-88",
            "location_name": "Vi tri audit",
            "status": "active",
        },
    )
    assert create_location.status_code == 201
    location_id = create_location.get_json()["item"]["id"]

    update_location = client.put(
        f"/locations/{location_id}",
        headers=auth_headers("admin", "Admin@123"),
        json={"location_name": "Vi tri audit cap nhat"},
    )
    assert update_location.status_code == 200

    delete_location = client.delete(
        f"/locations/{location_id}",
        headers=auth_headers("admin", "Admin@123"),
    )
    assert delete_location.status_code == 200

    with app.app_context():
        actions = {
            log.action
            for log in AuditLog.query.filter(
                AuditLog.action.in_(
                    [
                        "warehouses.created",
                        "warehouses.updated",
                        "warehouses.deleted",
                        "locations.created",
                        "locations.updated",
                        "locations.deleted",
                    ]
                )
            ).all()
        }

    assert actions == {
        "warehouses.created",
        "warehouses.updated",
        "warehouses.deleted",
        "locations.created",
        "locations.updated",
        "locations.deleted",
    }
