from app.extensions import db
from app.models import (
    AuditLog,
    BankAccount,
    Customer,
    ExportReceipt,
    ExportReceiptDetail,
    Invoice,
    Payment,
    Product,
    User,
    Warehouse,
    WarehouseLocation,
)
from app.services.inventory import confirm_export_receipt


def get_invoice_seed_context(app):
    with app.app_context():
        invoice = Invoice.query.filter_by(invoice_code="INV-DEMO-001").first()
        return {
            "invoice_id": invoice.id,
            "invoice_code": invoice.invoice_code,
            "status": invoice.status,
        }


def create_confirmed_export_receipt(app, receipt_code, *, with_customer=True, quantity=1):
    with app.app_context():
        manager_user = User.query.filter_by(username="manager").first()
        warehouse = Warehouse.query.filter_by(warehouse_code="WH001").first()
        customer = Customer.query.filter_by(customer_code="CUS003").first() if with_customer else None
        product = Product.query.filter_by(product_code="PRD001").first()
        location = WarehouseLocation.query.filter_by(
            warehouse_id=warehouse.id if warehouse else None,
            location_code="A-01",
        ).first()

        receipt = ExportReceipt(
            receipt_code=receipt_code,
            warehouse_id=warehouse.id,
            customer_id=customer.id if customer else None,
            created_by=manager_user.id,
            status="draft",
            note="Phieu xuat xac nhan de test hoa don toi thieu.",
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
            "detail_ids": [detail.id for detail in receipt.details],
        }


def test_seed_demo_contains_unpaid_invoice(app):
    with app.app_context():
        invoice = Invoice.query.filter_by(invoice_code="INV-DEMO-001").first()

        assert invoice is not None
        assert invoice.status == "unpaid"
        assert len(invoice.details) >= 1
        assert invoice.total_amount > 0


def test_accountant_can_create_invoice_from_confirmed_export_receipt(client, auth_headers, app):
    context = create_confirmed_export_receipt(app, "EXP-INV-TST-001")
    with app.app_context():
        bank_account = BankAccount.query.filter_by(account_number="0123456789").first()

    response = client.post(
        "/invoices",
        headers=auth_headers("accountant", "Accountant@123"),
        json={
            "export_receipt_id": context["receipt_id"],
            "bank_account_id": bank_account.id,
            "note": "Lap hoa don test cho khach hang doanh nghiep",
            "items": [
                {
                    "export_receipt_detail_id": context["detail_ids"][0],
                    "unit_price": 1850000,
                },
            ],
        },
    )

    assert response.status_code == 201
    payload = response.get_json()["item"]
    assert payload["status"] == "unpaid"
    assert payload["export_receipt_id"] == context["receipt_id"]
    assert payload["total_amount"] == 1850000

    with app.app_context():
        invoice = Invoice.query.filter_by(id=payload["id"]).first()
        audit_actions = {
            log.action
            for log in AuditLog.query.filter(
                AuditLog.entity_type == "invoice",
                AuditLog.entity_id == invoice.id,
            ).all()
        }

        assert invoice is not None
        assert len(invoice.details) == 1
        assert audit_actions == {"invoices.created"}


def test_create_invoice_rejects_draft_export_receipt(client, auth_headers, app):
    with app.app_context():
        draft_receipt = ExportReceipt.query.filter_by(receipt_code="EXP-DEMO-001").first()
        draft_receipt_id = draft_receipt.id
        draft_detail_id = draft_receipt.details[0].id

    response = client.post(
        "/invoices",
        headers=auth_headers("manager", "Manager@123"),
        json={
            "export_receipt_id": draft_receipt_id,
            "items": [],
        },
    )

    assert response.status_code == 422

    response = client.post(
        "/invoices",
        headers=auth_headers("manager", "Manager@123"),
        json={
            "export_receipt_id": draft_receipt_id,
            "items": [
                {
                    "export_receipt_detail_id": draft_detail_id,
                    "unit_price": 100000,
                },
            ],
        },
    )

    assert response.status_code == 400


def test_create_invoice_rejects_confirmed_receipt_without_customer(client, auth_headers, app):
    context = create_confirmed_export_receipt(app, "EXP-INV-TST-002", with_customer=False)

    response = client.post(
        "/invoices",
        headers=auth_headers("admin", "Admin@123"),
        json={
            "export_receipt_id": context["receipt_id"],
            "items": [
                {
                    "export_receipt_detail_id": context["detail_ids"][0],
                    "unit_price": 950000,
                },
            ],
        },
    )

    assert response.status_code == 400


def test_create_invoice_cannot_duplicate_same_export_receipt(client, auth_headers, app):
    context = create_confirmed_export_receipt(app, "EXP-INV-TST-003")

    payload = {
        "export_receipt_id": context["receipt_id"],
        "items": [
            {
                "export_receipt_detail_id": context["detail_ids"][0],
                "unit_price": 550000,
            },
        ],
    }

    first_response = client.post(
        "/invoices",
        headers=auth_headers("accountant", "Accountant@123"),
        json=payload,
    )
    second_response = client.post(
        "/invoices",
        headers=auth_headers("accountant", "Accountant@123"),
        json=payload,
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409


def test_invoice_list_supports_status_and_search_filters(client, auth_headers):
    response = client.get(
        "/invoices?page=1&page_size=10&status=unpaid&search=INV-DEMO-001&sort_by=invoice_code&sort_order=asc",
        headers=auth_headers("manager", "Manager@123"),
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["total"] >= 1
    assert any(item["invoice_code"] == "INV-DEMO-001" for item in payload["items"])
    assert all(item["status"] == "unpaid" for item in payload["items"])


def test_invoice_permission_matrix(client, auth_headers):
    admin_response = client.get("/invoices", headers=auth_headers("admin", "Admin@123"))
    manager_response = client.get("/invoices", headers=auth_headers("manager", "Manager@123"))
    accountant_response = client.get("/invoices", headers=auth_headers("accountant", "Accountant@123"))
    staff_response = client.get("/invoices", headers=auth_headers("staff", "Staff@123"))
    shipper_response = client.get("/invoices", headers=auth_headers("shipper", "Shipper@123"))

    assert admin_response.status_code == 200
    assert manager_response.status_code == 200
    assert accountant_response.status_code == 200
    assert staff_response.status_code == 403
    assert shipper_response.status_code == 403


def test_accountant_can_record_partial_payment_and_update_invoice_status(client, auth_headers, app):
    with app.app_context():
        invoice = Invoice.query.filter_by(invoice_code="INV-DEMO-001").first()
        invoice_id = invoice.id
        partial_amount = invoice.total_amount / 2

    response = client.post(
        "/payments",
        headers=auth_headers("accountant", "Accountant@123"),
        json={
            "invoice_id": invoice_id,
            "amount": partial_amount,
            "payment_method": "cash",
            "note": "Thu mot phan tien hoa don demo",
        },
    )

    assert response.status_code == 201
    payload = response.get_json()["item"]
    assert payload["invoice_id"] == invoice_id
    assert payload["amount"] == partial_amount

    invoice_response = client.get(
        f"/invoices/{invoice_id}",
        headers=auth_headers("accountant", "Accountant@123"),
    )
    invoice_payload = invoice_response.get_json()["item"]
    assert invoice_payload["status"] == "partial"
    assert invoice_payload["paid_amount"] == partial_amount
    assert invoice_payload["remaining_amount"] == partial_amount
    assert len(invoice_payload["payments"]) == 1

    with app.app_context():
        invoice = db.session.get(Invoice, invoice_id)
        payment = Payment.query.filter_by(invoice_id=invoice_id).first()
        audit_actions = {
            log.action
            for log in AuditLog.query.filter(
                AuditLog.entity_type == "payment",
                AuditLog.entity_id == payment.id,
            ).all()
        }

        assert invoice.status == "partial"
        assert audit_actions == {"payments.created"}


def test_payment_can_mark_invoice_paid(client, auth_headers, app):
    with app.app_context():
        invoice = Invoice.query.filter_by(invoice_code="INV-DEMO-001").first()
        invoice_id = invoice.id
        total_amount = invoice.total_amount

    response = client.post(
        "/payments",
        headers=auth_headers("manager", "Manager@123"),
        json={
            "invoice_id": invoice_id,
            "amount": total_amount,
            "payment_method": "bank_transfer",
        },
    )

    assert response.status_code == 201
    with app.app_context():
        invoice = db.session.get(Invoice, invoice_id)
        assert invoice.status == "paid"
        assert len(invoice.payments) == 1
        assert invoice.payments[0].amount == total_amount


def test_payment_rejects_overpayment(client, auth_headers, app):
    with app.app_context():
        invoice = Invoice.query.filter_by(invoice_code="INV-DEMO-001").first()
        invoice_id = invoice.id
        over_amount = invoice.total_amount + 1

    response = client.post(
        "/payments",
        headers=auth_headers("accountant", "Accountant@123"),
        json={
            "invoice_id": invoice_id,
            "amount": over_amount,
        },
    )

    assert response.status_code == 400
    with app.app_context():
        invoice = db.session.get(Invoice, invoice_id)
        assert invoice.status == "unpaid"
        assert Payment.query.filter_by(invoice_id=invoice_id).count() == 0


def test_payment_list_supports_invoice_filter(client, auth_headers, app):
    with app.app_context():
        invoice = Invoice.query.filter_by(invoice_code="INV-DEMO-001").first()
        invoice_id = invoice.id
        amount = invoice.total_amount / 3

    create_response = client.post(
        "/payments",
        headers=auth_headers("admin", "Admin@123"),
        json={
            "invoice_id": invoice_id,
            "amount": amount,
            "payment_method": "other",
            "note": "Thu tien test filter thanh toan",
        },
    )
    assert create_response.status_code == 201
    payment_code = create_response.get_json()["item"]["payment_code"]

    response = client.get(
        f"/payments?invoice_id={invoice_id}&search={payment_code}&payment_method=other",
        headers=auth_headers("accountant", "Accountant@123"),
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["total"] == 1
    assert payload["items"][0]["payment_code"] == payment_code


def test_payment_permission_matrix(client, auth_headers, app):
    with app.app_context():
        invoice = Invoice.query.filter_by(invoice_code="INV-DEMO-001").first()
        invoice_id = invoice.id

    assert client.get("/payments", headers=auth_headers("admin", "Admin@123")).status_code == 200
    assert client.get("/payments", headers=auth_headers("manager", "Manager@123")).status_code == 200
    assert (
        client.get("/payments", headers=auth_headers("accountant", "Accountant@123")).status_code
        == 200
    )
    assert client.get("/payments", headers=auth_headers("staff", "Staff@123")).status_code == 403
    assert client.get("/payments", headers=auth_headers("shipper", "Shipper@123")).status_code == 403

    response = client.post(
        "/payments",
        headers=auth_headers("staff", "Staff@123"),
        json={"invoice_id": invoice_id, "amount": 1000},
    )
    assert response.status_code == 403
