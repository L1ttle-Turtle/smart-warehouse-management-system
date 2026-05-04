from __future__ import annotations

from flask import Blueprint, abort, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from ..extensions import db
from ..models import Conversation, ConversationParticipant, Message, User
from ..permissions import get_current_user, permission_required
from ..schemas import ChatDirectConversationSchema, ChatMessageSchema
from ..serializers import (
    serialize_chat_conversation,
    serialize_chat_message,
    serialize_user_summary,
)
from ..utils import utc_now

chat_bp = Blueprint("chat", __name__)


def conversation_query():
    return Conversation.query.options(
        joinedload(Conversation.participants).joinedload(ConversationParticipant.user).joinedload(User.role),
        joinedload(Conversation.messages).joinedload(Message.sender),
    )


def get_active_user_or_abort(user_id):
    user = db.session.get(User, user_id)
    if not user or user.status != "active":
        abort(400, description="Người dùng không hợp lệ hoặc đang bị khóa.")
    return user


def get_conversation_for_user_or_abort(conversation_id, user_id):
    conversation = conversation_query().filter(Conversation.id == conversation_id).first()
    if not conversation:
        abort(404, description="Không tìm thấy cuộc trò chuyện.")

    participant_ids = {participant.user_id for participant in conversation.participants}
    if user_id not in participant_ids:
        abort(403, description="Bạn không thuộc cuộc trò chuyện này.")
    return conversation


def find_direct_conversation(current_user_id, target_user_id):
    current_conversation_ids = select(ConversationParticipant.conversation_id).where(
        ConversationParticipant.user_id == current_user_id
    )
    return (
        conversation_query()
        .join(ConversationParticipant)
        .filter(
            Conversation.conversation_type == "direct",
            Conversation.id.in_(current_conversation_ids),
            ConversationParticipant.user_id == target_user_id,
        )
        .first()
    )


@chat_bp.get("/chat/users")
@jwt_required()
@permission_required("chat.view")
def list_chat_users():
    current_user = get_current_user()
    users = (
        User.query.filter(User.status == "active", User.id != current_user.id)
        .order_by(User.full_name.asc(), User.id.asc())
        .all()
    )
    return jsonify({"items": [serialize_user_summary(user) for user in users]})


@chat_bp.get("/chat/conversations")
@jwt_required()
@permission_required("chat.view")
def list_conversations():
    current_user = get_current_user()
    conversation_ids = select(ConversationParticipant.conversation_id).where(
        ConversationParticipant.user_id == current_user.id
    )
    conversations = (
        conversation_query()
        .filter(Conversation.id.in_(conversation_ids))
        .order_by(Conversation.updated_at.desc(), Conversation.id.desc())
        .all()
    )
    return jsonify(
        {
            "items": [
                serialize_chat_conversation(conversation, current_user.id)
                for conversation in conversations
            ]
        }
    )


@chat_bp.post("/chat/conversations/direct")
@jwt_required()
@permission_required("chat.view")
def create_direct_conversation():
    current_user = get_current_user()
    payload = ChatDirectConversationSchema().load(request.get_json() or {})
    target_user = get_active_user_or_abort(payload["user_id"])
    if target_user.id == current_user.id:
        abort(400, description="Không thể tạo cuộc trò chuyện với chính mình.")

    conversation = find_direct_conversation(current_user.id, target_user.id)
    if conversation:
        return jsonify({"item": serialize_chat_conversation(conversation, current_user.id)})

    conversation = Conversation(conversation_type="direct")
    conversation.participants = [
        ConversationParticipant(user_id=current_user.id),
        ConversationParticipant(user_id=target_user.id),
    ]
    db.session.add(conversation)
    db.session.commit()
    return jsonify({"item": serialize_chat_conversation(conversation, current_user.id)}), 201


@chat_bp.get("/chat/conversations/<int:conversation_id>/messages")
@jwt_required()
@permission_required("chat.view")
def list_messages(conversation_id):
    current_user = get_current_user()
    conversation = get_conversation_for_user_or_abort(conversation_id, current_user.id)
    return jsonify({"items": [serialize_chat_message(message) for message in conversation.messages]})


@chat_bp.post("/chat/conversations/<int:conversation_id>/messages")
@jwt_required()
@permission_required("chat.view")
def create_message(conversation_id):
    current_user = get_current_user()
    conversation = get_conversation_for_user_or_abort(conversation_id, current_user.id)
    payload = ChatMessageSchema().load(request.get_json() or {})
    content = payload["content"].strip()
    if not content:
        abort(400, description="Nội dung tin nhắn không được để trống.")

    message = Message(
        conversation_id=conversation.id,
        sender_id=current_user.id,
        content=content,
        sent_at=utc_now(),
    )
    conversation.updated_at = utc_now()
    db.session.add(message)
    db.session.commit()
    return jsonify({"item": serialize_chat_message(message)}), 201
