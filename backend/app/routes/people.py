from flask import Blueprint, abort, current_app, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..models import Employee, Role, User
from ..permissions import get_current_user, permission_required
from ..schemas import (
    EmployeeCreateSchema,
    EmployeeUpdateSchema,
    UserCreateSchema,
    UserUpdateSchema,
)
from ..serializers import (
    serialize_employee,
    serialize_management_user,
    serialize_user_summary,
)

people_bp = Blueprint("people", __name__)


def normalize_optional_text(value):
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return value


def apply_user_payload(user, payload, is_create=False):
    if "username" in payload and payload["username"] is not None:
        user.username = payload["username"].strip()
    if "full_name" in payload and payload["full_name"] is not None:
        user.full_name = payload["full_name"].strip()
    if "email" in payload and payload["email"] is not None:
        user.email = payload["email"].strip().lower()
    if "phone" in payload:
        user.phone = normalize_optional_text(payload.get("phone"))
    if "role_id" in payload and payload["role_id"] is not None:
        role = db.session.get(Role, payload["role_id"])
        if not role:
            abort(400, description="Vai trò được chọn không tồn tại.")
        user.role_id = role.id
    if "status" in payload and payload["status"] is not None:
        user.status = payload["status"]

    password = payload.get("password")
    if is_create and not password:
        password = current_app.config["DEFAULT_PASSWORD"]
    if password:
        user.set_password(password)


def validate_user_uniqueness(user):
    duplicate_username = User.query.filter(
        User.username == user.username,
        User.id != getattr(user, "id", None),
    ).first()
    if duplicate_username:
        abort(409, description="Username đã tồn tại.")

    duplicate_email = User.query.filter(
        User.email == user.email,
        User.id != getattr(user, "id", None),
    ).first()
    if duplicate_email:
        abort(409, description="Email đã tồn tại.")


def apply_employee_payload(employee, payload):
    if "employee_code" in payload and payload["employee_code"] is not None:
        employee.employee_code = payload["employee_code"].strip()
    if "full_name" in payload and payload["full_name"] is not None:
        employee.full_name = payload["full_name"].strip()
    if "department" in payload:
        employee.department = normalize_optional_text(payload.get("department"))
    if "position" in payload:
        employee.position = normalize_optional_text(payload.get("position"))
    if "phone" in payload:
        employee.phone = normalize_optional_text(payload.get("phone"))
    if "email" in payload:
        email = payload.get("email")
        employee.email = email.strip().lower() if isinstance(email, str) and email.strip() else None
    if "status" in payload and payload["status"] is not None:
        employee.status = payload["status"]
    if "user_id" in payload:
        user_id = payload.get("user_id")
        if user_id is None:
            employee.user_id = None
        else:
            linked_user = db.session.get(User, user_id)
            if not linked_user:
                abort(400, description="Tài khoản liên kết không tồn tại.")
            employee.user_id = linked_user.id


def validate_employee_uniqueness(employee):
    duplicate_code = Employee.query.filter(
        Employee.employee_code == employee.employee_code,
        Employee.id != getattr(employee, "id", None),
    ).first()
    if duplicate_code:
        abort(409, description="Mã nhân viên đã tồn tại.")

    if employee.user_id is not None:
        duplicate_user = Employee.query.filter(
            Employee.user_id == employee.user_id,
            Employee.id != getattr(employee, "id", None),
        ).first()
        if duplicate_user:
            abort(409, description="Tài khoản này đã được liên kết với hồ sơ nhân sự khác.")


@people_bp.get("/directory/users")
@jwt_required()
@permission_required("employees.manage", "users.manage", any_of=True)
def directory_users():
    items = User.query.filter_by(status="active").order_by(User.full_name.asc()).all()
    return jsonify({"items": [serialize_user_summary(item) for item in items]})


@people_bp.get("/users")
@jwt_required()
@permission_required("users.view")
def list_users():
    search = normalize_optional_text(request.args.get("search"))
    query = User.query
    if search:
        like_term = f"%{search}%"
        query = query.filter(
            or_(
                User.username.ilike(like_term),
                User.full_name.ilike(like_term),
                User.email.ilike(like_term),
            )
        )
    items = query.order_by(User.id.desc()).all()
    return jsonify({"items": [serialize_management_user(item) for item in items]})


@people_bp.post("/users")
@jwt_required()
@permission_required("users.manage")
def create_user():
    payload = UserCreateSchema().load(request.get_json() or {})
    user = User()
    apply_user_payload(user, payload, True)
    validate_user_uniqueness(user)
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        abort(409, description="Không thể tạo tài khoản với dữ liệu hiện tại.")
    return jsonify({"item": serialize_management_user(user)}), 201


@people_bp.get("/users/<int:user_id>")
@jwt_required()
@permission_required("users.view")
def get_user(user_id):
    user = db.get_or_404(User, user_id)
    return jsonify({"item": serialize_management_user(user)})


@people_bp.put("/users/<int:user_id>")
@jwt_required()
@permission_required("users.manage")
def update_user(user_id):
    user = db.get_or_404(User, user_id)
    payload = UserUpdateSchema().load(request.get_json() or {})
    apply_user_payload(user, payload, False)
    validate_user_uniqueness(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        abort(409, description="Không thể cập nhật tài khoản với dữ liệu hiện tại.")
    return jsonify({"item": serialize_management_user(user)})


@people_bp.delete("/users/<int:user_id>")
@jwt_required()
@permission_required("users.manage")
def delete_user(user_id):
    current_user = get_current_user()
    user = db.get_or_404(User, user_id)
    if user.id == current_user.id:
        abort(400, description="Không thể xóa chính tài khoản đang đăng nhập.")
    if user.employee:
        abort(400, description="Tài khoản này đang liên kết với hồ sơ nhân sự và chưa thể xóa.")
    if user.delegations_granted or user.delegations_received:
        abort(400, description="Tài khoản này đang tham gia dữ liệu ủy quyền và chưa thể xóa.")
    db.session.delete(user)
    db.session.commit()
    return jsonify({"message": "Xóa tài khoản thành công."})


@people_bp.get("/employees")
@jwt_required()
@permission_required("employees.view")
def list_employees():
    search = normalize_optional_text(request.args.get("search"))
    query = Employee.query
    if search:
        like_term = f"%{search}%"
        query = query.filter(
            or_(
                Employee.employee_code.ilike(like_term),
                Employee.full_name.ilike(like_term),
                Employee.department.ilike(like_term),
                Employee.position.ilike(like_term),
            )
        )
    items = query.order_by(Employee.id.desc()).all()
    return jsonify({"items": [serialize_employee(item) for item in items]})


@people_bp.post("/employees")
@jwt_required()
@permission_required("employees.manage")
def create_employee():
    payload = EmployeeCreateSchema().load(request.get_json() or {})
    employee = Employee()
    apply_employee_payload(employee, payload)
    validate_employee_uniqueness(employee)
    db.session.add(employee)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        abort(409, description="Không thể tạo hồ sơ nhân sự với dữ liệu hiện tại.")
    return jsonify({"item": serialize_employee(employee)}), 201


@people_bp.get("/employees/<int:employee_id>")
@jwt_required()
@permission_required("employees.view")
def get_employee(employee_id):
    employee = db.get_or_404(Employee, employee_id)
    return jsonify({"item": serialize_employee(employee)})


@people_bp.put("/employees/<int:employee_id>")
@jwt_required()
@permission_required("employees.manage")
def update_employee(employee_id):
    employee = db.get_or_404(Employee, employee_id)
    payload = EmployeeUpdateSchema().load(request.get_json() or {})
    apply_employee_payload(employee, payload)
    validate_employee_uniqueness(employee)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        abort(409, description="Không thể cập nhật hồ sơ nhân sự với dữ liệu hiện tại.")
    return jsonify({"item": serialize_employee(employee)})


@people_bp.delete("/employees/<int:employee_id>")
@jwt_required()
@permission_required("employees.manage")
def delete_employee(employee_id):
    employee = db.get_or_404(Employee, employee_id)
    db.session.delete(employee)
    db.session.commit()
    return jsonify({"message": "Xóa hồ sơ nhân sự thành công."})
