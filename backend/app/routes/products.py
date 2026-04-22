from flask import Blueprint, abort, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError

from ..audit import log_audit_event
from ..extensions import db
from ..models import Category, Product
from ..permissions import get_current_user, permission_required
from ..schemas import ProductSchema
from ..serializers import serialize_product

products_bp = Blueprint("products", __name__)


SORT_FIELDS = {
    "id": Product.id,
    "product_code": Product.product_code,
    "product_name": Product.product_name,
    "quantity_total": Product.quantity_total,
    "min_stock": Product.min_stock,
    "status": Product.status,
    "created_at": Product.created_at,
    "updated_at": Product.updated_at,
}


def normalize_optional_text(value):
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return value


def get_pagination_params():
    page = max(request.args.get("page", default=1, type=int), 1)
    page_size = min(max(request.args.get("page_size", default=10, type=int), 1), 100)
    return page, page_size


def build_pagination_payload(pagination):
    return {
        "items": [serialize_product(item) for item in pagination.items],
        "total": pagination.total,
        "page": pagination.page,
        "page_size": pagination.per_page,
    }


def apply_sort(query):
    sort_by = normalize_optional_text(request.args.get("sort_by")) or "product_code"
    sort_order = (request.args.get("sort_order") or "asc").strip().lower()
    column = SORT_FIELDS.get(sort_by, Product.product_code)
    if sort_order == "desc":
        return query.order_by(column.desc())
    return query.order_by(column.asc())


def normalize_payload(payload):
    normalized_payload = dict(payload)
    for field_name in ["product_code", "product_name", "description"]:
        if field_name in normalized_payload:
            normalized_payload[field_name] = normalize_optional_text(normalized_payload[field_name])
    return normalized_payload


def validate_required_text_fields(payload):
    if "product_code" in payload and not payload["product_code"]:
        abort(400, description="Mã sản phẩm không được để trống.")
    if "product_name" in payload and not payload["product_name"]:
        abort(400, description="Tên sản phẩm không được để trống.")


def validate_category(category_id):
    if category_id is None:
        abort(400, description="Nhóm hàng là bắt buộc.")
    category = db.session.get(Category, category_id)
    if not category:
        abort(400, description="Nhóm hàng không hợp lệ.")
    return category


def validate_unique_product_code(product_code, record_id=None):
    if not product_code:
        return
    query = Product.query.filter(func.lower(Product.product_code) == product_code.lower())
    if record_id is not None:
        query = query.filter(Product.id != record_id)
    if query.first():
        abort(409, description="Mã sản phẩm đã tồn tại.")


def audit_product_change(action, actor_user_id, product):
    log_audit_event(
        action,
        "product",
        f"{action.split('.')[1].capitalize()} sản phẩm {product.product_name}.",
        actor_user_id=actor_user_id,
        entity_id=product.id,
        entity_label=product.product_name,
    )


@products_bp.get("/products")
@jwt_required()
@permission_required("products.view")
def list_products():
    query = Product.query.outerjoin(Category)
    search = normalize_optional_text(request.args.get("search"))
    if search:
        like_term = f"%{search}%"
        query = query.filter(
            or_(
                Product.product_code.ilike(like_term),
                Product.product_name.ilike(like_term),
                Product.description.ilike(like_term),
                Category.category_name.ilike(like_term),
            )
        )

    status = normalize_optional_text(request.args.get("status"))
    if status:
        query = query.filter(Product.status == status)

    category_id = request.args.get("category_id", type=int)
    if category_id:
        query = query.filter(Product.category_id == category_id)

    query = apply_sort(query)
    page, page_size = get_pagination_params()
    pagination = query.paginate(page=page, per_page=page_size, error_out=False)
    return jsonify(build_pagination_payload(pagination))


@products_bp.post("/products")
@jwt_required()
@permission_required("products.manage")
def create_product():
    current_user = get_current_user()
    payload = ProductSchema().load(request.get_json() or {})
    payload = normalize_payload(payload)
    payload.pop("quantity_total", None)
    validate_required_text_fields(payload)
    validate_category(payload.get("category_id"))
    validate_unique_product_code(payload.get("product_code"))

    product = Product(**payload)
    db.session.add(product)
    try:
        db.session.flush()
        audit_product_change("products.created", current_user.id, product)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        abort(409, description="Không thể tạo mới sản phẩm với thông tin hiện tại.")
    return jsonify({"item": serialize_product(product)}), 201


@products_bp.get("/products/<int:item_id>")
@jwt_required()
@permission_required("products.view")
def get_product(item_id):
    product = db.get_or_404(Product, item_id)
    return jsonify({"item": serialize_product(product)})


@products_bp.put("/products/<int:item_id>")
@jwt_required()
@permission_required("products.manage")
def update_product(item_id):
    current_user = get_current_user()
    product = db.get_or_404(Product, item_id)
    payload = ProductSchema(partial=True).load(request.get_json() or {})
    payload = normalize_payload(payload)
    payload.pop("quantity_total", None)
    validate_required_text_fields(payload)

    if "category_id" in payload:
        validate_category(payload.get("category_id"))
    if "product_code" in payload:
        validate_unique_product_code(payload.get("product_code"), product.id)

    for field_name, value in payload.items():
        setattr(product, field_name, value)

    try:
        audit_product_change("products.updated", current_user.id, product)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        abort(409, description="Không thể cập nhật sản phẩm với thông tin hiện tại.")
    return jsonify({"item": serialize_product(product)})


@products_bp.delete("/products/<int:item_id>")
@jwt_required()
@permission_required("products.manage")
def delete_product(item_id):
    current_user = get_current_user()
    product = db.get_or_404(Product, item_id)
    try:
        audit_product_change("products.deleted", current_user.id, product)
        db.session.delete(product)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        abort(409, description="Sản phẩm đang được tham chiếu ở nghiệp vụ khác nên chưa thể xóa.")
    return jsonify({"message": "Xóa sản phẩm thành công."})
