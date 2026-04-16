from __future__ import annotations

from flask import Blueprint, abort, jsonify, request
from flask_jwt_extended import jwt_required

from ..extensions import db
from ..models import Conversation, ConversationParticipant, Notification
from ..permissions import get_current_user, permission_required
from ..schemas import DirectConversationSchema, MessageSchema, NotificationSchema
from ..serializers import serialize_conversation, serialize_message, serialize_notification
from ..services.communications import (
    get_or_create_direct_conversation,
    notify_roles,
    notify_users,
    send_chat_message,
)

communications_bp = Blueprint("communications", __name__)


@communications_bp.get("/notifications")
@jwt_required()
@permission_required("notifications.view")
def list_notifications():
    user = get_current_user()
    items = (
        Notification.query.filter_by(receiver_id=user.id)
        .order_by(Notification.created_at.desc())
        .all()
    )
    return jsonify({"items": [serialize_notification(item) for item in items]})


@communications_bp.post("/notifications/broadcast")
@jwt_required()
@permission_required("notifications.manage")
def broadcast_notifications():
    payload = NotificationSchema().load(request.get_json() or {})
    if not payload["receiver_ids"] and not payload["role_names"]:
        abort(400, description="Please select receivers or role names.")
    sender = get_current_user()
    notify_users(
        sender.id,
        payload["receiver_ids"],
        payload["title"],
        payload["content"],
        payload["type"],
    )
    notify_roles(
        sender.id,
        payload["role_names"],
        payload["title"],
        payload["content"],
        payload["type"],
    )
    db.session.commit()
    return jsonify({"message": "Notifications sent successfully."})


@communications_bp.patch("/notifications/<int:notification_id>/read")
@jwt_required()
@permission_required("notifications.view")
def mark_notification_read(notification_id):
    user = get_current_user()
    notification = db.get_or_404(Notification, notification_id)
    if notification.receiver_id != user.id:
        abort(403, description="You can only update your own notifications.")
    notification.is_read = True
    db.session.commit()
    return jsonify({"item": serialize_notification(notification)})


@communications_bp.get("/chat/conversations")
@jwt_required()
@permission_required("chat.view")
def list_conversations():
    user = get_current_user()
    items = (
        Conversation.query.join(ConversationParticipant)
        .filter(ConversationParticipant.user_id == user.id)
        .order_by(Conversation.created_at.desc())
        .all()
    )
    return jsonify({"items": [serialize_conversation(item, user.id) for item in items]})


@communications_bp.post("/chat/conversations/direct")
@jwt_required()
@permission_required("chat.use")
def create_direct_conversation():
    payload = DirectConversationSchema().load(request.get_json() or {})
    user = get_current_user()
    if payload["user_id"] == user.id:
        abort(400, description="You cannot create a direct conversation with yourself.")
    conversation = get_or_create_direct_conversation(user.id, payload["user_id"])
    db.session.commit()
    return jsonify({"item": serialize_conversation(conversation, user.id)}), 201


@communications_bp.route("/chat/conversations/<int:conversation_id>/messages", methods=["GET", "POST"])
@jwt_required()
def conversation_messages(conversation_id):
    user = get_current_user()
    participant = ConversationParticipant.query.filter_by(
        conversation_id=conversation_id,
        user_id=user.id,
    ).first()
    if not participant:
        abort(403, description="You are not part of this conversation.")

    if request.method == "GET":
        permission_required("chat.view")(lambda: None)()
        messages = db.get_or_404(Conversation, conversation_id).messages
        return jsonify({"items": [serialize_message(message) for message in messages]})

    permission_required("chat.use")(lambda: None)()
    payload = MessageSchema().load(request.get_json() or {})
    message = send_chat_message(conversation_id, user.id, payload["content"])
    db.session.commit()
    return jsonify({"item": serialize_message(message)}), 201
