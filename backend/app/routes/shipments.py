from flask import Blueprint, abort, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy import or_
from sqlalchemy.orm import aliased

from ..audit import log_audit_event
from ..extensions import db
from ..models import ExportReceipt, Shipment, User, Warehouse
from ..permissions import get_current_user, permission_required
from ..schemas import ShipmentCreateSchema, ShipmentStatusSchema
from ..serializers import serialize_export_receipt, serialize_shipment, serialize_user_summary
from ..utils import generate_code, utc_now

shipments_bp = Blueprint("shipments", __name__)


SHIPMENT_SORT_FIELDS = {
    "shipment_code": Shipment.shipment_code,
    "status": Shipment.status,
    "created_at": Shipment.created_at,
    "updated_at": Shipment.updated_at,
    "assigned_at": Shipment.assigned_at,
    "in_transit_at": Shipment.in_transit_at,
    "delivered_at": Shipment.delivered_at,
    "cancelled_at": Shipment.cancelled_at,
}

SHIPMENT_TRANSITIONS = {
    "assigned": {"in_transit", "delivered", "cancelled"},
    "in_transit": {"delivered", "cancelled"},
    "delivered": set(),
    "cancelled": set(),
}

SHIPPER_ALLOWED_TRANSITIONS = {
    "assigned": {"in_transit"},
    "in_transit": {"delivered"},
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


def get_role_name(user):
    return user.role.role_name if user and user.role else None


def get_pagination_params():
    page = max(request.args.get("page", default=1, type=int), 1)
    page_size = min(max(request.args.get("page_size", default=10, type=int), 1), 100)
    return page, page_size


def build_pagination_payload(pagination):
    return {
        "items": [serialize_shipment(item) for item in pagination.items],
        "total": pagination.total,
        "page": pagination.page,
        "page_size": pagination.per_page,
    }


def apply_sort(query):
    sort_by = normalize_optional_text(request.args.get("sort_by")) or "created_at"
    sort_order = (request.args.get("sort_order") or "desc").strip().lower()
    column = SHIPMENT_SORT_FIELDS.get(sort_by, Shipment.created_at)
    if sort_order == "asc":
        return query.order_by(column.asc())
    return query.order_by(column.desc())


def validate_shipper_user(shipper_id):
    shipper = db.session.get(User, shipper_id)
    if not shipper or shipper.status != "active":
        abort(400, description="Shipper không hợp lệ.")
    if get_role_name(shipper) != "shipper":
        abort(400, description="Người được giao phải có vai trò shipper.")
    return shipper


def validate_export_receipt(export_receipt_id):
    receipt = db.session.get(ExportReceipt, export_receipt_id)
    if not receipt:
        abort(400, description="Phiếu xuất không hợp lệ.")
    return receipt


def validate_confirmed_export_receipt_for_shipment(export_receipt_id):
    receipt = validate_export_receipt(export_receipt_id)
    if receipt.status != "confirmed":
        abort(400, description="Chỉ có thể tạo shipment từ phiếu xuất đã xác nhận.")
    if receipt.shipment:
        abort(409, description="Phiếu xuất này đã có shipment.")
    return receipt


def ensure_shipment_scope(user, shipment):
    if get_role_name(user) == "shipper" and shipment.shipper_id != user.id:
        abort(403, description="Shipper chỉ được xem và cập nhật đơn được giao cho mình.")


def audit_shipment_change(action, actor_user_id, shipment):
    log_audit_event(
        action,
        "shipment",
        f"{action.split('.')[1].capitalize()} shipment {shipment.shipment_code}.",
        actor_user_id=actor_user_id,
        entity_id=shipment.id,
        entity_label=shipment.shipment_code,
    )


@shipments_bp.get("/shipments/meta")
@jwt_required()
@permission_required("shipments.manage")
def shipment_meta():
    current_user = get_current_user()
    if get_role_name(current_user) == "shipper":
        abort(403, description="Shipper chỉ được cập nhật đơn được giao, không thể tạo shipment mới.")

    shippers = (
        User.query.filter_by(status="active")
        .join(User.role)
        .filter_by(role_name="shipper")
        .order_by(User.full_name.asc())
        .all()
    )
    confirmed_receipts = (
        ExportReceipt.query.filter_by(status="confirmed")
        .outerjoin(Shipment, Shipment.export_receipt_id == ExportReceipt.id)
        .filter(Shipment.id.is_(None))
        .order_by(ExportReceipt.confirmed_at.desc(), ExportReceipt.created_at.desc())
        .all()
    )
    return jsonify(
        {
            "shippers": [serialize_user_summary(item) for item in shippers],
            "export_receipts": [serialize_export_receipt(item) for item in confirmed_receipts],
        }
    )


@shipments_bp.get("/shipments")
@jwt_required()
@permission_required("shipments.view")
def list_shipments():
    current_user = get_current_user()
    shipper_alias = aliased(User)
    query = (
        Shipment.query.join(Shipment.export_receipt)
        .join(ExportReceipt.warehouse)
        .outerjoin(ExportReceipt.customer)
        .join(shipper_alias, Shipment.shipper_id == shipper_alias.id)
    )

    search = normalize_optional_text(request.args.get("search"))
    if search:
        like_term = f"%{search}%"
        query = query.filter(
            or_(
                Shipment.shipment_code.ilike(like_term),
                Shipment.note.ilike(like_term),
                ExportReceipt.receipt_code.ilike(like_term),
                Warehouse.warehouse_code.ilike(like_term),
                Warehouse.warehouse_name.ilike(like_term),
                shipper_alias.full_name.ilike(like_term),
            )
        )

    status = normalize_optional_text(request.args.get("status"))
    if status:
        query = query.filter(Shipment.status == status)

    shipper_id = parse_optional_int_arg("shipper_id")
    if shipper_id is not None:
        validate_shipper_user(shipper_id)
        query = query.filter(Shipment.shipper_id == shipper_id)

    export_receipt_id = parse_optional_int_arg("export_receipt_id")
    if export_receipt_id is not None:
        validate_export_receipt(export_receipt_id)
        query = query.filter(Shipment.export_receipt_id == export_receipt_id)

    warehouse_id = parse_optional_int_arg("warehouse_id")
    if warehouse_id is not None:
        warehouse = db.session.get(Warehouse, warehouse_id)
        if not warehouse:
            abort(400, description="Kho không hợp lệ.")
        query = query.filter(ExportReceipt.warehouse_id == warehouse_id)

    if get_role_name(current_user) == "shipper":
        query = query.filter(Shipment.shipper_id == current_user.id)

    query = apply_sort(query)
    page, page_size = get_pagination_params()
    pagination = query.paginate(page=page, per_page=page_size, error_out=False)
    return jsonify(build_pagination_payload(pagination))


@shipments_bp.post("/shipments")
@jwt_required()
@permission_required("shipments.manage")
def create_shipment():
    current_user = get_current_user()
    if get_role_name(current_user) == "shipper":
        abort(403, description="Shipper chỉ được cập nhật đơn được giao, không thể tạo shipment mới.")

    payload = ShipmentCreateSchema().load(request.get_json() or {})
    receipt = validate_confirmed_export_receipt_for_shipment(payload["export_receipt_id"])
    validate_shipper_user(payload["shipper_id"])
    note = normalize_optional_text(payload.get("note"))

    shipment = Shipment(
        shipment_code=generate_code("SHP"),
        export_receipt_id=receipt.id,
        shipper_id=payload["shipper_id"],
        created_by=current_user.id,
        status="assigned",
        note=note,
        assigned_at=utc_now(),
    )
    db.session.add(shipment)
    db.session.flush()
    audit_shipment_change("shipments.created", current_user.id, shipment)
    db.session.commit()
    return jsonify({"item": serialize_shipment(shipment)}), 201


@shipments_bp.get("/shipments/<int:shipment_id>")
@jwt_required()
@permission_required("shipments.view")
def get_shipment(shipment_id):
    current_user = get_current_user()
    shipment = db.get_or_404(Shipment, shipment_id)
    ensure_shipment_scope(current_user, shipment)
    return jsonify({"item": serialize_shipment(shipment)})


@shipments_bp.post("/shipments/<int:shipment_id>/status")
@jwt_required()
@permission_required("shipments.manage")
def update_shipment_status(shipment_id):
    current_user = get_current_user()
    shipment = db.get_or_404(Shipment, shipment_id)
    ensure_shipment_scope(current_user, shipment)

    payload = ShipmentStatusSchema().load(request.get_json() or {})
    next_status = payload["status"]
    current_status = shipment.status
    role_name = get_role_name(current_user)

    if next_status == current_status:
        abort(400, description="Shipment đã ở trạng thái này.")

    if next_status not in SHIPMENT_TRANSITIONS.get(current_status, set()):
        abort(400, description="Không thể chuyển shipment sang trạng thái được chọn.")

    if role_name == "shipper" and next_status not in SHIPPER_ALLOWED_TRANSITIONS.get(current_status, set()):
        abort(403, description="Shipper chỉ được cập nhật đơn của mình theo đúng luồng giao hàng.")

    shipment.status = next_status
    note = normalize_optional_text(payload.get("note"))
    if note is not None:
        shipment.note = note

    if next_status == "in_transit" and shipment.in_transit_at is None:
        shipment.in_transit_at = utc_now()
    if next_status == "delivered" and shipment.delivered_at is None:
        shipment.delivered_at = utc_now()
    if next_status == "cancelled" and shipment.cancelled_at is None:
        shipment.cancelled_at = utc_now()

    audit_shipment_change("shipments.status_updated", current_user.id, shipment)
    db.session.commit()
    return jsonify({"item": serialize_shipment(shipment)})
