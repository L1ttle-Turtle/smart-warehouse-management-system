from flask import Blueprint, abort, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy import or_
from sqlalchemy.orm import joinedload

from ..audit import log_audit_event
from ..extensions import db
from ..models import BankAccount, Customer, Invoice, Payment
from ..permissions import get_current_user, permission_required
from ..schemas import PaymentCreateSchema
from ..serializers import serialize_payment
from ..utils import generate_code, utc_now

payments_bp = Blueprint("payments", __name__)

PAYMENT_METHOD_VALUES = {"cash", "bank_transfer", "other"}
PAYMENT_SORT_FIELDS = {
    "payment_code": Payment.payment_code,
    "amount": Payment.amount,
    "payment_method": Payment.payment_method,
    "paid_at": Payment.paid_at,
    "created_at": Payment.created_at,
    "updated_at": Payment.updated_at,
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
    page = parse_positive_int_arg("page", 1)
    page_size = parse_positive_int_arg("page_size", 10)
    return page, page_size


def apply_sort(query):
    sort_by = normalize_optional_text(request.args.get("sort_by")) or "paid_at"
    sort_order = (request.args.get("sort_order") or "desc").strip().lower()

    if sort_by not in PAYMENT_SORT_FIELDS:
        abort(400, description="sort_by không hợp lệ.")
    if sort_order not in {"asc", "desc"}:
        abort(400, description="sort_order không hợp lệ.")

    column = PAYMENT_SORT_FIELDS[sort_by]
    if sort_order == "asc":
        return query.order_by(column.asc(), Payment.id.asc())
    return query.order_by(column.desc(), Payment.id.desc())


def build_pagination_payload(pagination):
    return {
        "items": [serialize_payment(item) for item in pagination.items],
        "total": pagination.total,
        "page": pagination.page,
        "page_size": pagination.per_page,
    }


def get_invoice_or_abort(invoice_id):
    invoice = (
        Invoice.query.options(
            joinedload(Invoice.customer),
            joinedload(Invoice.bank_account),
            joinedload(Invoice.payments),
        )
        .filter(Invoice.id == invoice_id)
        .first()
    )
    if not invoice:
        abort(400, description="Hóa đơn không hợp lệ.")
    return invoice


def validate_bank_account(bank_account_id):
    if bank_account_id is None:
        return None
    bank_account = db.session.get(BankAccount, bank_account_id)
    if not bank_account:
        abort(400, description="Tài khoản ngân hàng không hợp lệ.")
    if bank_account.status != "active":
        abort(400, description="Tài khoản ngân hàng đang ngừng hoạt động.")
    return bank_account


def calculate_paid_amount(invoice):
    return sum(float(payment.amount or 0) for payment in invoice.payments)


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


def normalize_payment_payload(payload):
    normalized_payload = dict(payload)
    normalized_payload["note"] = normalize_optional_text(payload.get("note"))
    normalized_payload["amount"] = float(payload["amount"])
    normalized_payload["payment_method"] = payload.get("payment_method") or "cash"
    return normalized_payload


def audit_payment_change(action, actor_user_id, payment):
    log_audit_event(
        action,
        "payment",
        f"Ghi nhận thanh toán {payment.payment_code} cho hóa đơn {payment.invoice.invoice_code}.",
        actor_user_id=actor_user_id,
        entity_id=payment.id,
        entity_label=payment.payment_code,
    )


@payments_bp.get("/payments")
@jwt_required()
@permission_required("invoices.view")
def list_payments():
    query = (
        Payment.query.join(Payment.invoice)
        .outerjoin(Invoice.customer)
        .options(
            joinedload(Payment.invoice).joinedload(Invoice.customer),
            joinedload(Payment.bank_account),
            joinedload(Payment.creator),
        )
    )

    search = normalize_optional_text(request.args.get("q")) or normalize_optional_text(
        request.args.get("search")
    )
    if search:
        like_term = f"%{search}%"
        query = query.filter(
            or_(
                Payment.payment_code.ilike(like_term),
                Payment.note.ilike(like_term),
                Invoice.invoice_code.ilike(like_term),
                Customer.customer_code.ilike(like_term),
                Customer.customer_name.ilike(like_term),
            )
        )

    invoice_id = parse_optional_int_arg("invoice_id")
    if invoice_id is not None:
        get_invoice_or_abort(invoice_id)
        query = query.filter(Payment.invoice_id == invoice_id)

    payment_method = normalize_optional_text(request.args.get("payment_method"))
    if payment_method:
        if payment_method not in PAYMENT_METHOD_VALUES:
            abort(400, description="payment_method không hợp lệ.")
        query = query.filter(Payment.payment_method == payment_method)

    page, page_size = get_pagination_params()
    pagination = apply_sort(query).paginate(page=page, per_page=page_size, error_out=False)
    return jsonify(build_pagination_payload(pagination))


@payments_bp.post("/payments")
@jwt_required()
@permission_required("invoices.manage")
def create_payment():
    current_user = get_current_user()
    payload = normalize_payment_payload(PaymentCreateSchema().load(request.get_json() or {}))

    invoice = get_invoice_or_abort(payload["invoice_id"])
    bank_account = validate_bank_account(payload.get("bank_account_id"))
    remaining_amount = calculate_remaining_amount(invoice)
    if remaining_amount <= EPSILON:
        abort(400, description="Hóa đơn đã thanh toán đủ.")
    if payload["amount"] - remaining_amount > EPSILON:
        abort(400, description="Số tiền thanh toán vượt quá số còn phải thu.")

    payment = Payment(
        payment_code=generate_code("PAY"),
        invoice=invoice,
        bank_account_id=bank_account.id if bank_account else None,
        created_by=current_user.id,
        amount=payload["amount"],
        payment_method=payload["payment_method"],
        paid_at=payload.get("paid_at") or utc_now(),
        note=payload.get("note"),
    )
    db.session.add(payment)
    db.session.flush()

    update_invoice_payment_status(invoice)
    audit_payment_change("payments.created", current_user.id, payment)
    db.session.commit()

    return jsonify({"item": serialize_payment(payment)}), 201


@payments_bp.get("/payments/<int:payment_id>")
@jwt_required()
@permission_required("invoices.view")
def get_payment(payment_id):
    payment = (
        Payment.query.options(
            joinedload(Payment.invoice).joinedload(Invoice.customer),
            joinedload(Payment.bank_account),
            joinedload(Payment.creator),
        )
        .filter(Payment.id == payment_id)
        .first_or_404()
    )
    return jsonify({"item": serialize_payment(payment)})
