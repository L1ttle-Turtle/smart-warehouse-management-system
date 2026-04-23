from flask import Blueprint, abort, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy import or_

from ..audit import log_audit_event
from ..extensions import db
from ..models import Customer, ExportReceipt, ExportReceiptDetail, Product, Warehouse
from ..permissions import get_current_user, permission_required
from ..schemas import ExportReceiptSchema
from ..serializers import serialize_export_receipt
from ..services.inventory import confirm_export_receipt, validate_location_in_warehouse
from ..utils import generate_code

export_receipts_bp = Blueprint("export_receipts", __name__)


SORT_FIELDS = {
    "receipt_code": ExportReceipt.receipt_code,
    "status": ExportReceipt.status,
    "created_at": ExportReceipt.created_at,
    "updated_at": ExportReceipt.updated_at,
    "confirmed_at": ExportReceipt.confirmed_at,
}


def normalize_optional_text(value, *, lower=False):
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
        return value.lower() if lower else value
    return value


def get_pagination_params():
    page = max(request.args.get("page", default=1, type=int), 1)
    page_size = min(max(request.args.get("page_size", default=10, type=int), 1), 100)
    return page, page_size


def build_pagination_payload(pagination):
    return {
        "items": [serialize_export_receipt(item) for item in pagination.items],
        "total": pagination.total,
        "page": pagination.page,
        "page_size": pagination.per_page,
    }


def apply_sort(query):
    sort_by = normalize_optional_text(request.args.get("sort_by")) or "created_at"
    sort_order = (request.args.get("sort_order") or "desc").strip().lower()
    column = SORT_FIELDS.get(sort_by, ExportReceipt.created_at)
    if sort_order == "asc":
        return query.order_by(column.asc())
    return query.order_by(column.desc())


def validate_warehouse(warehouse_id):
    warehouse = db.session.get(Warehouse, warehouse_id)
    if not warehouse:
        abort(400, description="Kho không hợp lệ.")
    return warehouse


def validate_customer(customer_id):
    if customer_id is None:
        return None
    customer = db.session.get(Customer, customer_id)
    if not customer:
        abort(400, description="Khách hàng không hợp lệ.")
    return customer


def validate_product(product_id):
    product = db.session.get(Product, product_id)
    if not product:
        abort(400, description="Sản phẩm không hợp lệ.")
    return product


def normalize_payload(payload):
    normalized_payload = dict(payload)
    if "note" in normalized_payload:
        normalized_payload["note"] = normalize_optional_text(normalized_payload["note"])
    normalized_payload["items"] = [
        {
            **item,
            "quantity": float(item["quantity"]),
        }
        for item in normalized_payload.get("items", [])
    ]
    return normalized_payload


def validate_receipt_payload(payload):
    validate_warehouse(payload["warehouse_id"])
    validate_customer(payload.get("customer_id"))
    for item in payload.get("items", []):
        validate_product(item["product_id"])
        try:
            validate_location_in_warehouse(item["location_id"], payload["warehouse_id"])
        except ValueError as exc:
            abort(400, description=str(exc))
        if item["quantity"] <= 0:
            abort(400, description="Số lượng xuất phải lớn hơn 0.")


def sync_receipt_details(receipt, items):
    receipt.details.clear()
    db.session.flush()
    for item in items:
        receipt.details.append(
            ExportReceiptDetail(
                product_id=item["product_id"],
                location_id=item["location_id"],
                quantity=item["quantity"],
            )
        )


def audit_export_receipt_change(action, actor_user_id, receipt):
    log_audit_event(
        action,
        "export_receipt",
        f"{action.split('.')[1].capitalize()} phiếu xuất {receipt.receipt_code}.",
        actor_user_id=actor_user_id,
        entity_id=receipt.id,
        entity_label=receipt.receipt_code,
    )


@export_receipts_bp.get("/export-receipts")
@jwt_required()
@permission_required("export_receipts.view")
def list_export_receipts():
    query = ExportReceipt.query.join(Warehouse).outerjoin(Customer)
    search = normalize_optional_text(request.args.get("search"))
    if search:
        like_term = f"%{search}%"
        query = query.filter(
            or_(
                ExportReceipt.receipt_code.ilike(like_term),
                ExportReceipt.note.ilike(like_term),
                Warehouse.warehouse_code.ilike(like_term),
                Warehouse.warehouse_name.ilike(like_term),
                Customer.customer_code.ilike(like_term),
                Customer.customer_name.ilike(like_term),
            )
        )

    status = normalize_optional_text(request.args.get("status"))
    if status:
        query = query.filter(ExportReceipt.status == status)

    warehouse_id = request.args.get("warehouse_id", type=int)
    if warehouse_id:
        query = query.filter(ExportReceipt.warehouse_id == warehouse_id)

    query = apply_sort(query)
    page, page_size = get_pagination_params()
    pagination = query.paginate(page=page, per_page=page_size, error_out=False)
    return jsonify(build_pagination_payload(pagination))


@export_receipts_bp.post("/export-receipts")
@jwt_required()
@permission_required("export_receipts.manage")
def create_export_receipt():
    current_user = get_current_user()
    payload = ExportReceiptSchema().load(request.get_json() or {})
    payload = normalize_payload(payload)
    validate_receipt_payload(payload)

    receipt = ExportReceipt(
        receipt_code=generate_code("EXP"),
        warehouse_id=payload["warehouse_id"],
        customer_id=payload.get("customer_id"),
        created_by=current_user.id,
        note=payload.get("note"),
    )
    db.session.add(receipt)
    db.session.flush()
    sync_receipt_details(receipt, payload["items"])
    audit_export_receipt_change("export_receipts.created", current_user.id, receipt)
    db.session.commit()
    return jsonify({"item": serialize_export_receipt(receipt)}), 201


@export_receipts_bp.get("/export-receipts/<int:receipt_id>")
@jwt_required()
@permission_required("export_receipts.view")
def get_export_receipt(receipt_id):
    receipt = db.get_or_404(ExportReceipt, receipt_id)
    return jsonify({"item": serialize_export_receipt(receipt)})


@export_receipts_bp.put("/export-receipts/<int:receipt_id>")
@jwt_required()
@permission_required("export_receipts.manage")
def update_export_receipt(receipt_id):
    current_user = get_current_user()
    receipt = db.get_or_404(ExportReceipt, receipt_id)
    if receipt.status != "draft":
        abort(400, description="Chỉ phiếu xuất ở trạng thái nháp mới có thể chỉnh sửa.")

    payload = ExportReceiptSchema().load(request.get_json() or {})
    payload = normalize_payload(payload)
    validate_receipt_payload(payload)

    receipt.warehouse_id = payload["warehouse_id"]
    receipt.customer_id = payload.get("customer_id")
    receipt.note = payload.get("note")
    sync_receipt_details(receipt, payload["items"])
    audit_export_receipt_change("export_receipts.updated", current_user.id, receipt)
    db.session.commit()
    return jsonify({"item": serialize_export_receipt(receipt)})


@export_receipts_bp.post("/export-receipts/<int:receipt_id>/cancel")
@jwt_required()
@permission_required("export_receipts.manage")
def cancel_export_receipt_route(receipt_id):
    current_user = get_current_user()
    receipt = db.get_or_404(ExportReceipt, receipt_id)
    if receipt.status != "draft":
        abort(400, description="Chỉ phiếu xuất ở trạng thái nháp mới có thể hủy.")

    # Draft receipts have not touched inventory yet, so cancel only changes workflow state.
    receipt.status = "cancelled"
    audit_export_receipt_change("export_receipts.cancelled", current_user.id, receipt)
    db.session.commit()
    return jsonify({"item": serialize_export_receipt(receipt)})


@export_receipts_bp.post("/export-receipts/<int:receipt_id>/confirm")
@jwt_required()
@permission_required("export_receipts.manage")
def confirm_export_receipt_route(receipt_id):
    current_user = get_current_user()
    receipt = db.get_or_404(ExportReceipt, receipt_id)

    try:
        confirm_export_receipt(receipt, current_user.id)
        audit_export_receipt_change("export_receipts.confirmed", current_user.id, receipt)
        db.session.commit()
    except ValueError as exc:
        db.session.rollback()
        abort(400, description=str(exc))

    return jsonify({"item": serialize_export_receipt(receipt)})
