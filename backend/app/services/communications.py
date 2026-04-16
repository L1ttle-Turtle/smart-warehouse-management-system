from __future__ import annotations

from sqlalchemy import func

from ..extensions import db, socketio
from ..models import (
    Conversation,
    ConversationParticipant,
    Message,
    Notification,
    Role,
    User,
)
from ..serializers import serialize_message, serialize_notification
from ..utils import utc_now


def emit_to_user(user_id, event_name, payload):
    socketio.emit(event_name, payload, room=f"user:{user_id}")


def create_notification(sender_id, receiver_id, title, content, type="system"):
    notification = Notification(
        sender_id=sender_id,
        receiver_id=receiver_id,
        title=title,
        content=content,
        type=type,
    )
    db.session.add(notification)
    db.session.flush()
    emit_to_user(receiver_id, "notification:push", serialize_notification(notification))
    return notification


def notify_roles(sender_id, role_names, title, content, type="system"):
    if not role_names:
        return []
    users = (
        User.query.join(Role)
        .filter(Role.role_name.in_(role_names), User.status == "active")
        .all()
    )
    notifications = []
    for user in users:
        notifications.append(create_notification(sender_id, user.id, title, content, type))
    return notifications


def notify_users(sender_id, user_ids, title, content, type="system"):
    notifications = []
    for user_id in sorted(set(user_ids)):
        notifications.append(create_notification(sender_id, user_id, title, content, type))
    return notifications


def get_or_create_direct_conversation(user_a_id, user_b_id):
    candidate_ids = (
        db.session.query(ConversationParticipant.conversation_id)
        .filter(ConversationParticipant.user_id.in_([user_a_id, user_b_id]))
        .group_by(ConversationParticipant.conversation_id)
        .having(func.count(ConversationParticipant.id) == 2)
        .subquery()
    )
    conversation = (
        Conversation.query.filter(
            Conversation.id.in_(candidate_ids),
            Conversation.is_direct.is_(True),
        )
        .first()
    )
    if conversation:
        return conversation

    conversation = Conversation(is_direct=True)
    db.session.add(conversation)
    db.session.flush()
    db.session.add_all(
        [
            ConversationParticipant(conversation_id=conversation.id, user_id=user_a_id),
            ConversationParticipant(conversation_id=conversation.id, user_id=user_b_id),
        ]
    )
    return conversation


def send_chat_message(conversation_id, sender_id, content):
    conversation = db.get_or_404(Conversation, conversation_id)
    participant_ids = [participant.user_id for participant in conversation.participants]
    if sender_id not in participant_ids:
        raise ValueError("You are not a participant in this conversation.")

    message = Message(
        conversation_id=conversation_id,
        sender_id=sender_id,
        content=content,
    )
    db.session.add(message)
    db.session.flush()

    for participant in conversation.participants:
        if participant.user_id == sender_id:
            participant.last_read_at = utc_now()
    payload = serialize_message(message)
    payload["conversation_id"] = conversation_id
    for participant_id in participant_ids:
        emit_to_user(participant_id, "chat:receive", payload)
    return message
