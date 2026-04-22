from flask import Blueprint, jsonify
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
    items = InventoryMovement.query.order_by(InventoryMovement.created_at.desc()).all()
    return jsonify({"items": [serialize_inventory_movement(item) for item in items]})
