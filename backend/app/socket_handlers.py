from __future__ import annotations

from flask import request
from flask_jwt_extended import decode_token
from flask_socketio import disconnect, join_room

from .extensions import socketio
from .services.communications import send_chat_message


def register_socket_handlers():
    @socketio.on("connect")
    def handle_connect(auth=None):
        auth = auth or {}
        token = auth.get("token") or request.args.get("token")
        if not token:
            disconnect()
            return
        try:
            payload = decode_token(token)
            user_id = int(payload["sub"])
        except Exception:
            disconnect()
            return
        join_room(f"user:{user_id}")

    @socketio.on("chat:send")
    def handle_chat_send(payload):
        try:
            send_chat_message(
                conversation_id=payload["conversation_id"],
                sender_id=payload["sender_id"],
                content=payload["content"],
            )
        except Exception:
            return
