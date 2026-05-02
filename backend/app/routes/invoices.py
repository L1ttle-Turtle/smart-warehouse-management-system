from flask import Blueprint, abort, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy import or_
from sqlalchemy.orm import joinedload

from ..audit import log_audit_event
from ..extensions import db
from ..models import (
    BankAccount,
    Customer,
    ExportReceipt,
    ExportReceiptDetail,
    Invoice,
    InvoiceDetail,
    Payment,
    Warehouse,
)
from ..permissions import get_current_user, permission_required
from ..schemas import InvoiceCreateSchema
from ..serializers import serialize_bank_account, serialize_export_receipt, serialize_invoice
from ..utils import generate_code, utc_now

invoices_bp = Blueprint("invoices", __name__)


INVOICE_SORT_FIELDS = {
    "invoice_code": Invoice.invoice_code,
    "status": Invoice.status,
    "total_amount": Invoice.total_amount,
    "issued_at": Invoice.issued_at,
    "created_at": Invoice.created_at,
    "updated_at": Invoice.updated_at,
}

INVOICE_STATUS_VALUES = {"unpaid", "partial", "paid"}


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
    sort_by = normalize_optional_text(request.args.get("sort_by")) or "created_at"
    sort_order = (request.args.get("sort_order") or "desc").strip().lower()

    if sort_by not in INVOICE_SORT_FIELDS:
        abort(400, description="sort_by không hợp lệ.")
    if sort_order not in {"asc", "desc"}:
        abort(400, description="sort_order không hợp lệ.")

    column = INVOICE_SORT_FIELDS[sort_by]
    if sort_order == "asc":
        return query.order_by(column.asc(), Invoice.id.asc())
    return query.order_by(column.desc(), Invoice.id.desc())


def build_pagination_payload(pagination):
    return {
        "items": [serialize_invoice(item) for item in pagination.items],
        "total": pagination.total,
        "page": pagination.page,
        "page_size": pagination.per_page,
    }


def validate_customer(customer_id):
    customer = db.session.get(Customer, customer_id)
    if not customer:
        abort(400, description="Khách hàng không hợp lệ.")
    return customer


def validate_bank_account(bank_account_id):
    if bank_account_id is None:
        return None
    bank_account = db.session.get(BankAccount, bank_account_id)
    if not bank_account:
        abort(400, description="Tài khoản ngân hàng không hợp lệ.")
    if bank_account.status != "active":
        abort(400, description="Tài khoản ngân hàng đang ngừng hoạt động.")
    return bank_account


def validate_export_receipt(export_receipt_id):
    receipt = db.session.get(ExportReceipt, export_receipt_id)
    if not receipt:
        abort(400, description="Phiếu xuất không hợp lệ.")
    return receipt


def validate_confirmed_export_receipt_for_invoice(export_receipt_id):
    receipt = validate_export_receipt(export_receipt_id)
    if receipt.status != "confirmed":
        abort(400, description="Chỉ có thể tạo hóa đơn từ phiếu xuất đã xác nhận.")
    if not receipt.customer_id:
        abort(400, description="Phiếu xuất chưa gắn khách hàng nên chưa thể tạo hóa đơn.")
    if receipt.invoice:
        abort(409, description="Phiếu xuất này đã có hóa đơn.")
    return receipt


def normalize_invoice_payload(payload):
    normalized_payload = dict(payload)
    normalized_payload["note"] = normalize_optional_text(payload.get("note"))
    normalized_payload["items"] = [
        {
            "export_receipt_detail_id": item["export_receipt_detail_id"],
            "unit_price": float(item["unit_price"]),
        }
        for item in payload.get("items", [])
    ]
    return normalized_payload


def build_invoice_detail_values(receipt, pricing_items):
    if not receipt.details:
        abort(400, description="Phiếu xuất chưa có dòng chi tiết để lập hóa đơn.")

    pricing_map = {}
    for item in pricing_items:
        detail_id = item["export_receipt_detail_id"]
        if detail_id in pricing_map:
            abort(400, description="Không được trùng dòng phiếu xuất trong cùng hóa đơn.")
        pricing_map[detail_id] = item["unit_price"]

    receipt_detail_ids = {detail.id for detail in receipt.details}
    if set(pricing_map) != receipt_detail_ids:
        abort(400, description="Cần khai báo đơn giá cho đầy đủ các dòng của phiếu xuất.")

    detail_values = []
    total_amount = 0.0
    for detail in receipt.details:
        unit_price = pricing_map[detail.id]
        line_total = float(detail.quantity) * float(unit_price)
        total_amount += line_total
        detail_values.append(
            {
                "export_receipt_detail_id": detail.id,
                "product_id": detail.product_id,
                "location_id": detail.location_id,
                "quantity": float(detail.quantity),
                "unit_price": float(unit_price),
                "line_total": float(line_total),
            }
        )
    return detail_values, float(total_amount)


def audit_invoice_change(action, actor_user_id, invoice):
    log_audit_event(
        action,
        "invoice",
        f"{action.split('.')[1].capitalize()} hóa đơn {invoice.invoice_code}.",
        actor_user_id=actor_user_id,
        entity_id=invoice.id,
        entity_label=invoice.invoice_code,
    )


@invoices_bp.get("/invoices/meta")
@jwt_required()
@permission_required("invoices.manage")
def invoice_meta():
    bank_accounts = (
        BankAccount.query.filter_by(status="active")
        .order_by(BankAccount.bank_name.asc(), BankAccount.account_number.asc())
        .all()
    )
    confirmed_receipts = (
        ExportReceipt.query.filter_by(status="confirmed")
        .filter(ExportReceipt.customer_id.isnot(None))
        .outerjoin(Invoice, Invoice.export_receipt_id == ExportReceipt.id)
        .filter(Invoice.id.is_(None))
        .order_by(ExportReceipt.confirmed_at.desc(), ExportReceipt.created_at.desc())
        .all()
    )
    return jsonify(
        {
            "bank_accounts": [serialize_bank_account(item) for item in bank_accounts],
            "export_receipts": [serialize_export_receipt(item) for item in confirmed_receipts],
        }
    )


@invoices_bp.get("/invoices")
@jwt_required()
@permission_required("invoices.view")
def list_invoices():
    query = (
        Invoice.query.join(Invoice.export_receipt)
        .join(ExportReceipt.warehouse)
        .join(Invoice.customer)
        .options(
            joinedload(Invoice.export_receipt).joinedload(ExportReceipt.warehouse),
            joinedload(Invoice.customer),
            joinedload(Invoice.bank_account),
            joinedload(Invoice.creator),
            joinedload(Invoice.details).joinedload(InvoiceDetail.product),
            joinedload(Invoice.details).joinedload(InvoiceDetail.location),
            joinedload(Invoice.payments).joinedload(Payment.bank_account),
            joinedload(Invoice.payments).joinedload(Payment.creator),
        )
    )

    search = normalize_optional_text(request.args.get("q")) or normalize_optional_text(
        request.args.get("search")
    )
    if search:
        like_term = f"%{search}%"
        query = query.filter(
            or_(
                Invoice.invoice_code.ilike(like_term),
                Invoice.note.ilike(like_term),
                ExportReceipt.receipt_code.ilike(like_term),
                Customer.customer_code.ilike(like_term),
                Customer.customer_name.ilike(like_term),
                Warehouse.warehouse_code.ilike(like_term),
                Warehouse.warehouse_name.ilike(like_term),
            )
        )

    status = normalize_optional_text(request.args.get("status"))
    if status:
        if status not in INVOICE_STATUS_VALUES:
            abort(400, description="status không hợp lệ.")
        query = query.filter(Invoice.status == status)

    customer_id = parse_optional_int_arg("customer_id")
    if customer_id is not None:
        validate_customer(customer_id)
        query = query.filter(Invoice.customer_id == customer_id)

    export_receipt_id = parse_optional_int_arg("export_receipt_id")
    if export_receipt_id is not None:
        validate_export_receipt(export_receipt_id)
        query = query.filter(Invoice.export_receipt_id == export_receipt_id)

    page, page_size = get_pagination_params()
    pagination = apply_sort(query).paginate(page=page, per_page=page_size, error_out=False)
    return jsonify(build_pagination_payload(pagination))


@invoices_bp.post("/invoices")
@jwt_required()
@permission_required("invoices.manage")
def create_invoice():
    current_user = get_current_user()
    payload = normalize_invoice_payload(InvoiceCreateSchema().load(request.get_json() or {}))

    receipt = validate_confirmed_export_receipt_for_invoice(payload["export_receipt_id"])
    validate_customer(receipt.customer_id)
    bank_account = validate_bank_account(payload.get("bank_account_id"))
    detail_values, total_amount = build_invoice_detail_values(receipt, payload["items"])

    invoice = Invoice(
        invoice_code=generate_code("INV"),
        export_receipt_id=receipt.id,
        customer_id=receipt.customer_id,
        bank_account_id=bank_account.id if bank_account else None,
        created_by=current_user.id,
        status="unpaid",
        note=payload.get("note"),
        issued_at=utc_now(),
        total_amount=total_amount,
    )
    db.session.add(invoice)
    db.session.flush()

    for item in detail_values:
        invoice.details.append(InvoiceDetail(**item))

    audit_invoice_change("invoices.created", current_user.id, invoice)
    db.session.commit()
    return jsonify({"item": serialize_invoice(invoice)}), 201


@invoices_bp.get("/invoices/<int:invoice_id>")
@jwt_required()
@permission_required("invoices.view")
def get_invoice(invoice_id):
    invoice = (
        Invoice.query.options(
            joinedload(Invoice.export_receipt).joinedload(ExportReceipt.warehouse),
            joinedload(Invoice.customer),
            joinedload(Invoice.bank_account),
            joinedload(Invoice.creator),
            joinedload(Invoice.details).joinedload(InvoiceDetail.product),
            joinedload(Invoice.details).joinedload(InvoiceDetail.location),
            joinedload(Invoice.payments).joinedload(Payment.bank_account),
            joinedload(Invoice.payments).joinedload(Payment.creator),
        )
        .filter(Invoice.id == invoice_id)
        .first_or_404()
    )
    return jsonify({"item": serialize_invoice(invoice)})
