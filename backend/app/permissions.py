from functools import wraps

from flask import abort, g
from flask_jwt_extended import get_jwt_identity

from .extensions import db
from .models import User


def get_current_user():
    identity = get_jwt_identity()
    if identity is None:
        abort(401, description="Authentication required.")

    cached_user = getattr(g, "current_user", None)
    if cached_user is not None and str(cached_user.id) == str(identity):
        return cached_user

    user = db.session.get(User, int(identity))
    if not user or user.status != "active":
        abort(401, description="User is inactive or not found.")

    g.current_user = user
    return user


def permission_required(*permissions, any_of=False):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = get_current_user()
            granted = set(user.permission_names)
            if not permissions:
                return fn(*args, **kwargs)

            has_access = (
                bool(granted.intersection(permissions))
                if any_of
                else set(permissions).issubset(granted)
            )
            if not has_access:
                abort(403, description="You do not have permission to perform this action.")
            return fn(*args, **kwargs)

        return wrapper

    return decorator
