from flask import Blueprint, abort, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError

from ..audit import log_audit_event
from ..extensions import db
from ..models import BankAccount, Category, Customer, Supplier
from ..permissions import get_current_user, permission_required
from ..schemas import BankAccountSchema, CategorySchema, CustomerSchema, SupplierSchema
from ..serializers import (
    serialize_bank_account,
    serialize_category,
    serialize_customer,
    serialize_supplier,
)

catalogs_bp = Blueprint("catalogs", __name__)


RESOURCE_CONFIG = {
    "categories": {
        "model": Category,
        "schema": CategorySchema,
        "serializer": serialize_category,
        "view_permission": "categories.view",
        "manage_permission": "categories.manage",
        "search_fields": ["category_name", "description"],
        "sort_fields": {
            "id": Category.id,
            "category_name": Category.category_name,
            "created_at": Category.created_at,
            "updated_at": Category.updated_at,
        },
        "default_sort_by": "category_name",
        "default_sort_order": "asc",
        "unique_fields": {
            "category_name": "Tên nhóm hàng đã tồn tại.",
        },
        "required_text_fields": {
            "category_name": "Tên nhóm hàng không được để trống.",
        },
        "audit_entity_type": "category",
        "audit_label_field": "category_name",
        "resource_label": "nhóm hàng",
    },
    "suppliers": {
        "model": Supplier,
        "schema": SupplierSchema,
        "serializer": serialize_supplier,
        "view_permission": "suppliers.view",
        "manage_permission": "suppliers.manage",
        "search_fields": ["supplier_code", "supplier_name", "email", "phone"],
        "sort_fields": {
            "id": Supplier.id,
            "supplier_code": Supplier.supplier_code,
            "supplier_name": Supplier.supplier_name,
            "status": Supplier.status,
            "created_at": Supplier.created_at,
            "updated_at": Supplier.updated_at,
        },
        "default_sort_by": "supplier_code",
        "default_sort_order": "asc",
        "status_field": "status",
        "unique_fields": {
            "supplier_code": "Mã nhà cung cấp đã tồn tại.",
        },
        "required_text_fields": {
            "supplier_code": "Mã nhà cung cấp không được để trống.",
            "supplier_name": "Tên nhà cung cấp không được để trống.",
        },
        "audit_entity_type": "supplier",
        "audit_label_field": "supplier_name",
        "resource_label": "nhà cung cấp",
    },
    "customers": {
        "model": Customer,
        "schema": CustomerSchema,
        "serializer": serialize_customer,
        "view_permission": "customers.view",
        "manage_permission": "customers.manage",
        "search_fields": ["customer_code", "customer_name", "email", "phone"],
        "sort_fields": {
            "id": Customer.id,
            "customer_code": Customer.customer_code,
            "customer_name": Customer.customer_name,
            "status": Customer.status,
            "created_at": Customer.created_at,
            "updated_at": Customer.updated_at,
        },
        "default_sort_by": "customer_code",
        "default_sort_order": "asc",
        "status_field": "status",
        "unique_fields": {
            "customer_code": "Mã khách hàng đã tồn tại.",
        },
        "required_text_fields": {
            "customer_code": "Mã khách hàng không được để trống.",
            "customer_name": "Tên khách hàng không được để trống.",
        },
        "audit_entity_type": "customer",
        "audit_label_field": "customer_name",
        "resource_label": "khách hàng",
    },
    "bank-accounts": {
        "model": BankAccount,
        "schema": BankAccountSchema,
        "serializer": serialize_bank_account,
        "view_permission": "bank_accounts.view",
        "manage_permission": "bank_accounts.manage",
        "search_fields": ["bank_name", "account_number", "account_holder", "branch"],
        "sort_fields": {
            "id": BankAccount.id,
            "bank_name": BankAccount.bank_name,
            "account_number": BankAccount.account_number,
            "account_holder": BankAccount.account_holder,
            "status": BankAccount.status,
            "created_at": BankAccount.created_at,
            "updated_at": BankAccount.updated_at,
        },
        "default_sort_by": "account_number",
        "default_sort_order": "asc",
        "status_field": "status",
        "unique_fields": {
            "account_number": "Số tài khoản đã tồn tại.",
        },
        "required_text_fields": {
            "bank_name": "Tên ngân hàng không được để trống.",
            "account_number": "Số tài khoản không được để trống.",
            "account_holder": "Chủ tài khoản không được để trống.",
        },
        "audit_entity_type": "bank_account",
        "audit_label_field": "account_number",
        "resource_label": "tài khoản ngân hàng",
    },
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


def get_config(resource_name):
    config = RESOURCE_CONFIG.get(resource_name)
    if not config:
        abort(404, description="Không tìm thấy tài nguyên được yêu cầu.")
    return config


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


def apply_sort(query, config):
    sort_by = normalize_optional_text(request.args.get("sort_by")) or config["default_sort_by"]
    sort_order = (request.args.get("sort_order") or config["default_sort_order"]).strip().lower()
    column = config["sort_fields"].get(sort_by, config["sort_fields"][config["default_sort_by"]])
    if sort_order == "desc":
        return query.order_by(column.desc())
    return query.order_by(column.asc())


def normalize_payload(payload):
    normalized_payload = dict(payload)
    for field_name in [
        "category_name",
        "supplier_code",
        "supplier_name",
        "customer_code",
        "customer_name",
        "bank_name",
        "account_number",
        "account_holder",
        "branch",
        "description",
        "phone",
        "address",
    ]:
        if field_name in normalized_payload:
            normalized_payload[field_name] = normalize_optional_text(normalized_payload[field_name])
    if "email" in normalized_payload:
        normalized_payload["email"] = normalize_optional_text(normalized_payload["email"], lower=True)
    return normalized_payload


def validate_required_text_fields(config, payload):
    for field_name, error_message in config["required_text_fields"].items():
        if field_name in payload and not payload[field_name]:
            abort(400, description=error_message)


def validate_unique_fields(config, payload, record_id=None):
    model = config["model"]
    for field_name, error_message in config["unique_fields"].items():
        value = payload.get(field_name)
        if not value:
            continue
        column = getattr(model, field_name)
        query = model.query.filter(func.lower(column) == value.lower())
        if record_id is not None:
            query = query.filter(model.id != record_id)
        if query.first():
            abort(409, description=error_message)


def apply_payload(record, payload):
    for field_name, value in payload.items():
        setattr(record, field_name, value)


def audit_catalog_change(action, config, actor_user_id, record):
    label = getattr(record, config["audit_label_field"], None)
    log_audit_event(
        action,
        config["audit_entity_type"],
        f"{action.split('.')[1].capitalize()} {config['resource_label']} {label}.",
        actor_user_id=actor_user_id,
        entity_id=record.id,
        entity_label=label,
    )


def catalog_collection(resource_name):
    config = get_config(resource_name)
    model = config["model"]

    if request.method == "GET":
        permission_required(config["view_permission"])(lambda: None)()
        query = model.query
        search = normalize_optional_text(request.args.get("search"))
        if search:
            like_term = f"%{search}%"
            query = query.filter(
                or_(*[getattr(model, field_name).ilike(like_term) for field_name in config["search_fields"]])
            )

        status_field = config.get("status_field")
        if status_field:
            status = normalize_optional_text(request.args.get("status"))
            if status:
                query = query.filter(getattr(model, status_field) == status)

        query = apply_sort(query, config)
        page, page_size = get_pagination_params()
        pagination = query.paginate(page=page, per_page=page_size, error_out=False)
        return jsonify(build_pagination_payload(pagination, config["serializer"]))

    permission_required(config["manage_permission"])(lambda: None)()
    current_user = get_current_user()
    payload = config["schema"]().load(request.get_json() or {})
    payload = normalize_payload(payload)
    validate_required_text_fields(config, payload)
    validate_unique_fields(config, payload)

    record = model()
    apply_payload(record, payload)
    db.session.add(record)
    try:
        db.session.flush()
        audit_catalog_change(f"{resource_name.replace('-', '_')}.created", config, current_user.id, record)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        abort(409, description="Không thể tạo mới dữ liệu với thông tin hiện tại.")
    return jsonify({"item": config["serializer"](record)}), 201


def catalog_detail(resource_name, item_id):
    config = get_config(resource_name)
    model = config["model"]
    record = db.get_or_404(model, item_id)

    if request.method == "GET":
        permission_required(config["view_permission"])(lambda: None)()
        return jsonify({"item": config["serializer"](record)})

    if request.method == "PUT":
        permission_required(config["manage_permission"])(lambda: None)()
        current_user = get_current_user()
        payload = config["schema"](partial=True).load(request.get_json() or {})
        payload = normalize_payload(payload)
        validate_required_text_fields(config, payload)
        validate_unique_fields(config, payload, record.id)
        apply_payload(record, payload)
        try:
            audit_catalog_change(f"{resource_name.replace('-', '_')}.updated", config, current_user.id, record)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            abort(409, description="Không thể cập nhật dữ liệu với thông tin hiện tại.")
        return jsonify({"item": config["serializer"](record)})

    permission_required(config["manage_permission"])(lambda: None)()
    current_user = get_current_user()
    try:
        audit_catalog_change(f"{resource_name.replace('-', '_')}.deleted", config, current_user.id, record)
        db.session.delete(record)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        abort(409, description="Bản ghi này đang được tham chiếu ở nghiệp vụ khác nên chưa thể xóa.")
    return jsonify({"message": "Xóa bản ghi thành công."})


@catalogs_bp.route("/categories", methods=["GET", "POST"])
@jwt_required()
def categories_collection():
    return catalog_collection("categories")


@catalogs_bp.route("/categories/<int:item_id>", methods=["GET", "PUT", "DELETE"])
@jwt_required()
def categories_detail(item_id):
    return catalog_detail("categories", item_id)


@catalogs_bp.route("/suppliers", methods=["GET", "POST"])
@jwt_required()
def suppliers_collection():
    return catalog_collection("suppliers")


@catalogs_bp.route("/suppliers/<int:item_id>", methods=["GET", "PUT", "DELETE"])
@jwt_required()
def suppliers_detail(item_id):
    return catalog_detail("suppliers", item_id)


@catalogs_bp.route("/customers", methods=["GET", "POST"])
@jwt_required()
def customers_collection():
    return catalog_collection("customers")


@catalogs_bp.route("/customers/<int:item_id>", methods=["GET", "PUT", "DELETE"])
@jwt_required()
def customers_detail(item_id):
    return catalog_detail("customers", item_id)


@catalogs_bp.route("/bank-accounts", methods=["GET", "POST"])
@jwt_required()
def bank_accounts_collection():
    return catalog_collection("bank-accounts")


@catalogs_bp.route("/bank-accounts/<int:item_id>", methods=["GET", "PUT", "DELETE"])
@jwt_required()
def bank_accounts_detail(item_id):
    return catalog_detail("bank-accounts", item_id)
