from flask import request
from flask_jwt_extended import decode_token
from flask_socketio import disconnect, join_room

from .extensions import socketio
from .models import User


def user_room(user_id):
    return f"user:{user_id}"


@socketio.on("connect")
def handle_socket_connect(auth):
    token = (auth or {}).get("token")
    if not token:
        disconnect()
        return False

    try:
        decoded_token = decode_token(token)
        user_id = int(decoded_token["sub"])
    except Exception:
        disconnect()
        return False

    user = User.query.get(user_id)
    if not user or user.status != "active":
        disconnect()
        return False

    join_room(user_room(user_id))
    request.sid_user_id = user_id
    return True
