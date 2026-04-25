from flask import Blueprint, abort, jsonify, request
from flask_jwt_extended import jwt_required

from ..audit import log_audit_event
from ..extensions import db
from ..models import Inventory, InventoryMovement, Product, Warehouse
from ..permissions import get_current_user, permission_required
from ..schemas import InventoryAdjustmentSchema
from ..serializers import serialize_inventory_movement, serialize_inventory_row
from ..services.inventory import adjust_inventory, validate_location_in_warehouse

inventory_bp = Blueprint("inventory", __name__)


def normalize_optional_text(value):
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return value


def validate_warehouse(warehouse_id):
    warehouse = db.session.get(Warehouse, warehouse_id)
    if not warehouse:
        abort(400, description="Kho không hợp lệ.")
    return warehouse


def validate_product(product_id):
    product = db.session.get(Product, product_id)
    if not product:
        abort(400, description="Sản phẩm không hợp lệ.")
    return product


@inventory_bp.get("")
@jwt_required()
@permission_required("inventory.view")
def list_inventory():
    items = Inventory.query.order_by(Inventory.updated_at.desc()).all()
    return jsonify({"items": [serialize_inventory_row(item) for item in items]})


@inventory_bp.get("/movements")
@jwt_required()
@permission_required("inventory.view")
def list_movements():
    query = InventoryMovement.query

    reference_type = (request.args.get("reference_type") or "").strip()
    if reference_type:
        query = query.filter(InventoryMovement.reference_type == reference_type)

    raw_reference_id = request.args.get("reference_id")
    if raw_reference_id is not None and not raw_reference_id.strip():
        abort(400, description="reference_id phải là số nguyên hợp lệ.")
    reference_id = request.args.get("reference_id", type=int)
    if raw_reference_id is not None and reference_id is None:
        abort(400, description="reference_id phải là số nguyên hợp lệ.")
    if reference_id is not None:
        query = query.filter(InventoryMovement.reference_id == reference_id)

    items = query.order_by(InventoryMovement.created_at.desc()).all()
    return jsonify({"items": [serialize_inventory_movement(item) for item in items]})


@inventory_bp.post("/adjustments")
@jwt_required()
@permission_required("inventory.manage")
def create_inventory_adjustment():
    current_user = get_current_user()
    payload = InventoryAdjustmentSchema().load(request.get_json() or {})
    warehouse = validate_warehouse(payload["warehouse_id"])
    product = validate_product(payload["product_id"])
    note = normalize_optional_text(payload.get("note"))

    inventory_row = Inventory.query.filter_by(
        warehouse_id=payload["warehouse_id"],
        location_id=payload["location_id"],
        product_id=payload["product_id"],
    ).first()
    current_quantity = float(inventory_row.quantity if inventory_row else 0)
    actual_quantity = float(payload["actual_quantity"])
    delta = actual_quantity - current_quantity

    if delta == 0:
        abort(400, description="Số lượng thực tế không thay đổi, không cần điều chỉnh.")

    try:
        validate_location_in_warehouse(payload["location_id"], payload["warehouse_id"])
        movement = adjust_inventory(
            warehouse_id=payload["warehouse_id"],
            location_id=payload["location_id"],
            product_id=payload["product_id"],
            delta=delta,
            movement_type="adjustment",
            reference_type="inventory_adjustment",
            reference_id=None,
            actor_id=current_user.id,
            note=note or "",
        )
        inventory_row = Inventory.query.filter_by(
            warehouse_id=payload["warehouse_id"],
            location_id=payload["location_id"],
            product_id=payload["product_id"],
        ).first()
        log_audit_event(
            "inventory.adjusted",
            "inventory",
            (
                f"Điều chỉnh tồn kho {product.product_code} tại "
                f"{warehouse.warehouse_code} về {actual_quantity}."
            ),
            actor_user_id=current_user.id,
            entity_id=inventory_row.id if inventory_row else None,
            entity_label=f"{warehouse.warehouse_code}:{product.product_code}",
        )
        db.session.commit()
    except ValueError as exc:
        db.session.rollback()
        abort(400, description=str(exc))

    return (
        jsonify(
            {
                "inventory": serialize_inventory_row(inventory_row),
                "movement": serialize_inventory_movement(movement),
            }
        ),
        201,
    )
