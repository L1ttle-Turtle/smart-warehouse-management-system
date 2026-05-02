from __future__ import annotations

from flask import Blueprint, abort, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy import or_
from sqlalchemy.orm import joinedload

from ..audit import log_audit_event
from ..extensions import db
from ..models import InternalTask, Notification, Role, User
from ..permissions import get_current_user, permission_required
from ..schemas import NotificationBroadcastSchema, TaskCreateSchema, TaskStatusSchema
from ..serializers import serialize_notification, serialize_task, serialize_user_summary
from ..utils import generate_code, utc_now

communications_bp = Blueprint("communications", __name__)

TASK_STATUS_VALUES = {"todo", "in_progress", "done", "cancelled"}
TASK_PRIORITY_VALUES = {"low", "medium", "high"}
NOTIFICATION_TYPE_VALUES = {"system", "task", "inventory", "shipment", "payment"}


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


def get_pagination_params():
    page = parse_positive_int_arg("page", 1)
    page_size = parse_positive_int_arg("page_size", 10)
    return page, page_size


def build_pagination_payload(pagination, serializer):
    return {
        "items": [serializer(item) for item in pagination.items],
        "total": pagination.total,
        "page": pagination.page,
        "page_size": pagination.per_page,
    }


def get_active_user_or_abort(user_id):
    user = db.session.get(User, user_id)
    if not user:
        abort(400, description="Người dùng không hợp lệ.")
    if user.status != "active":
        abort(400, description="Người dùng đang ngừng hoạt động.")
    return user


def create_notification(sender_id, receiver_id, title, content, notification_type="system"):
    notification = Notification(
        sender_id=sender_id,
        receiver_id=receiver_id,
        title=title,
        content=content,
        type=notification_type,
    )
    db.session.add(notification)
    return notification


def collect_broadcast_receiver_ids(receiver_ids, role_names):
    normalized_ids = set(receiver_ids or [])
    normalized_role_names = {role_name.strip() for role_name in (role_names or []) if role_name.strip()}

    if normalized_role_names:
        role_users = (
            User.query.join(Role)
            .filter(Role.role_name.in_(normalized_role_names), User.status == "active")
            .all()
        )
        normalized_ids.update(user.id for user in role_users)

    if not normalized_ids:
        abort(400, description="Vui lòng chọn ít nhất một người nhận hoặc vai trò nhận thông báo.")

    users = User.query.filter(User.id.in_(normalized_ids), User.status == "active").all()
    found_ids = {user.id for user in users}
    if found_ids != normalized_ids:
        abort(400, description="Danh sách người nhận có user không hợp lệ hoặc đang bị khóa.")
    return sorted(found_ids)


def audit_task_change(action, actor_user_id, task):
    log_audit_event(
        action,
        "task",
        f"{action.split('.')[1].capitalize()} công việc {task.task_code}.",
        actor_user_id=actor_user_id,
        target_user_id=task.assigned_to_id,
        entity_id=task.id,
        entity_label=task.task_code,
    )


@communications_bp.get("/notifications")
@jwt_required()
@permission_required("notifications.view")
def list_notifications():
    current_user = get_current_user()
    query = Notification.query.filter(Notification.receiver_id == current_user.id).options(
        joinedload(Notification.sender),
        joinedload(Notification.receiver),
    )

    is_read = normalize_optional_text(request.args.get("is_read"))
    if is_read:
        if is_read not in {"true", "false"}:
            abort(400, description="is_read phải là true hoặc false.")
        query = query.filter(Notification.is_read.is_(is_read == "true"))

    notification_type = normalize_optional_text(request.args.get("type"))
    if notification_type:
        if notification_type not in NOTIFICATION_TYPE_VALUES:
            abort(400, description="type không hợp lệ.")
        query = query.filter(Notification.type == notification_type)

    page, page_size = get_pagination_params()
    pagination = query.order_by(Notification.created_at.desc(), Notification.id.desc()).paginate(
        page=page,
        per_page=page_size,
        error_out=False,
    )
    return jsonify(build_pagination_payload(pagination, serialize_notification))


@communications_bp.post("/notifications/broadcast")
@jwt_required()
@permission_required("notifications.manage")
def broadcast_notifications():
    current_user = get_current_user()
    payload = NotificationBroadcastSchema().load(request.get_json() or {})
    receiver_ids = collect_broadcast_receiver_ids(
        payload.get("receiver_ids", []),
        payload.get("role_names", []),
    )

    notifications = [
        create_notification(
            current_user.id,
            receiver_id,
            payload["title"].strip(),
            payload["content"].strip(),
            payload.get("type") or "system",
        )
        for receiver_id in receiver_ids
    ]
    db.session.commit()
    return jsonify({"items": [serialize_notification(item) for item in notifications]}), 201


@communications_bp.patch("/notifications/<int:notification_id>/read")
@jwt_required()
@permission_required("notifications.view")
def mark_notification_read(notification_id):
    current_user = get_current_user()
    notification = db.session.get(Notification, notification_id)
    if not notification:
        abort(404, description="Không tìm thấy thông báo.")
    if notification.receiver_id != current_user.id:
        abort(403, description="Bạn chỉ có thể đánh dấu thông báo của chính mình.")

    notification.is_read = True
    notification.read_at = utc_now()
    db.session.commit()
    return jsonify({"item": serialize_notification(notification)})


@communications_bp.get("/tasks/meta")
@jwt_required()
@permission_required("tasks.view")
def tasks_meta():
    users = User.query.filter_by(status="active").order_by(User.full_name.asc()).all()
    return jsonify({"users": [serialize_user_summary(user) for user in users]})


@communications_bp.get("/tasks")
@jwt_required()
@permission_required("tasks.view")
def list_tasks():
    current_user = get_current_user()
    query = InternalTask.query.join(InternalTask.assignee).options(
        joinedload(InternalTask.assignee).joinedload(User.role),
        joinedload(InternalTask.creator),
    )

    if "tasks.manage" not in current_user.permission_names:
        query = query.filter(InternalTask.assigned_to_id == current_user.id)

    search = normalize_optional_text(request.args.get("q")) or normalize_optional_text(
        request.args.get("search")
    )
    if search:
        like_term = f"%{search}%"
        query = query.filter(
            or_(
                InternalTask.task_code.ilike(like_term),
                InternalTask.title.ilike(like_term),
                InternalTask.description.ilike(like_term),
                User.full_name.ilike(like_term),
            )
        )

    status = normalize_optional_text(request.args.get("status"))
    if status:
        if status not in TASK_STATUS_VALUES:
            abort(400, description="status không hợp lệ.")
        query = query.filter(InternalTask.status == status)

    priority = normalize_optional_text(request.args.get("priority"))
    if priority:
        if priority not in TASK_PRIORITY_VALUES:
            abort(400, description="priority không hợp lệ.")
        query = query.filter(InternalTask.priority == priority)

    assigned_to_id = parse_optional_int_arg("assigned_to_id")
    if assigned_to_id is not None:
        get_active_user_or_abort(assigned_to_id)
        if "tasks.manage" not in current_user.permission_names and assigned_to_id != current_user.id:
            abort(403, description="Bạn chỉ có thể lọc công việc được giao cho chính mình.")
        query = query.filter(InternalTask.assigned_to_id == assigned_to_id)

    page, page_size = get_pagination_params()
    pagination = query.order_by(InternalTask.created_at.desc(), InternalTask.id.desc()).paginate(
        page=page,
        per_page=page_size,
        error_out=False,
    )
    return jsonify(build_pagination_payload(pagination, serialize_task))


@communications_bp.post("/tasks")
@jwt_required()
@permission_required("tasks.manage")
def create_task():
    current_user = get_current_user()
    payload = TaskCreateSchema().load(request.get_json() or {})
    assignee = get_active_user_or_abort(payload["assigned_to_id"])

    task = InternalTask(
        task_code=generate_code("TSK"),
        title=payload["title"].strip(),
        description=normalize_optional_text(payload.get("description")),
        assigned_to_id=assignee.id,
        created_by=current_user.id,
        status="todo",
        priority=payload.get("priority") or "medium",
        due_at=payload.get("due_at"),
    )
    db.session.add(task)
    db.session.flush()

    create_notification(
        current_user.id,
        assignee.id,
        f"Công việc mới {task.task_code}",
        task.title,
        "task",
    )
    audit_task_change("tasks.created", current_user.id, task)
    db.session.commit()
    return jsonify({"item": serialize_task(task)}), 201


@communications_bp.patch("/tasks/<int:task_id>/status")
@jwt_required()
@permission_required("tasks.view")
def update_task_status(task_id):
    current_user = get_current_user()
    payload = TaskStatusSchema().load(request.get_json() or {})
    task = db.session.get(InternalTask, task_id)
    if not task:
        abort(404, description="Không tìm thấy công việc.")

    can_manage = "tasks.manage" in current_user.permission_names
    if not can_manage and task.assigned_to_id != current_user.id:
        abort(403, description="Bạn chỉ có thể cập nhật công việc được giao cho chính mình.")

    task.status = payload["status"]
    if task.status == "done":
        task.completed_at = utc_now()
        task.cancelled_at = None
    elif task.status == "cancelled":
        task.cancelled_at = utc_now()
        task.completed_at = None
    else:
        task.completed_at = None
        task.cancelled_at = None

    audit_task_change("tasks.updated", current_user.id, task)
    db.session.commit()
    return jsonify({"item": serialize_task(task)})
