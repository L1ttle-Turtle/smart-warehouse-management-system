from __future__ import annotations

from datetime import datetime

from flask import Blueprint, abort, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_
from sqlalchemy.sql.sqltypes import Boolean, DateTime, Float, Integer

from ..extensions import db
from ..models import (
    BankAccount,
    Category,
    Customer,
    Employee,
    Product,
    Role,
    Task,
    User,
    Warehouse,
    WarehouseLocation,
    Supplier,
)
from ..permissions import get_current_user, permission_required
from ..serializers import SERIALIZER_MAP, serialize_role
from ..services.communications import create_notification
from ..utils import parse_iso_datetime

crud_bp = Blueprint("crud", __name__)


def serialize_record(record):
    serializer = SERIALIZER_MAP.get(type(record), lambda value: value.to_dict())
    return serializer(record)


def coerce_value(column, value):
    if value == "" and column.nullable:
        return None
    if isinstance(column.type, Integer) and value is not None:
        return int(value)
    if isinstance(column.type, Float) and value is not None:
        return float(value)
    if isinstance(column.type, Boolean):
        return bool(value)
    if isinstance(column.type, DateTime) and value:
        return parse_iso_datetime(value)
    return value


def prepare_user(record, payload, is_create):
    password = payload.pop("password", None)
    if is_create and not password:
        password = "Password123!"
    if password:
        record.set_password(password)


def prepare_task(record, payload, is_create):
    if not payload.get("assigned_by") and is_create:
        payload["assigned_by"] = get_current_user().id


def after_task_save(task, created):
    if task.assigned_to:
        create_notification(
            sender_id=get_current_user().id,
            receiver_id=task.assigned_to,
            title="Cong viec moi",
            content=f"Ban duoc giao cong viec: {task.title}",
            type="task",
        )


RESOURCE_MAP = {
    "users": {
        "model": User,
        "fields": ["username", "full_name", "email", "phone", "role_id", "status"],
        "view_permission": "users.manage",
        "manage_permission": "users.manage",
        "pre_save": prepare_user,
        "search_fields": ["username", "full_name", "email"],
    },
    "employees": {
        "model": Employee,
        "fields": [
            "employee_code",
            "user_id",
            "full_name",
            "department",
            "position",
            "phone",
            "email",
            "responsibility",
            "status",
        ],
        "view_permission": "employees.view",
        "manage_permission": "employees.manage",
        "search_fields": ["employee_code", "full_name", "department", "position"],
    },
    "categories": {
        "model": Category,
        "fields": ["category_name", "description"],
        "view_permission": "categories.view",
        "manage_permission": "categories.manage",
        "search_fields": ["category_name", "description"],
    },
    "suppliers": {
        "model": Supplier,
        "fields": ["supplier_code", "supplier_name", "email", "phone", "address", "status"],
        "view_permission": "suppliers.view",
        "manage_permission": "suppliers.manage",
        "search_fields": ["supplier_code", "supplier_name"],
    },
    "customers": {
        "model": Customer,
        "fields": ["customer_code", "customer_name", "email", "phone", "address", "status"],
        "view_permission": "customers.view",
        "manage_permission": "customers.manage",
        "search_fields": ["customer_code", "customer_name"],
    },
    "warehouses": {
        "model": Warehouse,
        "fields": [
            "warehouse_code",
            "warehouse_name",
            "address",
            "manager_id",
            "capacity",
            "status",
        ],
        "view_permission": "warehouses.view",
        "manage_permission": "warehouses.manage",
        "search_fields": ["warehouse_code", "warehouse_name", "address"],
    },
    "locations": {
        "model": WarehouseLocation,
        "fields": ["warehouse_id", "zone", "shelf", "bin_code", "note"],
        "view_permission": "locations.view",
        "manage_permission": "locations.manage",
        "search_fields": ["bin_code", "zone", "shelf"],
    },
    "products": {
        "model": Product,
        "fields": [
            "product_code",
            "product_name",
            "category_id",
            "supplier_id",
            "unit",
            "import_price",
            "export_price",
            "min_stock",
            "max_stock",
            "status",
            "description",
        ],
        "view_permission": "products.view",
        "manage_permission": "products.manage",
        "search_fields": ["product_code", "product_name"],
    },
    "bank-accounts": {
        "model": BankAccount,
        "fields": ["bank_name", "account_number", "account_holder", "branch", "status"],
        "view_permission": "bank_accounts.view",
        "manage_permission": "bank_accounts.manage",
        "search_fields": ["bank_name", "account_number", "account_holder"],
    },
    "tasks": {
        "model": Task,
        "fields": [
            "title",
            "description",
            "assigned_by",
            "assigned_to",
            "related_module",
            "deadline",
            "status",
        ],
        "view_permission": "tasks.view",
        "manage_permission": "tasks.manage",
        "search_fields": ["title", "related_module", "status"],
        "pre_save": prepare_task,
        "after_save": after_task_save,
    },
}


@crud_bp.get("/roles")
@jwt_required()
@permission_required("roles.view")
def list_roles():
    roles = Role.query.order_by(Role.role_name.asc()).all()
    return jsonify({"items": [serialize_role(role) for role in roles]})


@crud_bp.get("/directory/users")
@jwt_required()
def user_directory():
    items = User.query.filter_by(status="active").order_by(User.full_name.asc()).all()
    return jsonify({"items": [serialize_record(item) for item in items]})


@crud_bp.route("/<resource_name>", methods=["GET", "POST"])
@jwt_required()
def collection(resource_name):
    config = RESOURCE_MAP.get(resource_name)
    if not config:
        abort(404, description="Resource not found.")

    view_permission = config["view_permission"]
    manage_permission = config["manage_permission"]
    user = get_current_user()
    if request.method == "GET":
        permission_required(view_permission)(lambda: None)()
        model = config["model"]
        query = model.query
        search = request.args.get("search")
        search_fields = config.get("search_fields", [])
        if search and search_fields:
            filters = [getattr(model, field).ilike(f"%{search}%") for field in search_fields]
            query = query.filter(or_(*filters))
        if resource_name == "tasks" and manage_permission not in user.permission_names:
            query = query.filter(Task.assigned_to == user.id)
        items = query.order_by(model.id.desc()).all()
        return jsonify({"items": [serialize_record(item) for item in items]})

    permission_required(manage_permission)(lambda: None)()
    model = config["model"]
    payload = request.get_json() or {}
    record = model()
    pre_save = config.get("pre_save")
    if pre_save:
        pre_save(record, payload, True)
    for field in config["fields"]:
        if field not in payload:
            continue
        column = getattr(model, field).property.columns[0]
        setattr(record, field, coerce_value(column, payload[field]))
    db.session.add(record)
    try:
        db.session.flush()
        after_save = config.get("after_save")
        if after_save:
            after_save(record, True)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        abort(409, description="Duplicate or invalid data.")
    return jsonify({"item": serialize_record(record)}), 201


@crud_bp.route("/<resource_name>/<int:item_id>", methods=["GET", "PUT", "DELETE"])
@jwt_required()
def resource_detail(resource_name, item_id):
    config = RESOURCE_MAP.get(resource_name)
    if not config:
        abort(404, description="Resource not found.")

    model = config["model"]
    record = db.get_or_404(model, item_id)
    user = get_current_user()
    if request.method == "GET":
        permission_required(config["view_permission"])(lambda: None)()
        if resource_name == "tasks" and config["manage_permission"] not in user.permission_names:
            if record.assigned_to != user.id:
                abort(403, description="You do not have access to this task.")
        return jsonify({"item": serialize_record(record)})

    permission_required(config["manage_permission"])(lambda: None)()
    if request.method == "DELETE":
        db.session.delete(record)
        db.session.commit()
        return jsonify({"message": "Deleted successfully."})

    payload = request.get_json() or {}
    pre_save = config.get("pre_save")
    if pre_save:
        pre_save(record, payload, False)
    for field in config["fields"]:
        if field not in payload:
            continue
        column = getattr(model, field).property.columns[0]
        setattr(record, field, coerce_value(column, payload[field]))
    try:
        db.session.flush()
        after_save = config.get("after_save")
        if after_save:
            after_save(record, False)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        abort(409, description="Duplicate or invalid data.")
    return jsonify({"item": serialize_record(record)})
