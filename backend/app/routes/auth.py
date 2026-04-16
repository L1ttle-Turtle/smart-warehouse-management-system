from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, jwt_required

from ..extensions import db
from ..models import User
from ..permissions import get_current_user
from ..schemas import LoginSchema, ProfileUpdateSchema
from ..serializers import serialize_user

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.post("/login")
def login():
    payload = LoginSchema().load(request.get_json() or {})
    user = User.query.filter_by(username=payload["username"]).first()
    if not user or not user.check_password(payload["password"]):
        return jsonify({"message": "Invalid username or password."}), 401
    if user.status != "active":
        return jsonify({"message": "User account is inactive."}), 403

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

    next_email = payload.get("email")
    if next_email is not None:
        next_email = next_email.strip().lower()
        if not next_email:
            return jsonify({"message": "Email không được để trống."}), 400
        existing_user = User.query.filter(User.email == next_email, User.id != current_user.id).first()
        if existing_user:
            return jsonify({"message": "Email này đã được sử dụng bởi tài khoản khác."}), 409
        current_user.email = next_email

    if "phone" in payload:
        next_phone = payload.get("phone")
        current_user.phone = next_phone.strip() if isinstance(next_phone, str) and next_phone.strip() else None

    new_password = payload.get("new_password")
    if new_password:
        current_password = payload.get("current_password")
        if not current_password:
            return jsonify({"message": "Vui lòng nhập mật khẩu hiện tại để đổi mật khẩu."}), 400
        if not current_user.check_password(current_password):
            return jsonify({"message": "Mật khẩu hiện tại không chính xác."}), 400
        current_user.set_password(new_password)

    db.session.commit()
    return jsonify({"user": serialize_user(current_user)})


@auth_bp.post("/logout")
@jwt_required()
def logout():
    return jsonify({"message": "Logged out successfully."})
