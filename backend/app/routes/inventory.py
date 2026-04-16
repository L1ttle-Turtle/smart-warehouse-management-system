from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from ..models import Inventory, InventoryMovement, Product
from ..permissions import permission_required
from ..serializers import serialize_inventory_movement, serialize_inventory_row, serialize_product

inventory_bp = Blueprint("inventory", __name__)


@inventory_bp.get("/")
@jwt_required()
@permission_required("inventory.view")
def list_inventory():
    query = Inventory.query
    warehouse_id = request.args.get("warehouse_id", type=int)
    product_id = request.args.get("product_id", type=int)
    if warehouse_id:
        query = query.filter(Inventory.warehouse_id == warehouse_id)
    if product_id:
        query = query.filter(Inventory.product_id == product_id)
    items = query.order_by(Inventory.updated_at.desc()).all()
    return jsonify({"items": [serialize_inventory_row(item) for item in items]})


@inventory_bp.get("/movements")
@jwt_required()
@permission_required("inventory.view")
def list_movements():
    query = InventoryMovement.query
    product_id = request.args.get("product_id", type=int)
    if product_id:
        query = query.filter(InventoryMovement.product_id == product_id)
    items = query.order_by(InventoryMovement.created_at.desc()).all()
    return jsonify({"items": [serialize_inventory_movement(item) for item in items]})


@inventory_bp.get("/low-stock")
@jwt_required()
@permission_required("inventory.view")
def low_stock():
    items = Product.query.filter(Product.quantity_total <= Product.min_stock).all()
    return jsonify({"items": [serialize_product(item) for item in items]})
