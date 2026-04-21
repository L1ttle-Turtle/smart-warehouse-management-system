from datetime import timedelta

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy import or_

from ..models import AuditLog, Employee, User, UserPermissionDelegation
from ..permissions import get_current_user, permission_required
from ..serializers import serialize_audit_log
from ..utils import utc_now

insights_bp = Blueprint("insights", __name__)


AUDIT_SORT_FIELDS = {
    "created_at": AuditLog.created_at,
    "action": AuditLog.action,
    "entity_type": AuditLog.entity_type,
}


def normalize_optional_text(value):
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def build_paginated_response(pagination):
    return {
        "items": [serialize_audit_log(item) for item in pagination.items],
        "total": pagination.total,
        "page": pagination.page,
        "page_size": pagination.per_page,
    }


@insights_bp.get("/dashboard/identity")
@jwt_required()
@permission_required("dashboard.view")
def identity_dashboard():
    current_user = get_current_user()
    now = utc_now()
    expiring_threshold = now + timedelta(days=7)

    active_received = [item for item in current_user.delegations_received if item.is_active]
    active_granted = [item for item in current_user.delegations_granted if item.is_active]
    expiring_received = [
        item for item in active_received if item.expires_at and item.expires_at <= expiring_threshold
    ]

    personal_logs = (
        AuditLog.query.filter(
            or_(
                AuditLog.actor_user_id == current_user.id,
                AuditLog.target_user_id == current_user.id,
            )
        )
        .order_by(AuditLog.created_at.desc())
        .limit(8)
        .all()
    )

    payload = {
        "profile": {
            "id": current_user.id,
            "username": current_user.username,
            "full_name": current_user.full_name,
            "role": current_user.role.role_name if current_user.role else None,
            "email": current_user.email,
            "phone": current_user.phone,
            "status": current_user.status,
            "last_login_at": current_user.last_login_at.isoformat() if current_user.last_login_at else None,
            "must_change_password": current_user.must_change_password,
        },
        "employee": {
            "employee_code": current_user.employee.employee_code if current_user.employee else None,
            "department": current_user.employee.department if current_user.employee else None,
            "position": current_user.employee.position if current_user.employee else None,
            "status": current_user.employee.status if current_user.employee else None,
        },
        "permission_summary": {
            "total_permissions": len(current_user.permission_names),
            "delegated_permissions": len(active_received),
            "role_permissions": max(len(current_user.permission_names) - len(active_received), 0),
        },
        "delegation_summary": {
            "active_received": len(active_received),
            "active_granted": len(active_granted),
            "expiring_soon": len(expiring_received),
        },
        "recent_activity": [serialize_audit_log(item) for item in personal_logs],
    }

    if "users.view" in current_user.permission_names or "employees.view" in current_user.permission_names:
        payload["management_summary"] = {
            "total_users": User.query.count(),
            "active_users": User.query.filter_by(status="active").count(),
            "must_change_password_users": User.query.filter_by(must_change_password=True).count(),
            "total_employees": Employee.query.count(),
            "active_employees": Employee.query.filter_by(status="active").count(),
            "active_delegations": UserPermissionDelegation.query.filter(
                UserPermissionDelegation.revoked_at.is_(None),
                or_(
                    UserPermissionDelegation.expires_at.is_(None),
                    UserPermissionDelegation.expires_at >= now,
                ),
            ).count(),
        }

    if "audit_logs.view" in current_user.permission_names:
        payload["audit_summary"] = {
            "total_logs": AuditLog.query.count(),
            "today_logins": AuditLog.query.filter(
                AuditLog.action == "auth.login_success",
                AuditLog.created_at >= now.replace(hour=0, minute=0, second=0, microsecond=0),
            ).count(),
        }

    return jsonify(payload)


@insights_bp.get("/audit-logs")
@jwt_required()
@permission_required("audit_logs.view")
def list_audit_logs():
    query = AuditLog.query
    search = normalize_optional_text(request.args.get("search"))
    action = normalize_optional_text(request.args.get("action"))
    entity_type = normalize_optional_text(request.args.get("entity_type"))
    actor_user_id = request.args.get("actor_user_id", type=int)
    target_user_id = request.args.get("target_user_id", type=int)
    page = max(request.args.get("page", default=1, type=int), 1)
    page_size = min(max(request.args.get("page_size", default=10, type=int), 1), 100)
    sort_by = normalize_optional_text(request.args.get("sort_by")) or "created_at"
    sort_order = (request.args.get("sort_order") or "desc").strip().lower()

    if search:
        like_term = f"%{search}%"
        query = query.filter(
            or_(
                AuditLog.entity_label.ilike(like_term),
                AuditLog.description.ilike(like_term),
                AuditLog.action.ilike(like_term),
            )
        )
    if action:
        query = query.filter(AuditLog.action == action)
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
    if actor_user_id:
        query = query.filter(AuditLog.actor_user_id == actor_user_id)
    if target_user_id:
        query = query.filter(AuditLog.target_user_id == target_user_id)

    sort_column = AUDIT_SORT_FIELDS.get(sort_by, AuditLog.created_at)
    if sort_order == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    pagination = query.paginate(page=page, per_page=page_size, error_out=False)
    return jsonify(build_paginated_response(pagination))
