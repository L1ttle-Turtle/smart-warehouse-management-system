from flask import Blueprint, abort, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import joinedload

from ..audit import log_audit_event
from ..extensions import db
from ..models import Category, Inventory, InventoryMovement, Product, Warehouse, WarehouseLocation
from ..permissions import get_current_user, permission_required
from ..schemas import InventoryAdjustmentSchema
from ..serializers import serialize_inventory_movement, serialize_inventory_row
from ..services.inventory import adjust_inventory, validate_location_in_warehouse

inventory_bp = Blueprint("inventory", __name__)


STOCK_STATUS_VALUES = {"in_stock", "low_stock", "out_of_stock"}
SORT_FIELDS = {
    "updated_at": Inventory.updated_at,
    "created_at": Inventory.created_at,
    "quantity": Inventory.quantity,
    "min_stock": Product.min_stock,
    "product_code": Product.product_code,
    "product_name": Product.product_name,
    "warehouse_name": Warehouse.warehouse_name,
    "location_name": WarehouseLocation.location_name,
}


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


def parse_bool_arg(name):
    raw_value = request.args.get(name)
    if raw_value is None:
        return None

    value = raw_value.strip().lower()
    if value in {"true", "1", "yes"}:
        return True
    if value in {"false", "0", "no"}:
        return False
    abort(400, description=f"{name} phải là true hoặc false.")


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


def validate_warehouse(warehouse_id):
    warehouse = db.session.get(Warehouse, warehouse_id)
    if not warehouse:
        abort(400, description="Kho không hợp lệ.")
    return warehouse


def validate_location(location_id):
    location = db.session.get(WarehouseLocation, location_id)
    if not location:
        abort(400, description="Vị trí kho không hợp lệ.")
    return location


def validate_product(product_id):
    product = db.session.get(Product, product_id)
    if not product:
        abort(400, description="Sản phẩm không hợp lệ.")
    return product


def validate_category(category_id):
    category = db.session.get(Category, category_id)
    if not category:
        abort(400, description="Nhóm hàng không hợp lệ.")
    return category


def build_inventory_query():
    return (
        Inventory.query.join(Inventory.product)
        .join(Inventory.warehouse)
        .join(Inventory.location)
        .options(
            joinedload(Inventory.product).joinedload(Product.category),
            joinedload(Inventory.warehouse),
            joinedload(Inventory.location),
        )
    )


def apply_inventory_filters(query):
    q = normalize_optional_text(request.args.get("q")) or normalize_optional_text(request.args.get("search"))
    warehouse_id = parse_optional_int_arg("warehouse_id")
    location_id = parse_optional_int_arg("location_id")
    product_id = parse_optional_int_arg("product_id")
    category_id = parse_optional_int_arg("category_id")
    stock_status = normalize_optional_text(request.args.get("stock_status"),)
    low_stock_only = parse_bool_arg("low_stock_only")

    if warehouse_id is not None:
        validate_warehouse(warehouse_id)
        query = query.filter(Inventory.warehouse_id == warehouse_id)

    if location_id is not None:
        location = validate_location(location_id)
        if warehouse_id is not None and location.warehouse_id != warehouse_id:
            abort(400, description="Vị trí kho không thuộc kho đã chọn.")
        query = query.filter(Inventory.location_id == location_id)

    if product_id is not None:
        validate_product(product_id)
        query = query.filter(Inventory.product_id == product_id)

    if category_id is not None:
        validate_category(category_id)
        query = query.filter(Product.category_id == category_id)

    if q:
        like_term = f"%{q}%"
        query = query.filter(
            or_(
                Product.product_code.ilike(like_term),
                Product.product_name.ilike(like_term),
            )
        )

    if stock_status:
        if stock_status not in STOCK_STATUS_VALUES:
            abort(400, description="stock_status không hợp lệ.")

        safe_min_stock = func.coalesce(Product.min_stock, 0)
        if stock_status == "out_of_stock":
            query = query.filter(Inventory.quantity <= 0)
        elif stock_status == "low_stock":
            query = query.filter(
                and_(
                    Inventory.quantity > 0,
                    Inventory.quantity <= safe_min_stock,
                )
            )
        else:
            query = query.filter(Inventory.quantity > safe_min_stock)
    elif low_stock_only is True:
        safe_min_stock = func.coalesce(Product.min_stock, 0)
        query = query.filter(
            or_(
                Inventory.quantity <= 0,
                and_(
                    Inventory.quantity > 0,
                    Inventory.quantity <= safe_min_stock,
                ),
            )
        )

    return query


def apply_inventory_sort(query):
    sort_by = normalize_optional_text(request.args.get("sort_by")) or "updated_at"
    sort_order = (request.args.get("sort_order") or "desc").strip().lower()

    if sort_by not in SORT_FIELDS:
        abort(400, description="sort_by không hợp lệ.")
    if sort_order not in {"asc", "desc"}:
        abort(400, description="sort_order không hợp lệ.")

    column = SORT_FIELDS[sort_by]
    if sort_order == "asc":
        return query.order_by(column.asc(), Inventory.id.asc())
    return query.order_by(column.desc(), Inventory.id.desc())


@inventory_bp.get("")
@jwt_required()
@permission_required("inventory.view")
def list_inventory():
    query = apply_inventory_sort(apply_inventory_filters(build_inventory_query()))

    page = parse_positive_int_arg("page", 1)
    page_size_default = parse_positive_int_arg("page_size", 10, maximum=500)
    per_page = parse_positive_int_arg("per_page", page_size_default, maximum=500)
    has_pagination_args = any(
        request.args.get(name) is not None
        for name in {"page", "per_page", "page_size"}
    )

    if has_pagination_args:
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        items = pagination.items
        total = pagination.total
        current_page = pagination.page
        current_page_size = pagination.per_page
    else:
        items = query.all()
        total = len(items)
        current_page = 1
        current_page_size = total or per_page

    return jsonify(
        {
            "items": [serialize_inventory_row(item) for item in items],
            "total": total,
            "page": current_page,
            "page_size": current_page_size,
            "per_page": current_page_size,
        }
    )


@inventory_bp.get("/movements")
@jwt_required()
@permission_required("inventory.view")
def list_movements():
    query = InventoryMovement.query.options(
        joinedload(InventoryMovement.warehouse),
        joinedload(InventoryMovement.location),
        joinedload(InventoryMovement.product),
        joinedload(InventoryMovement.performer),
    )

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
