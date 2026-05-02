from app.extensions import db
from app.models import Customer, ExportReceipt, ExportReceiptDetail, Product, Role, Shipment, User, Warehouse, WarehouseLocation
from app.services.inventory import confirm_export_receipt
from app.utils import utc_now


def get_seed_shipment_context(app):
    with app.app_context():
        shipment = Shipment.query.filter_by(shipment_code="SHP-DEMO-001").first()
        shipper = User.query.filter_by(username="shipper").first()
        return {
            "shipment_id": shipment.id,
            "shipment_code": shipment.shipment_code,
            "shipper_id": shipper.id,
        }


def create_confirmed_export_receipt(app, receipt_code, *, quantity=1):
    with app.app_context():
        manager_user = User.query.filter_by(username="manager").first()
        warehouse = Warehouse.query.filter_by(warehouse_code="WH001").first()
        customer = Customer.query.filter_by(customer_code="CUS001").first()
        product = Product.query.filter_by(product_code="PRD001").first()
        location = WarehouseLocation.query.filter_by(
            warehouse_id=warehouse.id if warehouse else None,
            location_code="A-01",
        ).first()

        receipt = ExportReceipt(
            receipt_code=receipt_code,
            warehouse_id=warehouse.id,
            customer_id=customer.id,
            created_by=manager_user.id,
            status="draft",
            note="Phieu xuat xac nhan de mo shipment test.",
        )
        receipt.details.append(
            ExportReceiptDetail(
                product_id=product.id,
                location_id=location.id,
                quantity=quantity,
            )
        )
        db.session.add(receipt)
        db.session.flush()
        confirm_export_receipt(receipt, manager_user.id)
        db.session.commit()

        return {
            "receipt_id": receipt.id,
            "manager_id": manager_user.id,
        }


def create_additional_shipper(app, username):
    with app.app_context():
        existing = User.query.filter_by(username=username).first()
        if existing:
            return existing.id

        shipper_role = Role.query.filter_by(role_name="shipper").first()
        user = User(
            username=username,
            full_name=f"{username.title()} User",
            email=f"{username}@warehouse.local",
            phone="0911000000",
            status="active",
            must_change_password=False,
            role=shipper_role,
        )
        user.set_password("Shipper@123")
        db.session.add(user)
        db.session.commit()
        return user.id


def create_shipment_direct(app, shipment_code, export_receipt_id, shipper_id):
    with app.app_context():
        manager_user = User.query.filter_by(username="manager").first()
        shipment = Shipment(
            shipment_code=shipment_code,
            export_receipt_id=export_receipt_id,
            shipper_id=shipper_id,
            created_by=manager_user.id,
            status="assigned",
            note="Shipment tao truc tiep cho case test phan quyen shipper.",
            assigned_at=utc_now(),
        )
        db.session.add(shipment)
        db.session.commit()
        return shipment.id


def test_seed_demo_contains_assigned_shipment(app):
    with app.app_context():
        shipment = Shipment.query.filter_by(shipment_code="SHP-DEMO-001").first()

        assert shipment is not None
        assert shipment.status == "assigned"
        assert shipment.export_receipt is not None
        assert shipment.export_receipt.status == "confirmed"


def test_manager_can_create_shipment_from_confirmed_export_receipt(client, auth_headers, app):
    context = create_confirmed_export_receipt(app, "EXP-SHP-TST-001")
    shipper_context = get_seed_shipment_context(app)

    response = client.post(
        "/shipments",
        headers=auth_headers("manager", "Manager@123"),
        json={
            "export_receipt_id": context["receipt_id"],
            "shipper_id": shipper_context["shipper_id"],
            "note": "Giao shipper chay tuyen noi thanh",
        },
    )

    assert response.status_code == 201
    payload = response.get_json()["item"]
    assert payload["status"] == "assigned"
    assert payload["export_receipt_id"] == context["receipt_id"]
    assert payload["shipper_id"] == shipper_context["shipper_id"]


def test_create_shipment_rejects_draft_export_receipt(client, auth_headers, app):
    with app.app_context():
        draft_receipt = ExportReceipt.query.filter_by(receipt_code="EXP-DEMO-001").first()
        shipper = User.query.filter_by(username="shipper").first()

    response = client.post(
        "/shipments",
        headers=auth_headers("admin", "Admin@123"),
        json={
            "export_receipt_id": draft_receipt.id,
            "shipper_id": shipper.id,
        },
    )

    assert response.status_code == 400


def test_shipper_only_sees_own_shipments(client, auth_headers, app):
    second_shipper_id = create_additional_shipper(app, "shipper2")
    receipt_context = create_confirmed_export_receipt(app, "EXP-SHP-TST-002")
    create_shipment_direct(app, "SHP-TST-002", receipt_context["receipt_id"], second_shipper_id)

    response = client.get("/shipments", headers=auth_headers("shipper", "Shipper@123"))

    assert response.status_code == 200
    shipment_codes = [item["shipment_code"] for item in response.get_json()["items"]]
    assert "SHP-DEMO-001" in shipment_codes
    assert "SHP-TST-002" not in shipment_codes


def test_shipper_can_update_own_shipment_but_not_other_shipments(client, auth_headers, app):
    seed_context = get_seed_shipment_context(app)
    own_response = client.post(
        f"/shipments/{seed_context['shipment_id']}/status",
        headers=auth_headers("shipper", "Shipper@123"),
        json={"status": "in_transit", "note": "Dang giao trong ca sang"},
    )

    assert own_response.status_code == 200
    assert own_response.get_json()["item"]["status"] == "in_transit"

    second_shipper_id = create_additional_shipper(app, "shipper3")
    receipt_context = create_confirmed_export_receipt(app, "EXP-SHP-TST-003")
    other_shipment_id = create_shipment_direct(app, "SHP-TST-003", receipt_context["receipt_id"], second_shipper_id)

    forbidden_response = client.post(
        f"/shipments/{other_shipment_id}/status",
        headers=auth_headers("shipper", "Shipper@123"),
        json={"status": "in_transit"},
    )

    assert forbidden_response.status_code == 403


def test_shipper_cannot_create_shipment(client, auth_headers, app):
    context = create_confirmed_export_receipt(app, "EXP-SHP-TST-004")
    shipper_context = get_seed_shipment_context(app)

    response = client.post(
        "/shipments",
        headers=auth_headers("shipper", "Shipper@123"),
        json={
            "export_receipt_id": context["receipt_id"],
            "shipper_id": shipper_context["shipper_id"],
        },
    )

    assert response.status_code == 403


def test_shipment_meta_returns_shippers_and_confirmed_receipts(client, auth_headers, app):
    context = create_confirmed_export_receipt(app, "EXP-SHP-TST-004A")

    response = client.get("/shipments/meta", headers=auth_headers("manager", "Manager@123"))

    assert response.status_code == 200
    payload = response.get_json()
    assert any(item["role_name"] == "shipper" for item in payload["shippers"])
    assert any(item["id"] == context["receipt_id"] for item in payload["export_receipts"])


def test_shipper_cannot_access_shipment_meta(client, auth_headers):
    response = client.get("/shipments/meta", headers=auth_headers("shipper", "Shipper@123"))

    assert response.status_code == 403


def test_shipment_status_transition_rules(client, auth_headers, app):
    context = create_confirmed_export_receipt(app, "EXP-SHP-TST-005")
    shipper_context = get_seed_shipment_context(app)

    create_response = client.post(
        "/shipments",
        headers=auth_headers("admin", "Admin@123"),
        json={
            "export_receipt_id": context["receipt_id"],
            "shipper_id": shipper_context["shipper_id"],
        },
    )
    shipment_id = create_response.get_json()["item"]["id"]

    invalid_response = client.post(
        f"/shipments/{shipment_id}/status",
        headers=auth_headers("shipper", "Shipper@123"),
        json={"status": "cancelled"},
    )
    assert invalid_response.status_code == 403

    delivered_response = client.post(
        f"/shipments/{shipment_id}/status",
        headers=auth_headers("manager", "Manager@123"),
        json={"status": "delivered"},
    )
    assert delivered_response.status_code == 200

    repeat_response = client.post(
        f"/shipments/{shipment_id}/status",
        headers=auth_headers("manager", "Manager@123"),
        json={"status": "cancelled"},
    )
    assert repeat_response.status_code == 400


def test_shipment_permission_matrix(client, auth_headers):
    admin_response = client.get("/shipments", headers=auth_headers("admin", "Admin@123"))
    manager_response = client.get("/shipments", headers=auth_headers("manager", "Manager@123"))
    staff_response = client.get("/shipments", headers=auth_headers("staff", "Staff@123"))
    shipper_response = client.get("/shipments", headers=auth_headers("shipper", "Shipper@123"))
    accountant_response = client.get("/shipments", headers=auth_headers("accountant", "Accountant@123"))

    assert admin_response.status_code == 200
    assert manager_response.status_code == 200
    assert staff_response.status_code == 200
    assert shipper_response.status_code == 200
    assert accountant_response.status_code == 403
