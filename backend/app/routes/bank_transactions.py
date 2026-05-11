from flask import Blueprint, abort, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy import or_
from sqlalchemy.orm import joinedload

from ..audit import log_audit_event
from ..extensions import db
from ..models import BankAccount, BankTransactionLog, Invoice, Payment
from ..permissions import get_current_user, permission_required
from ..schemas import BankTransactionReconcileSchema, BankTransactionSimulateSchema
from ..serializers import serialize_bank_transaction
from ..utils import generate_code, utc_now

bank_transactions_bp = Blueprint("bank_transactions", __name__)

BANK_TRANSACTION_STATUS_VALUES = {"pending", "matched", "reconciled", "ignored"}
BANK_TRANSACTION_SORT_FIELDS = {
    "transaction_code": BankTransactionLog.transaction_code,
    "amount": BankTransactionLog.amount,
    "status": BankTransactionLog.status,
    "received_at": BankTransactionLog.received_at,
    "created_at": BankTransactionLog.created_at,
    "updated_at": BankTransactionLog.updated_at,
}
EPSILON = 0.000001


def normalize_optional_text(value):
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return value


def parse_optional_int_arg(name):
    raw_value = request.args.get(name)
    if raw_value is None:
        return None

    raw_value = raw_value.strip()
    if not raw_value:
        abort(400, description=f"{name} phải là số nguyên hợp lệ.")

    try:
        return int(raw_value)
    except ValueError:
        abort(400, description=f"{name} phải là số nguyên hợp lệ.")


def parse_positive_int_arg(name, default, *, minimum=1, maximum=100):
    raw_value = request.args.get(name)
    if raw_value is None:
        return default

    raw_value = raw_value.strip()
    if not raw_value:
        abort(400, description=f"{name} phải là số nguyên hợp lệ.")

    try:
        parsed_value = int(raw_value)
    except ValueError:
        abort(400, description=f"{name} phải là số nguyên hợp lệ.")

    if parsed_value < minimum or parsed_value > maximum:
        abort(400, description=f"{name} phải nằm trong khoảng {minimum}-{maximum}.")
    return parsed_value


def get_pagination_params():
    return parse_positive_int_arg("page", 1), parse_positive_int_arg("page_size", 10)


def apply_sort(query):
    sort_by = normalize_optional_text(request.args.get("sort_by")) or "received_at"
    sort_order = (request.args.get("sort_order") or "desc").strip().lower()

    if sort_by not in BANK_TRANSACTION_SORT_FIELDS:
        abort(400, description="sort_by không hợp lệ.")
    if sort_order not in {"asc", "desc"}:
        abort(400, description="sort_order không hợp lệ.")

    column = BANK_TRANSACTION_SORT_FIELDS[sort_by]
    if sort_order == "asc":
        return query.order_by(column.asc(), BankTransactionLog.id.asc())
    return query.order_by(column.desc(), BankTransactionLog.id.desc())


def build_pagination_payload(pagination):
    return {
        "items": [serialize_bank_transaction(item) for item in pagination.items],
        "total": pagination.total,
        "page": pagination.page,
        "page_size": pagination.per_page,
    }


def calculate_paid_amount(invoice):
    return float(
        db.session.query(db.func.coalesce(db.func.sum(Payment.amount), 0))
        .filter(Payment.invoice_id == invoice.id)
        .scalar()
        or 0
    )


def calculate_remaining_amount(invoice):
    return max(float(invoice.total_amount or 0) - calculate_paid_amount(invoice), 0)


def update_invoice_payment_status(invoice):
    paid_amount = calculate_paid_amount(invoice)
    total_amount = float(invoice.total_amount or 0)
    if paid_amount <= EPSILON:
        invoice.status = "unpaid"
    elif paid_amount + EPSILON >= total_amount:
        invoice.status = "paid"
    else:
        invoice.status = "partial"


def validate_bank_account(bank_account_id):
    if bank_account_id is None:
        return None
    bank_account = db.session.get(BankAccount, bank_account_id)
    if not bank_account:
        abort(400, description="Tài khoản ngân hàng không hợp lệ.")
    if bank_account.status != "active":
        abort(400, description="Tài khoản ngân hàng đang ngừng hoạt động.")
    return bank_account


def find_invoice_for_payload(payload):
    invoice_code = normalize_optional_text(payload.get("invoice_code"))
    if invoice_code:
        return Invoice.query.filter_by(invoice_code=invoice_code).first()

    description = payload.get("description") or ""
    for invoice in Invoice.query.order_by(Invoice.created_at.desc()).all():
        if invoice.invoice_code and invoice.invoice_code in description:
            return invoice
    return None


def audit_bank_transaction(action, actor_user_id, transaction):
    log_audit_event(
        action,
        "bank_transaction",
        f"{action.split('.')[1].capitalize()} giao dịch ngân hàng {transaction.transaction_code}.",
        actor_user_id=actor_user_id,
        entity_id=transaction.id,
        entity_label=transaction.transaction_code,
    )


@bank_transactions_bp.get("/bank-transactions")
@jwt_required()
@permission_required("invoices.view")
def list_bank_transactions():
    query = BankTransactionLog.query.outerjoin(BankTransactionLog.invoice).options(
        joinedload(BankTransactionLog.invoice),
        joinedload(BankTransactionLog.bank_account),
        joinedload(BankTransactionLog.creator),
        joinedload(BankTransactionLog.reconciler),
    )

    search = normalize_optional_text(request.args.get("q")) or normalize_optional_text(
        request.args.get("search")
    )
    if search:
        like_term = f"%{search}%"
        query = query.filter(
            or_(
                BankTransactionLog.transaction_code.ilike(like_term),
                BankTransactionLog.description.ilike(like_term),
                BankTransactionLog.note.ilike(like_term),
                Invoice.invoice_code.ilike(like_term),
            )
        )

    status = normalize_optional_text(request.args.get("status"))
    if status:
        if status not in BANK_TRANSACTION_STATUS_VALUES:
            abort(400, description="status không hợp lệ.")
        query = query.filter(BankTransactionLog.status == status)

    invoice_id = parse_optional_int_arg("invoice_id")
    if invoice_id is not None:
        invoice = db.session.get(Invoice, invoice_id)
        if not invoice:
            abort(400, description="Hóa đơn không hợp lệ.")
        query = query.filter(BankTransactionLog.invoice_id == invoice_id)

    page, page_size = get_pagination_params()
    pagination = apply_sort(query).paginate(page=page, per_page=page_size, error_out=False)
    return jsonify(build_pagination_payload(pagination))


@bank_transactions_bp.post("/bank-transactions/simulate")
@jwt_required()
@permission_required("invoices.manage")
def simulate_bank_transaction():
    current_user = get_current_user()
    payload = BankTransactionSimulateSchema().load(request.get_json() or {})
    payload["description"] = payload["description"].strip()
    payload["note"] = normalize_optional_text(payload.get("note"))
    payload["amount"] = float(payload["amount"])

    bank_account = validate_bank_account(payload.get("bank_account_id"))
    invoice = find_invoice_for_payload(payload)
    transaction = BankTransactionLog(
        transaction_code=generate_code("BNK"),
        invoice_id=invoice.id if invoice else None,
        bank_account_id=bank_account.id if bank_account else None,
        created_by=current_user.id,
        amount=payload["amount"],
        description=payload["description"],
        status="matched" if invoice else "pending",
        received_at=payload.get("received_at") or utc_now(),
        note=payload.get("note"),
    )
    db.session.add(transaction)
    db.session.flush()
    audit_bank_transaction("bank_transactions.simulated", current_user.id, transaction)
    db.session.commit()
    return jsonify({"item": serialize_bank_transaction(transaction)}), 201


@bank_transactions_bp.post("/bank-transactions/<int:transaction_id>/reconcile")
@jwt_required()
@permission_required("invoices.manage")
def reconcile_bank_transaction(transaction_id):
    current_user = get_current_user()
    payload = BankTransactionReconcileSchema().load(request.get_json() or {})
    transaction = (
        BankTransactionLog.query.options(
            joinedload(BankTransactionLog.invoice).joinedload(Invoice.payments),
            joinedload(BankTransactionLog.bank_account),
        )
        .filter(BankTransactionLog.id == transaction_id)
        .first_or_404()
    )
    if transaction.status == "reconciled":
        abort(400, description="Giao dịch này đã được đối soát.")
    if not transaction.invoice:
        abort(400, description="Giao dịch chưa khớp hóa đơn nên chưa thể đối soát.")

    remaining_amount = calculate_remaining_amount(transaction.invoice)
    if remaining_amount <= EPSILON:
        abort(400, description="Hóa đơn đã thanh toán đủ.")
    if float(transaction.amount or 0) - remaining_amount > EPSILON:
        abort(400, description="Số tiền giao dịch vượt quá số còn phải thu của hóa đơn.")

    payment = Payment(
        payment_code=generate_code("PAY"),
        invoice_id=transaction.invoice_id,
        bank_account_id=transaction.bank_account_id or transaction.invoice.bank_account_id,
        created_by=current_user.id,
        amount=float(transaction.amount),
        payment_method="bank_transfer",
        paid_at=transaction.received_at,
        note=normalize_optional_text(payload.get("note")) or f"Đối soát từ {transaction.transaction_code}",
    )
    db.session.add(payment)
    db.session.flush()

    transaction.status = "reconciled"
    transaction.reconciled_by = current_user.id
    transaction.reconciled_at = utc_now()
    transaction.note = normalize_optional_text(payload.get("note")) or transaction.note
    update_invoice_payment_status(transaction.invoice)
    audit_bank_transaction("bank_transactions.reconciled", current_user.id, transaction)
    db.session.commit()
    return jsonify(
        {
            "item": serialize_bank_transaction(transaction),
            "payment_id": payment.id,
            "invoice_status": transaction.invoice.status,
        }
    )
