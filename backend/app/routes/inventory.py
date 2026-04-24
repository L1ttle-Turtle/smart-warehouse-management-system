from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from ..models import Inventory, InventoryMovement
from ..permissions import permission_required
from ..serializers import serialize_inventory_movement, serialize_inventory_row

inventory_bp = Blueprint("inventory", __name__)


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

    reference_id = request.args.get("reference_id", type=int)
    if reference_id is not None:
        query = query.filter(InventoryMovement.reference_id == reference_id)

    items = query.order_by(InventoryMovement.created_at.desc()).all()
    return jsonify({"items": [serialize_inventory_movement(item) for item in items]})
