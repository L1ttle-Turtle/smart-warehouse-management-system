from flask import Blueprint, abort, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy import or_

from ..audit import log_audit_event
from ..extensions import db
from ..models import ImportReceipt, ImportReceiptDetail, Product, Supplier, Warehouse, WarehouseLocation
from ..permissions import get_current_user, permission_required
from ..schemas import ImportReceiptSchema
from ..serializers import serialize_import_receipt
from ..services.inventory import confirm_import_receipt, validate_location_in_warehouse
from ..utils import generate_code

import_receipts_bp = Blueprint("import_receipts", __name__)


SORT_FIELDS = {
    "receipt_code": ImportReceipt.receipt_code,
    "status": ImportReceipt.status,
    "created_at": ImportReceipt.created_at,
    "updated_at": ImportReceipt.updated_at,
    "confirmed_at": ImportReceipt.confirmed_at,
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
        "items": [serialize_import_receipt(item) for item in pagination.items],
        "total": pagination.total,
        "page": pagination.page,
        "page_size": pagination.per_page,
    }


def apply_sort(query):
    sort_by = normalize_optional_text(request.args.get("sort_by")) or "created_at"
    sort_order = (request.args.get("sort_order") or "desc").strip().lower()
    column = SORT_FIELDS.get(sort_by, ImportReceipt.created_at)
    if sort_order == "asc":
        return query.order_by(column.asc())
    return query.order_by(column.desc())


def validate_warehouse(warehouse_id):
    warehouse = db.session.get(Warehouse, warehouse_id)
    if not warehouse:
        abort(400, description="Kho không hợp lệ.")
    return warehouse


def validate_supplier(supplier_id):
    if supplier_id is None:
        return None
    supplier = db.session.get(Supplier, supplier_id)
    if not supplier:
        abort(400, description="Nhà cung cấp không hợp lệ.")
    return supplier


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
    validate_supplier(payload.get("supplier_id"))
    for item in payload.get("items", []):
        validate_product(item["product_id"])
        try:
            validate_location_in_warehouse(item["location_id"], payload["warehouse_id"])
        except ValueError as exc:
            abort(400, description=str(exc))
        if item["quantity"] <= 0:
            abort(400, description="Số lượng nhập phải lớn hơn 0.")


def sync_receipt_details(receipt, items):
    receipt.details.clear()
    db.session.flush()
    for item in items:
        receipt.details.append(
            ImportReceiptDetail(
                product_id=item["product_id"],
                location_id=item["location_id"],
                quantity=item["quantity"],
            )
        )


def audit_import_receipt_change(action, actor_user_id, receipt):
    log_audit_event(
        action,
        "import_receipt",
        f"{action.split('.')[1].capitalize()} phiếu nhập {receipt.receipt_code}.",
        actor_user_id=actor_user_id,
        entity_id=receipt.id,
        entity_label=receipt.receipt_code,
    )


@import_receipts_bp.get("/import-receipts")
@jwt_required()
@permission_required("import_receipts.view")
def list_import_receipts():
    query = ImportReceipt.query.join(Warehouse).outerjoin(Supplier)
    search = normalize_optional_text(request.args.get("search"))
    if search:
        like_term = f"%{search}%"
        query = query.filter(
            or_(
                ImportReceipt.receipt_code.ilike(like_term),
                ImportReceipt.note.ilike(like_term),
                Warehouse.warehouse_code.ilike(like_term),
                Warehouse.warehouse_name.ilike(like_term),
                Supplier.supplier_code.ilike(like_term),
                Supplier.supplier_name.ilike(like_term),
            )
        )

    status = normalize_optional_text(request.args.get("status"))
    if status:
        query = query.filter(ImportReceipt.status == status)

    warehouse_id = request.args.get("warehouse_id", type=int)
    if warehouse_id:
        query = query.filter(ImportReceipt.warehouse_id == warehouse_id)

    query = apply_sort(query)
    page, page_size = get_pagination_params()
    pagination = query.paginate(page=page, per_page=page_size, error_out=False)
    return jsonify(build_pagination_payload(pagination))


@import_receipts_bp.post("/import-receipts")
@jwt_required()
@permission_required("import_receipts.manage")
def create_import_receipt():
    current_user = get_current_user()
    payload = ImportReceiptSchema().load(request.get_json() or {})
    payload = normalize_payload(payload)
    validate_receipt_payload(payload)

    receipt = ImportReceipt(
        receipt_code=generate_code("IMP"),
        warehouse_id=payload["warehouse_id"],
        supplier_id=payload.get("supplier_id"),
        created_by=current_user.id,
        note=payload.get("note"),
    )
    db.session.add(receipt)
    db.session.flush()
    sync_receipt_details(receipt, payload["items"])
    audit_import_receipt_change("import_receipts.created", current_user.id, receipt)
    db.session.commit()
    return jsonify({"item": serialize_import_receipt(receipt)}), 201


@import_receipts_bp.get("/import-receipts/<int:receipt_id>")
@jwt_required()
@permission_required("import_receipts.view")
def get_import_receipt(receipt_id):
    receipt = db.get_or_404(ImportReceipt, receipt_id)
    return jsonify({"item": serialize_import_receipt(receipt)})


@import_receipts_bp.put("/import-receipts/<int:receipt_id>")
@jwt_required()
@permission_required("import_receipts.manage")
def update_import_receipt(receipt_id):
    current_user = get_current_user()
    receipt = db.get_or_404(ImportReceipt, receipt_id)
    if receipt.status != "draft":
        abort(400, description="Chỉ phiếu nhập ở trạng thái nháp mới có thể chỉnh sửa.")

    payload = ImportReceiptSchema().load(request.get_json() or {})
    payload = normalize_payload(payload)
    validate_receipt_payload(payload)

    receipt.warehouse_id = payload["warehouse_id"]
    receipt.supplier_id = payload.get("supplier_id")
    receipt.note = payload.get("note")
    sync_receipt_details(receipt, payload["items"])
    audit_import_receipt_change("import_receipts.updated", current_user.id, receipt)
    db.session.commit()
    return jsonify({"item": serialize_import_receipt(receipt)})


@import_receipts_bp.post("/import-receipts/<int:receipt_id>/cancel")
@jwt_required()
@permission_required("import_receipts.manage")
def cancel_import_receipt_route(receipt_id):
    current_user = get_current_user()
    receipt = db.get_or_404(ImportReceipt, receipt_id)
    if receipt.status != "draft":
        abort(400, description="Chỉ phiếu nhập ở trạng thái nháp mới có thể hủy.")

    # Draft receipts have not touched inventory yet, so cancel only changes workflow state.
    receipt.status = "cancelled"
    audit_import_receipt_change("import_receipts.cancelled", current_user.id, receipt)
    db.session.commit()
    return jsonify({"item": serialize_import_receipt(receipt)})


@import_receipts_bp.post("/import-receipts/<int:receipt_id>/confirm")
@jwt_required()
@permission_required("import_receipts.manage")
def confirm_import_receipt_route(receipt_id):
    current_user = get_current_user()
    receipt = db.get_or_404(ImportReceipt, receipt_id)

    try:
        confirm_import_receipt(receipt, current_user.id)
        audit_import_receipt_change("import_receipts.confirmed", current_user.id, receipt)
        db.session.commit()
    except ValueError as exc:
        db.session.rollback()
        abort(400, description=str(exc))

    return jsonify({"item": serialize_import_receipt(receipt)})
