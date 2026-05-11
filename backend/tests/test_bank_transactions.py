from app.extensions import db
from app.models import BankTransactionLog, Invoice, Payment


def test_bank_transaction_list_returns_seeded_demo_items(client, auth_headers):
    response = client.get(
        "/bank-transactions?page=1&page_size=10&sort_by=transaction_code&sort_order=asc",
        headers=auth_headers("accountant", "Accountant@123"),
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["total"] >= 2
    assert any(item["transaction_code"] == "BNK-DEMO-001" for item in payload["items"])


def test_simulate_bank_transaction_matches_invoice_code(client, auth_headers, app):
    response = client.post(
        "/bank-transactions/simulate",
        headers=auth_headers("accountant", "Accountant@123"),
        json={
            "invoice_code": "INV-DEMO-001",
            "amount": 250000,
            "description": "Khach thanh toan them cho INV-DEMO-001",
            "note": "Giao dich test tu automation",
        },
    )

    assert response.status_code == 201
    payload = response.get_json()["item"]
    assert payload["invoice_code"] == "INV-DEMO-001"
    assert payload["status"] == "matched"

    with app.app_context():
        transaction = BankTransactionLog.query.filter_by(
            transaction_code=payload["transaction_code"]
        ).first()
        assert transaction is not None
        assert transaction.invoice is not None


def test_simulate_bank_transaction_without_invoice_stays_pending(client, auth_headers):
    response = client.post(
        "/bank-transactions/simulate",
        headers=auth_headers("manager", "Manager@123"),
        json={
            "amount": 180000,
            "description": "Khach chuyen khoan thieu noi dung hoa don",
        },
    )

    assert response.status_code == 201
    payload = response.get_json()["item"]
    assert payload["invoice_id"] is None
    assert payload["status"] == "pending"


def test_reconcile_bank_transaction_creates_payment_and_updates_invoice(client, auth_headers, app):
    with app.app_context():
        transaction = BankTransactionLog.query.filter_by(transaction_code="BNK-DEMO-003").first()
        transaction_id = transaction.id
        invoice_id = transaction.invoice_id
        amount = transaction.amount

    response = client.post(
        f"/bank-transactions/{transaction_id}/reconcile",
        headers=auth_headers("accountant", "Accountant@123"),
        json={"note": "Doi soat tu giao dich ngan hang demo"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["item"]["status"] == "reconciled"
    assert payload["payment_id"]

    with app.app_context():
        invoice = db.session.get(Invoice, invoice_id)
        payment = Payment.query.filter_by(invoice_id=invoice_id, amount=amount).first()
        transaction = BankTransactionLog.query.filter_by(transaction_code="BNK-DEMO-003").first()

        assert payment is not None
        assert payment.payment_method == "bank_transfer"
        assert invoice.status in {"partial", "paid"}
        assert transaction.status == "reconciled"
        assert transaction.reconciled_by is not None


def test_reconcile_bank_transaction_rejects_pending_or_overpayment(client, auth_headers, app):
    with app.app_context():
        pending_transaction = BankTransactionLog.query.filter_by(
            transaction_code="BNK-DEMO-002"
        ).first()
        invoice = Invoice.query.filter_by(invoice_code="INV-DEMO-001").first()
        pending_transaction_id = pending_transaction.id
        invoice_code = invoice.invoice_code
        overpay_amount = invoice.total_amount + 1

    pending_response = client.post(
        f"/bank-transactions/{pending_transaction_id}/reconcile",
        headers=auth_headers("accountant", "Accountant@123"),
        json={},
    )
    assert pending_response.status_code == 400

    simulate_response = client.post(
        "/bank-transactions/simulate",
        headers=auth_headers("admin", "Admin@123"),
        json={
            "invoice_code": invoice_code,
            "amount": overpay_amount,
            "description": f"Thanh toan vuot qua {invoice_code}",
        },
    )
    transaction_id = simulate_response.get_json()["item"]["id"]

    overpay_response = client.post(
        f"/bank-transactions/{transaction_id}/reconcile",
        headers=auth_headers("admin", "Admin@123"),
        json={},
    )
    assert overpay_response.status_code == 400


def test_bank_transaction_permission_matrix(client, auth_headers):
    assert client.get(
        "/bank-transactions",
        headers=auth_headers("admin", "Admin@123"),
    ).status_code == 200
    assert client.get(
        "/bank-transactions",
        headers=auth_headers("accountant", "Accountant@123"),
    ).status_code == 200
    assert client.get(
        "/bank-transactions",
        headers=auth_headers("staff", "Staff@123"),
    ).status_code == 403

    response = client.post(
        "/bank-transactions/simulate",
        headers=auth_headers("staff", "Staff@123"),
        json={"amount": 100000, "description": "staff khong duoc doi soat"},
    )
    assert response.status_code == 403
