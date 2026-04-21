from flask import request

from .extensions import db
from .models import AuditLog


def log_audit_event(
    action,
    entity_type,
    description,
    *,
    actor_user_id=None,
    target_user_id=None,
    entity_id=None,
    entity_label=None,
    commit=False,
):
    audit_log = AuditLog(
        actor_user_id=actor_user_id,
        target_user_id=target_user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        entity_label=entity_label,
        description=description,
        ip_address=request.headers.get("X-Forwarded-For", request.remote_addr),
    )
    db.session.add(audit_log)
    if commit:
        db.session.commit()
    return audit_log
