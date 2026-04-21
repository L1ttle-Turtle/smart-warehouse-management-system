from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, jwt_required

from ..audit import log_audit_event
from ..extensions import db
from ..models import User
from ..permissions import get_current_user
from ..schemas import LoginSchema, ProfileUpdateSchema
from ..serializers import serialize_user
from ..utils import utc_now

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.post("/login")
def login():
    payload = LoginSchema().load(request.get_json() or {})
    user = User.query.filter_by(username=payload["username"]).first()
    if not user or not user.check_password(payload["password"]):
        log_audit_event(
            "auth.login_failed",
            "user",
            f"Đăng nhập thất bại cho username {payload['username']}.",
            actor_user_id=user.id if user else None,
            entity_label=payload["username"],
            commit=True,
        )
        return jsonify({"message": "Sai tên đăng nhập hoặc mật khẩu."}), 401

    if user.status != "active":
        log_audit_event(
            "auth.login_blocked",
            "user",
            f"Tài khoản {user.username} bị từ chối đăng nhập do đang ngừng hoạt động.",
            actor_user_id=user.id,
            target_user_id=user.id,
            entity_id=user.id,
            entity_label=user.username,
            commit=True,
        )
        return jsonify({"message": "Tài khoản đang bị khóa hoặc ngừng hoạt động."}), 403

    user.last_login_at = utc_now()
    log_audit_event(
        "auth.login_success",
        "user",
        f"Đăng nhập thành công cho tài khoản {user.username}.",
        actor_user_id=user.id,
        target_user_id=user.id,
        entity_id=user.id,
        entity_label=user.username,
    )
    db.session.commit()

    token = create_access_token(identity=str(user.id))
    return jsonify({"access_token": token, "user": serialize_user(user)})


@auth_bp.get("/me")
@jwt_required()
def me():
    return jsonify({"user": serialize_user(get_current_user())})


@auth_bp.patch("/profile")
@jwt_required()
def update_profile():
    current_user = get_current_user()
    payload = ProfileUpdateSchema().load(request.get_json() or {})
    updated_parts = []

    next_email = payload.get("email")
    if next_email is not None:
        next_email = next_email.strip().lower()
        if not next_email:
            return jsonify({"message": "Email không được để trống."}), 400
        existing_user = User.query.filter(User.email == next_email, User.id != current_user.id).first()
        if existing_user:
            return jsonify({"message": "Email này đã được sử dụng bởi tài khoản khác."}), 409
        if current_user.email != next_email:
            current_user.email = next_email
            updated_parts.append("email")

    if "phone" in payload:
        next_phone = payload.get("phone")
        normalized_phone = next_phone.strip() if isinstance(next_phone, str) and next_phone.strip() else None
        if current_user.phone != normalized_phone:
            current_user.phone = normalized_phone
            updated_parts.append("số điện thoại")

    new_password = payload.get("new_password")
    if new_password:
        current_password = payload.get("current_password")
        if not current_password:
            return jsonify({"message": "Vui lòng nhập mật khẩu hiện tại để đổi mật khẩu."}), 400
        if not current_user.check_password(current_password):
            return jsonify({"message": "Mật khẩu hiện tại không chính xác."}), 400
        current_user.set_password(new_password)
        current_user.must_change_password = False
        updated_parts.append("mật khẩu")

    if not updated_parts:
        return jsonify({"user": serialize_user(current_user)})

    log_audit_event(
        "auth.profile_updated",
        "user",
        f"Cập nhật hồ sơ cá nhân: {', '.join(updated_parts)}.",
        actor_user_id=current_user.id,
        target_user_id=current_user.id,
        entity_id=current_user.id,
        entity_label=current_user.username,
    )
    db.session.commit()
    return jsonify({"user": serialize_user(current_user)})


@auth_bp.post("/logout")
@jwt_required()
def logout():
    current_user = get_current_user()
    log_audit_event(
        "auth.logout",
        "user",
        f"Tài khoản {current_user.username} đã đăng xuất.",
        actor_user_id=current_user.id,
        target_user_id=current_user.id,
        entity_id=current_user.id,
        entity_label=current_user.username,
        commit=True,
    )
    return jsonify({"message": "Đăng xuất thành công."})
