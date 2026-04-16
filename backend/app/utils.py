from __future__ import annotations

import random
from datetime import UTC, date, datetime
from decimal import Decimal


def serialize_value(value):
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def model_to_dict(model, exclude=None):
    exclude = set(exclude or [])
    data = {}
    for column in model.__table__.columns:
        if column.name in exclude:
            continue
        data[column.name] = serialize_value(getattr(model, column.name))
    return data


def generate_code(prefix: str) -> str:
    timestamp = utc_now().strftime("%Y%m%d%H%M%S")
    suffix = random.randint(100, 999)
    return f"{prefix}-{timestamp}-{suffix}"


def parse_iso_datetime(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)


def utc_now():
    return datetime.now(UTC).replace(tzinfo=None)
