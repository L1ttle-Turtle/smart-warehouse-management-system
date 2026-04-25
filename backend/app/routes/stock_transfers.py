from flask import Blueprint, abort, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy import or_
from sqlalchemy.orm import aliased

from ..audit import log_audit_event
from ..extensions import db
from ..models import Product, StockTransfer, StockTransferDetail, Warehouse
from ..permissions import get_current_user, permission_required
from ..schemas import StockTransferSchema
from ..serializers import serialize_stock_transfer
from ..services.inventory import confirm_stock_transfer, validate_location_in_warehouse
from ..utils import generate_code

stock_transfers_bp = Blueprint("stock_transfers", __name__)


SORT_FIELDS = {
    "transfer_code": StockTransfer.transfer_code,
    "status": StockTransfer.status,
    "created_at": StockTransfer.created_at,
    "updated_at": StockTransfer.updated_at,
    "confirmed_at": StockTransfer.confirmed_at,
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
        "items": [serialize_stock_transfer(item) for item in pagination.items],
        "total": pagination.total,
        "page": pagination.page,
        "page_size": pagination.per_page,
    }


def apply_sort(query):
    sort_by = normalize_optional_text(request.args.get("sort_by")) or "created_at"
    sort_order = (request.args.get("sort_order") or "desc").strip().lower()
    column = SORT_FIELDS.get(sort_by, StockTransfer.created_at)
    if sort_order == "asc":
        return query.order_by(column.asc())
    return query.order_by(column.desc())


def validate_warehouse(warehouse_id, label):
    warehouse = db.session.get(Warehouse, warehouse_id)
    if not warehouse:
        abort(400, description=f"{label} không hợp lệ.")
    return warehouse


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


def validate_transfer_payload(payload):
    source_warehouse_id = payload["source_warehouse_id"]
    target_warehouse_id = payload["target_warehouse_id"]
    validate_warehouse(source_warehouse_id, "Kho nguồn")
    validate_warehouse(target_warehouse_id, "Kho đích")
    if source_warehouse_id == target_warehouse_id:
        abort(400, description="Kho nguồn và kho đích phải khác nhau.")

    for item in payload.get("items", []):
        validate_product(item["product_id"])
        try:
            validate_location_in_warehouse(item["source_location_id"], source_warehouse_id)
            validate_location_in_warehouse(item["target_location_id"], target_warehouse_id)
        except ValueError as exc:
            abort(400, description=str(exc))
        if item["quantity"] <= 0:
            abort(400, description="Số lượng điều chuyển phải lớn hơn 0.")


def sync_transfer_details(transfer, items):
    transfer.details.clear()
    db.session.flush()
    for item in items:
        transfer.details.append(
            StockTransferDetail(
                product_id=item["product_id"],
                source_location_id=item["source_location_id"],
                target_location_id=item["target_location_id"],
                quantity=item["quantity"],
            )
        )


def audit_stock_transfer_change(action, actor_user_id, transfer):
    log_audit_event(
        action,
        "stock_transfer",
        f"{action.split('.')[1].capitalize()} phiếu điều chuyển {transfer.transfer_code}.",
        actor_user_id=actor_user_id,
        entity_id=transfer.id,
        entity_label=transfer.transfer_code,
    )


def claim_draft_stock_transfer_for_mutation(transfer_id, lock_status, error_message):
    claimed_rows = (
        db.session.query(StockTransfer)
        .filter(
            StockTransfer.id == transfer_id,
            StockTransfer.status == "draft",
        )
        .update({"status": lock_status}, synchronize_session=False)
    )
    if claimed_rows == 0:
        transfer = db.session.get(StockTransfer, transfer_id)
        if not transfer:
            abort(404)
        abort(400, description=error_message)

    transfer = db.session.get(StockTransfer, transfer_id)
    transfer.status = "draft"
    return transfer


@stock_transfers_bp.get("/stock-transfers")
@jwt_required()
@permission_required("stock_transfers.view")
def list_stock_transfers():
    source_warehouse = aliased(Warehouse)
    target_warehouse = aliased(Warehouse)
    query = (
        StockTransfer.query.join(
            source_warehouse,
            StockTransfer.source_warehouse_id == source_warehouse.id,
        )
        .join(
            target_warehouse,
            StockTransfer.target_warehouse_id == target_warehouse.id,
        )
    )

    search = normalize_optional_text(request.args.get("search"))
    if search:
        like_term = f"%{search}%"
        query = query.filter(
            or_(
                StockTransfer.transfer_code.ilike(like_term),
                StockTransfer.note.ilike(like_term),
                source_warehouse.warehouse_code.ilike(like_term),
                source_warehouse.warehouse_name.ilike(like_term),
                target_warehouse.warehouse_code.ilike(like_term),
                target_warehouse.warehouse_name.ilike(like_term),
            )
        )

    status = normalize_optional_text(request.args.get("status"))
    if status:
        query = query.filter(StockTransfer.status == status)

    source_warehouse_id = request.args.get("source_warehouse_id", type=int)
    if source_warehouse_id:
        query = query.filter(StockTransfer.source_warehouse_id == source_warehouse_id)

    target_warehouse_id = request.args.get("target_warehouse_id", type=int)
    if target_warehouse_id:
        query = query.filter(StockTransfer.target_warehouse_id == target_warehouse_id)

    query = apply_sort(query)
    page, page_size = get_pagination_params()
    pagination = query.paginate(page=page, per_page=page_size, error_out=False)
    return jsonify(build_pagination_payload(pagination))


@stock_transfers_bp.post("/stock-transfers")
@jwt_required()
@permission_required("stock_transfers.manage")
def create_stock_transfer():
    current_user = get_current_user()
    payload = StockTransferSchema().load(request.get_json() or {})
    payload = normalize_payload(payload)
    validate_transfer_payload(payload)

    transfer = StockTransfer(
        transfer_code=generate_code("TRF"),
        source_warehouse_id=payload["source_warehouse_id"],
        target_warehouse_id=payload["target_warehouse_id"],
        created_by=current_user.id,
        note=payload.get("note"),
    )
    db.session.add(transfer)
    db.session.flush()
    sync_transfer_details(transfer, payload["items"])
    audit_stock_transfer_change("stock_transfers.created", current_user.id, transfer)
    db.session.commit()
    return jsonify({"item": serialize_stock_transfer(transfer)}), 201


@stock_transfers_bp.get("/stock-transfers/<int:transfer_id>")
@jwt_required()
@permission_required("stock_transfers.view")
def get_stock_transfer(transfer_id):
    transfer = db.get_or_404(StockTransfer, transfer_id)
    return jsonify({"item": serialize_stock_transfer(transfer)})


@stock_transfers_bp.put("/stock-transfers/<int:transfer_id>")
@jwt_required()
@permission_required("stock_transfers.manage")
def update_stock_transfer(transfer_id):
    current_user = get_current_user()
    try:
        transfer = claim_draft_stock_transfer_for_mutation(
            transfer_id,
            "editing",
            "Chỉ phiếu điều chuyển ở trạng thái nháp mới có thể chỉnh sửa.",
        )
        payload = StockTransferSchema().load(request.get_json() or {})
        payload = normalize_payload(payload)
        validate_transfer_payload(payload)

        transfer.source_warehouse_id = payload["source_warehouse_id"]
        transfer.target_warehouse_id = payload["target_warehouse_id"]
        transfer.note = payload.get("note")
        sync_transfer_details(transfer, payload["items"])
        audit_stock_transfer_change("stock_transfers.updated", current_user.id, transfer)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return jsonify({"item": serialize_stock_transfer(transfer)})


@stock_transfers_bp.post("/stock-transfers/<int:transfer_id>/cancel")
@jwt_required()
@permission_required("stock_transfers.manage")
def cancel_stock_transfer_route(transfer_id):
    current_user = get_current_user()
    try:
        transfer = claim_draft_stock_transfer_for_mutation(
            transfer_id,
            "cancelling",
            "Chỉ phiếu điều chuyển ở trạng thái nháp mới có thể hủy.",
        )
        # Draft transfers have not touched inventory yet, so cancel only changes workflow state.
        transfer.status = "cancelled"
        audit_stock_transfer_change("stock_transfers.cancelled", current_user.id, transfer)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return jsonify({"item": serialize_stock_transfer(transfer)})


@stock_transfers_bp.post("/stock-transfers/<int:transfer_id>/confirm")
@jwt_required()
@permission_required("stock_transfers.manage")
def confirm_stock_transfer_route(transfer_id):
    current_user = get_current_user()
    try:
        transfer = claim_draft_stock_transfer_for_mutation(
            transfer_id,
            "confirming",
            "Chỉ phiếu điều chuyển ở trạng thái nháp mới có thể xác nhận.",
        )
        confirm_stock_transfer(transfer, current_user.id)
        audit_stock_transfer_change("stock_transfers.confirmed", current_user.id, transfer)
        db.session.commit()
    except ValueError as exc:
        db.session.rollback()
        abort(400, description=str(exc))
    except Exception:
        db.session.rollback()
        raise

    return jsonify({"item": serialize_stock_transfer(transfer)})
