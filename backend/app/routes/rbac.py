from flask import Blueprint, abort, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy import or_

from ..constants import ROLE_DELEGATION_ALLOWED_TARGETS
from ..extensions import db
from ..models import Permission, Role, User, UserPermissionDelegation
from ..permissions import get_current_user, permission_required
from ..schemas import UserDelegationSchema
from ..serializers import serialize_role, serialize_user_delegation, serialize_user_summary

rbac_bp = Blueprint("rbac", __name__)


def get_manageable_role_names(current_user):
    if not current_user.role:
        return []
    return ROLE_DELEGATION_ALLOWED_TARGETS.get(current_user.role.role_name, [])


def ensure_manageable_target_user(current_user, target_user):
    allowed_role_names = get_manageable_role_names(current_user)
    target_role_name = target_user.role.role_name if target_user.role else None
    if target_role_name not in allowed_role_names:
        abort(403, description="Bạn chỉ được ủy quyền cho user thuộc vai trò cấp dưới được phép quản lý.")
    if target_user.status != "active":
        abort(400, description="Chỉ có thể ủy quyền cho user đang hoạt động.")


def ensure_permission_can_be_delegated_to_target(target_user, permission):
    if (
        permission.permission_name == "delegations.manage"
        and not get_manageable_role_names(target_user)
    ):
        abort(400, description="User thuộc vai trò cấp thấp không thể nhận quyền ủy quyền tiếp cho account khác.")


@rbac_bp.get("/roles")
@jwt_required()
@permission_required("roles.view")
def list_roles():
    roles = Role.query.order_by(Role.role_name.asc()).all()
    return jsonify({"items": [serialize_role(role) for role in roles]})


@rbac_bp.get("/delegations")
@jwt_required()
@permission_required("delegations.manage")
def list_delegations():
    current_user = get_current_user()
    target_user_id = request.args.get("target_user_id", type=int)
    if not target_user_id:
        return jsonify({"items": []})

    target_user = db.get_or_404(User, target_user_id)
    ensure_manageable_target_user(current_user, target_user)

    items = (
        UserPermissionDelegation.query.filter_by(target_user_id=target_user.id)
        .order_by(UserPermissionDelegation.created_at.desc())
        .all()
    )
    return jsonify({"items": [serialize_user_delegation(item) for item in items]})


@rbac_bp.get("/delegations/users")
@jwt_required()
@permission_required("delegations.manage")
def list_delegation_users():
    current_user = get_current_user()
    manageable_role_names = get_manageable_role_names(current_user)
    if not manageable_role_names:
        return jsonify({"items": [], "total": 0, "page": 1, "page_size": 10})

    target_roles = (
        Role.query.filter(Role.role_name.in_(manageable_role_names))
        .order_by(Role.role_name.asc())
        .all()
    )
    manageable_role_ids = [role.id for role in target_roles]

    role_id = request.args.get("role_id", type=int)
    page = request.args.get("page", default=1, type=int)
    page_size = request.args.get("page_size", default=10, type=int)
    search = (request.args.get("search") or "").strip()

    if role_id and role_id not in manageable_role_ids:
        abort(403, description="Bạn chỉ được xem người dùng thuộc vai trò cấp dưới được phép quản lý.")

    query = User.query.filter(User.role_id.in_(manageable_role_ids)).order_by(User.full_name.asc())
    if role_id:
        query = query.filter(User.role_id == role_id)
    if search:
        like_term = f"%{search}%"
        query = query.filter(
            or_(
                User.username.ilike(like_term),
                User.full_name.ilike(like_term),
                User.email.ilike(like_term),
            )
        )

    page = max(page, 1)
    page_size = min(max(page_size, 1), 50)
    pagination = query.paginate(page=page, per_page=page_size, error_out=False)

    return jsonify(
        {
            "items": [serialize_user_summary(item) for item in pagination.items],
            "total": pagination.total,
            "page": pagination.page,
            "page_size": pagination.per_page,
        }
    )


@rbac_bp.get("/delegations/meta")
@jwt_required()
@permission_required("delegations.manage")
def delegation_meta():
    current_user = get_current_user()
    manageable_role_names = get_manageable_role_names(current_user)
    target_roles = (
        Role.query.filter(Role.role_name.in_(manageable_role_names))
        .order_by(Role.role_name.asc())
        .all()
        if manageable_role_names
        else []
    )
    grantable_permissions = (
        Permission.query.filter(Permission.permission_name.in_(current_user.permission_names))
        .order_by(Permission.permission_name.asc())
        .all()
    )

    return jsonify(
        {
            "grantor": {
                "user_id": current_user.id,
                "full_name": current_user.full_name,
                "role_name": current_user.role.role_name if current_user.role else None,
                "permissions": current_user.permission_names,
            },
            "target_roles": [role.to_dict() for role in target_roles],
            "grantable_permissions": [permission.to_dict() for permission in grantable_permissions],
        }
    )


@rbac_bp.post("/delegations")
@jwt_required()
@permission_required("delegations.manage")
def create_delegation():
    current_user = get_current_user()
    payload = UserDelegationSchema().load(request.get_json() or {})
    target_user = db.get_or_404(User, payload["target_user_id"])
    permission = db.get_or_404(Permission, payload["permission_id"])

    ensure_manageable_target_user(current_user, target_user)
    ensure_permission_can_be_delegated_to_target(target_user, permission)
    if permission.permission_name not in current_user.permission_names:
        abort(403, description="Bạn chỉ được ủy quyền những quyền mà mình đang có.")

    exists = UserPermissionDelegation.query.filter_by(
        grantor_user_id=current_user.id,
        target_user_id=target_user.id,
        permission_id=permission.id,
    ).first()
    if exists:
        abort(409, description="Quyền này đã được bạn ủy quyền cho user đã chọn.")

    delegation = UserPermissionDelegation(
        grantor_user_id=current_user.id,
        grantor_role_id=current_user.role_id,
        target_user_id=target_user.id,
        target_role_id=target_user.role_id,
        permission_id=permission.id,
        note=payload.get("note"),
    )
    db.session.add(delegation)
    db.session.commit()
    return jsonify({"item": serialize_user_delegation(delegation)}), 201


@rbac_bp.delete("/delegations/<int:delegation_id>")
@jwt_required()
@permission_required("delegations.manage")
def delete_delegation(delegation_id):
    current_user = get_current_user()
    delegation = db.get_or_404(UserPermissionDelegation, delegation_id)
    is_admin = current_user.role and current_user.role.role_name == "admin"
    if not is_admin and delegation.grantor_user_id != current_user.id:
        abort(403, description="Bạn chỉ được thu hồi quyền do chính mình đã ủy quyền.")

    db.session.delete(delegation)
    db.session.commit()
    return jsonify({"message": "Thu hồi ủy quyền thành công."})
