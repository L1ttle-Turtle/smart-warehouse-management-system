import re
import unicodedata

from flask import Blueprint, abort, current_app, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from ..audit import log_audit_event
from ..constants import ROLE_DELEGATION_ALLOWED_TARGETS
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

USER_SORT_FIELDS = {
    "id": User.id,
    "username": User.username,
    "full_name": User.full_name,
    "email": User.email,
    "status": User.status,
    "created_at": User.created_at,
    "updated_at": User.updated_at,
    "last_login_at": User.last_login_at,
}

EMPLOYEE_SORT_FIELDS = {
    "id": Employee.id,
    "employee_code": Employee.employee_code,
    "full_name": Employee.full_name,
    "department": Employee.department,
    "position": Employee.position,
    "status": Employee.status,
    "created_at": Employee.created_at,
    "updated_at": Employee.updated_at,
}


def normalize_optional_text(value):
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return value


def build_department_prefix(department):
    normalized_department = normalize_optional_text(department)
    if not normalized_department:
        return "EMP"

    ascii_text = unicodedata.normalize("NFD", normalized_department)
    ascii_text = "".join(
        character for character in ascii_text if unicodedata.category(character) != "Mn"
    )
    ascii_text = ascii_text.replace("đ", "d").replace("Đ", "D")
    words = re.findall(r"[A-Za-z0-9]+", ascii_text)
    prefix = "".join(word[0].upper() for word in words[:4])
    return prefix or "EMP"


def generate_employee_code(department):
    prefix = build_department_prefix(department)
    existing_codes = [
        code
        for (code,) in db.session.query(Employee.employee_code)
        .filter(Employee.employee_code.like(f"{prefix}-%"))
        .all()
    ]

    max_sequence = 0
    for code in existing_codes:
        matched = re.match(rf"^{re.escape(prefix)}-(\d+)$", code)
        if matched:
            max_sequence = max(max_sequence, int(matched.group(1)))

    candidate = f"{prefix}-{max_sequence + 1:03d}"
    while Employee.query.filter_by(employee_code=candidate).first():
        max_sequence += 1
        candidate = f"{prefix}-{max_sequence + 1:03d}"
    return candidate


def parse_bool_filter(value):
    if value is None or value == "":
        return None
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes"}:
        return True
    if normalized in {"0", "false", "no"}:
        return False
    abort(400, description="Giá trị bộ lọc boolean không hợp lệ.")


def build_pagination_payload(pagination, serializer):
    return {
        "items": [serializer(item) for item in pagination.items],
        "total": pagination.total,
        "page": pagination.page,
        "page_size": pagination.per_page,
    }


def apply_sort(query, sort_fields, default_field):
    sort_by = normalize_optional_text(request.args.get("sort_by")) or default_field
    sort_order = (request.args.get("sort_order") or "desc").strip().lower()
    column = sort_fields.get(sort_by, sort_fields[default_field])
    if sort_order == "asc":
        return query.order_by(column.asc())
    return query.order_by(column.desc())


def get_pagination_params():
    page = max(request.args.get("page", default=1, type=int), 1)
    page_size = min(max(request.args.get("page_size", default=10, type=int), 1), 100)
    return page, page_size


def get_manageable_role_names_for_user_management(current_user):
    role_name = current_user.role.role_name if current_user.role else None
    if role_name == "admin":
        return None
    return set(ROLE_DELEGATION_ALLOWED_TARGETS.get(role_name, []))


def ensure_assignable_role(current_user, role):
    manageable_role_names = get_manageable_role_names_for_user_management(current_user)
    if manageable_role_names is None:
        return
    if role.role_name not in manageable_role_names:
        abort(
            403,
            description="Bạn không thể gán hoặc tạo tài khoản với vai trò cao hơn quyền gốc của mình.",
        )


def ensure_manageable_user_for_management(current_user, user):
    manageable_role_names = get_manageable_role_names_for_user_management(current_user)
    if manageable_role_names is None:
        return

    target_role_name = user.role.role_name if user.role else None
    if target_role_name not in manageable_role_names:
        abort(
            403,
            description="Bạn chỉ được quản lý tài khoản thuộc vai trò cấp dưới được phép.",
        )


def apply_user_payload(user, payload, is_create=False, current_user=None):
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
        if current_user:
            ensure_assignable_role(current_user, role)
        user.role_id = role.id
    if "status" in payload and payload["status"] is not None:
        user.status = payload["status"]

    password = payload.get("password")
    if is_create and not password:
        password = current_app.config["DEFAULT_PASSWORD"]
        user.must_change_password = True
        user.set_password(password, mark_changed=False)
    elif password:
        user.must_change_password = not is_create
        user.set_password(password, mark_changed=is_create)


def validate_user_uniqueness(user):
    duplicate_username = User.query.filter(
        User.username == user.username,
        User.id != getattr(user, "id", None),
    ).first()
    if duplicate_username:
        abort(409, description="Tên đăng nhập đã tồn tại.")

    duplicate_email = User.query.filter(
        User.email == user.email,
        User.id != getattr(user, "id", None),
    ).first()
    if duplicate_email:
        abort(409, description="Email đã tồn tại.")


def apply_employee_payload(employee, payload):
    if "employee_code" in payload:
        incoming_code = normalize_optional_text(payload.get("employee_code"))
        if incoming_code is not None:
            employee.employee_code = incoming_code
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
    status = normalize_optional_text(request.args.get("status"))
    role_id = request.args.get("role_id", type=int)
    has_employee = parse_bool_filter(request.args.get("has_employee"))

    query = User.query.outerjoin(Employee)
    if search:
        like_term = f"%{search}%"
        query = query.filter(
            or_(
                User.username.ilike(like_term),
                User.full_name.ilike(like_term),
                User.email.ilike(like_term),
                Employee.employee_code.ilike(like_term),
            )
        )
    if status:
        query = query.filter(User.status == status)
    if role_id:
        query = query.filter(User.role_id == role_id)
    if has_employee is True:
        query = query.filter(Employee.id.isnot(None))
    if has_employee is False:
        query = query.filter(Employee.id.is_(None))

    query = apply_sort(query, USER_SORT_FIELDS, "created_at")
    page, page_size = get_pagination_params()
    pagination = query.paginate(page=page, per_page=page_size, error_out=False)
    return jsonify(build_pagination_payload(pagination, serialize_management_user))


@people_bp.post("/users")
@jwt_required()
@permission_required("users.manage")
def create_user():
    current_user = get_current_user()
    payload = UserCreateSchema().load(request.get_json() or {})
    user = User()
    apply_user_payload(user, payload, True, current_user=current_user)
    validate_user_uniqueness(user)
    db.session.add(user)
    try:
        db.session.flush()
        log_audit_event(
            "users.created",
            "user",
            f"Tạo tài khoản {user.username} với vai trò {user.role.role_name if user.role else user.role_id}.",
            actor_user_id=current_user.id,
            target_user_id=user.id,
            entity_id=user.id,
            entity_label=user.username,
        )
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
    current_user = get_current_user()
    user = db.get_or_404(User, user_id)
    ensure_manageable_user_for_management(current_user, user)
    payload = UserUpdateSchema().load(request.get_json() or {})
    apply_user_payload(user, payload, False, current_user=current_user)
    validate_user_uniqueness(user)
    try:
        log_audit_event(
            "users.updated",
            "user",
            f"Cập nhật tài khoản {user.username}.",
            actor_user_id=current_user.id,
            target_user_id=user.id,
            entity_id=user.id,
            entity_label=user.username,
        )
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
    ensure_manageable_user_for_management(current_user, user)
    if user.employee:
        abort(400, description="Tài khoản này đang liên kết với hồ sơ nhân sự và chưa thể xóa.")
    if user.delegations_granted or user.delegations_received:
        abort(400, description="Tài khoản này đang tham gia dữ liệu ủy quyền và chưa thể xóa.")

    username = user.username
    log_audit_event(
        "users.deleted",
        "user",
        f"Xóa tài khoản {username}.",
        actor_user_id=current_user.id,
        entity_id=user.id,
        entity_label=username,
    )
    db.session.delete(user)
    db.session.commit()
    return jsonify({"message": "Xóa tài khoản thành công."})


@people_bp.get("/employees")
@jwt_required()
@permission_required("employees.view")
def list_employees():
    search = normalize_optional_text(request.args.get("search"))
    status = normalize_optional_text(request.args.get("status"))
    has_user = parse_bool_filter(request.args.get("has_user"))

    query = Employee.query.outerjoin(User)
    if search:
        like_term = f"%{search}%"
        query = query.filter(
            or_(
                Employee.employee_code.ilike(like_term),
                Employee.full_name.ilike(like_term),
                Employee.department.ilike(like_term),
                Employee.position.ilike(like_term),
                User.username.ilike(like_term),
            )
        )
    if status:
        query = query.filter(Employee.status == status)
    if has_user is True:
        query = query.filter(Employee.user_id.isnot(None))
    if has_user is False:
        query = query.filter(Employee.user_id.is_(None))

    query = apply_sort(query, EMPLOYEE_SORT_FIELDS, "created_at")
    page, page_size = get_pagination_params()
    pagination = query.paginate(page=page, per_page=page_size, error_out=False)
    return jsonify(build_pagination_payload(pagination, serialize_employee))


@people_bp.post("/employees")
@jwt_required()
@permission_required("employees.manage")
def create_employee():
    current_user = get_current_user()
    payload = EmployeeCreateSchema().load(request.get_json() or {})
    employee = Employee()
    apply_employee_payload(employee, payload)
    if not employee.employee_code:
        employee.employee_code = generate_employee_code(employee.department)
    validate_employee_uniqueness(employee)
    db.session.add(employee)
    try:
        db.session.flush()
        log_audit_event(
            "employees.created",
            "employee",
            f"Tạo hồ sơ nhân sự {employee.full_name}.",
            actor_user_id=current_user.id,
            target_user_id=employee.user_id,
            entity_id=employee.id,
            entity_label=employee.employee_code,
        )
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
    current_user = get_current_user()
    employee = db.get_or_404(Employee, employee_id)
    payload = EmployeeUpdateSchema().load(request.get_json() or {})
    apply_employee_payload(employee, payload)
    validate_employee_uniqueness(employee)
    try:
        log_audit_event(
            "employees.updated",
            "employee",
            f"Cập nhật hồ sơ nhân sự {employee.full_name}.",
            actor_user_id=current_user.id,
            target_user_id=employee.user_id,
            entity_id=employee.id,
            entity_label=employee.employee_code,
        )
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        abort(409, description="Không thể cập nhật hồ sơ nhân sự với dữ liệu hiện tại.")
    return jsonify({"item": serialize_employee(employee)})


@people_bp.delete("/employees/<int:employee_id>")
@jwt_required()
@permission_required("employees.manage")
def delete_employee(employee_id):
    current_user = get_current_user()
    employee = db.get_or_404(Employee, employee_id)
    employee_code = employee.employee_code
    full_name = employee.full_name
    linked_user_id = employee.user_id
    log_audit_event(
        "employees.deleted",
        "employee",
        f"Xóa hồ sơ nhân sự {full_name}.",
        actor_user_id=current_user.id,
        target_user_id=linked_user_id,
        entity_id=employee.id,
        entity_label=employee_code,
    )
    db.session.delete(employee)
    db.session.commit()
    return jsonify({"message": "Xóa hồ sơ nhân sự thành công."})
