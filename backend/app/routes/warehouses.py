from flask import Blueprint, abort, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError

from ..audit import log_audit_event
from ..extensions import db
from ..models import Inventory, InventoryMovement, Warehouse, WarehouseLocation
from ..permissions import get_current_user, permission_required
from ..schemas import WarehouseLocationSchema, WarehouseSchema
from ..serializers import serialize_warehouse, serialize_warehouse_location

warehouses_bp = Blueprint("warehouses", __name__)


WAREHOUSE_SORT_FIELDS = {
    "id": Warehouse.id,
    "warehouse_code": Warehouse.warehouse_code,
    "warehouse_name": Warehouse.warehouse_name,
    "status": Warehouse.status,
    "created_at": Warehouse.created_at,
    "updated_at": Warehouse.updated_at,
}

LOCATION_SORT_FIELDS = {
    "id": WarehouseLocation.id,
    "location_code": WarehouseLocation.location_code,
    "location_name": WarehouseLocation.location_name,
    "status": WarehouseLocation.status,
    "created_at": WarehouseLocation.created_at,
    "updated_at": WarehouseLocation.updated_at,
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


def build_pagination_payload(pagination, serializer):
    return {
        "items": [serializer(item) for item in pagination.items],
        "total": pagination.total,
        "page": pagination.page,
        "page_size": pagination.per_page,
    }


def apply_sort(query, sort_fields, default_sort_by):
    sort_by = normalize_optional_text(request.args.get("sort_by")) or default_sort_by
    sort_order = (request.args.get("sort_order") or "asc").strip().lower()
    column = sort_fields.get(sort_by, sort_fields[default_sort_by])
    if sort_order == "desc":
        return query.order_by(column.desc())
    return query.order_by(column.asc())


def normalize_warehouse_payload(payload):
    normalized_payload = dict(payload)
    for field_name in ["warehouse_code", "warehouse_name", "address"]:
        if field_name in normalized_payload:
            normalized_payload[field_name] = normalize_optional_text(normalized_payload[field_name])
    return normalized_payload


def normalize_location_payload(payload):
    normalized_payload = dict(payload)
    for field_name in ["location_code", "location_name"]:
        if field_name in normalized_payload:
            normalized_payload[field_name] = normalize_optional_text(normalized_payload[field_name])
    return normalized_payload


def validate_warehouse_required_fields(payload):
    if "warehouse_code" in payload and not payload["warehouse_code"]:
        abort(400, description="Mã kho không được để trống.")
    if "warehouse_name" in payload and not payload["warehouse_name"]:
        abort(400, description="Tên kho không được để trống.")


def validate_location_required_fields(payload):
    if "location_code" in payload and not payload["location_code"]:
        abort(400, description="Mã vị trí không được để trống.")
    if "location_name" in payload and not payload["location_name"]:
        abort(400, description="Tên vị trí không được để trống.")


def validate_warehouse_exists(warehouse_id):
    if warehouse_id is None:
        abort(400, description="Kho là bắt buộc.")
    warehouse = db.session.get(Warehouse, warehouse_id)
    if not warehouse:
        abort(400, description="Kho không hợp lệ.")
    return warehouse


def validate_unique_warehouse_code(warehouse_code, record_id=None):
    if not warehouse_code:
        return
    query = Warehouse.query.filter(func.lower(Warehouse.warehouse_code) == warehouse_code.lower())
    if record_id is not None:
        query = query.filter(Warehouse.id != record_id)
    if query.first():
        abort(409, description="Mã kho đã tồn tại.")


def validate_unique_location_code(warehouse_id, location_code, record_id=None):
    if not warehouse_id or not location_code:
        return
    query = WarehouseLocation.query.filter(
        WarehouseLocation.warehouse_id == warehouse_id,
        func.lower(WarehouseLocation.location_code) == location_code.lower(),
    )
    if record_id is not None:
        query = query.filter(WarehouseLocation.id != record_id)
    if query.first():
        abort(409, description="Mã vị trí đã tồn tại trong kho này.")


def audit_warehouse_change(action, actor_user_id, warehouse):
    log_audit_event(
        action,
        "warehouse",
        f"{action.split('.')[1].capitalize()} kho {warehouse.warehouse_name}.",
        actor_user_id=actor_user_id,
        entity_id=warehouse.id,
        entity_label=warehouse.warehouse_name,
    )


def audit_location_change(action, actor_user_id, location):
    label = f"{location.location_name} ({location.location_code})"
    log_audit_event(
        action,
        "warehouse_location",
        f"{action.split('.')[1].capitalize()} vị trí {label}.",
        actor_user_id=actor_user_id,
        entity_id=location.id,
        entity_label=label,
    )


def warehouse_has_dependencies(warehouse):
    if WarehouseLocation.query.filter_by(warehouse_id=warehouse.id).first():
        return True
    if Inventory.query.filter_by(warehouse_id=warehouse.id).first():
        return True
    if InventoryMovement.query.filter_by(warehouse_id=warehouse.id).first():
        return True
    return False


def location_has_dependencies(location):
    if Inventory.query.filter_by(location_id=location.id).first():
        return True
    if InventoryMovement.query.filter_by(location_id=location.id).first():
        return True
    return False


@warehouses_bp.get("/warehouses")
@jwt_required()
@permission_required("warehouses.view")
def list_warehouses():
    query = Warehouse.query
    search = normalize_optional_text(request.args.get("search"))
    if search:
        like_term = f"%{search}%"
        query = query.filter(
            or_(
                Warehouse.warehouse_code.ilike(like_term),
                Warehouse.warehouse_name.ilike(like_term),
                Warehouse.address.ilike(like_term),
            )
        )

    status = normalize_optional_text(request.args.get("status"))
    if status:
        query = query.filter(Warehouse.status == status)

    query = apply_sort(query, WAREHOUSE_SORT_FIELDS, "warehouse_code")
    page, page_size = get_pagination_params()
    pagination = query.paginate(page=page, per_page=page_size, error_out=False)
    return jsonify(build_pagination_payload(pagination, serialize_warehouse))


@warehouses_bp.post("/warehouses")
@jwt_required()
@permission_required("warehouses.manage")
def create_warehouse():
    current_user = get_current_user()
    payload = WarehouseSchema().load(request.get_json() or {})
    payload = normalize_warehouse_payload(payload)
    validate_warehouse_required_fields(payload)
    validate_unique_warehouse_code(payload.get("warehouse_code"))

    warehouse = Warehouse(**payload)
    db.session.add(warehouse)
    try:
        db.session.flush()
        audit_warehouse_change("warehouses.created", current_user.id, warehouse)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        abort(409, description="Không thể tạo mới kho với thông tin hiện tại.")
    return jsonify({"item": serialize_warehouse(warehouse)}), 201


@warehouses_bp.get("/warehouses/<int:item_id>")
@jwt_required()
@permission_required("warehouses.view")
def get_warehouse(item_id):
    warehouse = db.get_or_404(Warehouse, item_id)
    return jsonify({"item": serialize_warehouse(warehouse)})


@warehouses_bp.put("/warehouses/<int:item_id>")
@jwt_required()
@permission_required("warehouses.manage")
def update_warehouse(item_id):
    current_user = get_current_user()
    warehouse = db.get_or_404(Warehouse, item_id)
    payload = WarehouseSchema(partial=True).load(request.get_json() or {})
    payload = normalize_warehouse_payload(payload)
    validate_warehouse_required_fields(payload)

    if "warehouse_code" in payload:
        validate_unique_warehouse_code(payload.get("warehouse_code"), warehouse.id)

    for field_name, value in payload.items():
        setattr(warehouse, field_name, value)

    try:
        audit_warehouse_change("warehouses.updated", current_user.id, warehouse)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        abort(409, description="Không thể cập nhật kho với thông tin hiện tại.")
    return jsonify({"item": serialize_warehouse(warehouse)})


@warehouses_bp.delete("/warehouses/<int:item_id>")
@jwt_required()
@permission_required("warehouses.manage")
def delete_warehouse(item_id):
    current_user = get_current_user()
    warehouse = db.get_or_404(Warehouse, item_id)
    if warehouse_has_dependencies(warehouse):
        abort(409, description="Kho đang có vị trí hoặc dữ liệu tồn kho liên quan nên chưa thể xóa.")

    try:
        audit_warehouse_change("warehouses.deleted", current_user.id, warehouse)
        db.session.delete(warehouse)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        abort(409, description="Kho đang được tham chiếu ở nghiệp vụ khác nên chưa thể xóa.")
    return jsonify({"message": "Xóa kho thành công."})


@warehouses_bp.get("/locations")
@jwt_required()
@permission_required("locations.view")
def list_locations():
    query = WarehouseLocation.query.join(Warehouse)
    search = normalize_optional_text(request.args.get("search"))
    if search:
        like_term = f"%{search}%"
        query = query.filter(
            or_(
                WarehouseLocation.location_code.ilike(like_term),
                WarehouseLocation.location_name.ilike(like_term),
                Warehouse.warehouse_code.ilike(like_term),
                Warehouse.warehouse_name.ilike(like_term),
            )
        )

    status = normalize_optional_text(request.args.get("status"))
    if status:
        query = query.filter(WarehouseLocation.status == status)

    warehouse_id = request.args.get("warehouse_id", type=int)
    if warehouse_id:
        query = query.filter(WarehouseLocation.warehouse_id == warehouse_id)

    query = apply_sort(query, LOCATION_SORT_FIELDS, "location_code").order_by(WarehouseLocation.warehouse_id.asc())
    page, page_size = get_pagination_params()
    pagination = query.paginate(page=page, per_page=page_size, error_out=False)
    return jsonify(build_pagination_payload(pagination, serialize_warehouse_location))


@warehouses_bp.post("/locations")
@jwt_required()
@permission_required("locations.manage")
def create_location():
    current_user = get_current_user()
    payload = WarehouseLocationSchema().load(request.get_json() or {})
    payload = normalize_location_payload(payload)
    validate_location_required_fields(payload)
    validate_warehouse_exists(payload.get("warehouse_id"))
    validate_unique_location_code(payload.get("warehouse_id"), payload.get("location_code"))

    location = WarehouseLocation(**payload)
    db.session.add(location)
    try:
        db.session.flush()
        audit_location_change("locations.created", current_user.id, location)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        abort(409, description="Không thể tạo mới vị trí với thông tin hiện tại.")
    return jsonify({"item": serialize_warehouse_location(location)}), 201


@warehouses_bp.get("/locations/<int:item_id>")
@jwt_required()
@permission_required("locations.view")
def get_location(item_id):
    location = db.get_or_404(WarehouseLocation, item_id)
    return jsonify({"item": serialize_warehouse_location(location)})


@warehouses_bp.put("/locations/<int:item_id>")
@jwt_required()
@permission_required("locations.manage")
def update_location(item_id):
    current_user = get_current_user()
    location = db.get_or_404(WarehouseLocation, item_id)
    payload = WarehouseLocationSchema(partial=True).load(request.get_json() or {})
    payload = normalize_location_payload(payload)
    validate_location_required_fields(payload)

    target_warehouse_id = payload.get("warehouse_id", location.warehouse_id)
    if "warehouse_id" in payload:
        if payload["warehouse_id"] != location.warehouse_id and location_has_dependencies(location):
            abort(
                409,
                description="Vị trí đã phát sinh dữ liệu tồn kho hoặc biến động nên không thể chuyển sang kho khác.",
            )
        validate_warehouse_exists(target_warehouse_id)
    if "location_code" in payload or "warehouse_id" in payload:
        validate_unique_location_code(
            target_warehouse_id,
            payload.get("location_code", location.location_code),
            location.id,
        )

    for field_name, value in payload.items():
        setattr(location, field_name, value)

    try:
        audit_location_change("locations.updated", current_user.id, location)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        abort(409, description="Không thể cập nhật vị trí với thông tin hiện tại.")
    return jsonify({"item": serialize_warehouse_location(location)})


@warehouses_bp.delete("/locations/<int:item_id>")
@jwt_required()
@permission_required("locations.manage")
def delete_location(item_id):
    current_user = get_current_user()
    location = db.get_or_404(WarehouseLocation, item_id)
    if location_has_dependencies(location):
        abort(409, description="Vị trí đang có dữ liệu tồn kho hoặc biến động nên chưa thể xóa.")

    try:
        audit_location_change("locations.deleted", current_user.id, location)
        db.session.delete(location)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        abort(409, description="Vị trí đang được tham chiếu ở nghiệp vụ khác nên chưa thể xóa.")
    return jsonify({"message": "Xóa vị trí thành công."})
