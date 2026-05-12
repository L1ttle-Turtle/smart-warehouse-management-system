from __future__ import annotations

from ..extensions import db
from ..models import Inventory, Notification, Role, User
from ..serializers import get_inventory_stock_status


def _format_quantity(value):
    quantity = float(value or 0)
    return str(int(quantity)) if quantity.is_integer() else f"{quantity:g}"


def _get_inventory_alert_receivers():
    return (
        User.query.join(Role)
        .filter(User.status == "active", Role.role_name.in_(("admin", "manager")))
        .order_by(User.id.asc())
        .all()
    )


def create_low_stock_notifications(inventory: Inventory, movement):
    product = inventory.product
    warehouse = inventory.warehouse
    location = inventory.location
    if not product or not warehouse or not location:
        return []

    stock_state = get_inventory_stock_status(inventory.quantity, product.min_stock)
    if stock_state["stock_status"] == "in_stock":
        return []

    title = (
        f"Cảnh báo tồn kho {product.product_code} "
        f"@ {warehouse.warehouse_code}/{location.location_code}"
    )
    reference_label = movement.reference_type or movement.movement_type
    reference_id = movement.reference_id or movement.id or "mới"
    content = (
        f"{product.product_name} tại {warehouse.warehouse_name} / {location.location_name} "
        f"đang ở trạng thái {stock_state['stock_status_label'].lower()}: "
        f"còn {_format_quantity(inventory.quantity)}, "
        f"ngưỡng tối thiểu {_format_quantity(product.min_stock)}. "
        f"Phát sinh từ {reference_label} #{reference_id}."
    )

    notifications = []
    for receiver in _get_inventory_alert_receivers():
        existing_unread_alert = Notification.query.filter_by(
            receiver_id=receiver.id,
            title=title,
            type="inventory",
            is_read=False,
        ).first()
        if existing_unread_alert:
            continue

        notification = Notification(
            sender_id=movement.performed_by,
            receiver_id=receiver.id,
            title=title,
            content=content,
            type="inventory",
        )
        db.session.add(notification)
        notifications.append(notification)

    return notifications
