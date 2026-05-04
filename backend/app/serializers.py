from .constants import ROLE_DELEGATION_ALLOWED_TARGETS
from .models import (
    AuditLog,
    BankAccount,
    Category,
    Conversation,
    Customer,
    Employee,
    ExportReceipt,
    ExportReceiptDetail,
    Inventory,
    InventoryMovement,
    Invoice,
    InvoiceDetail,
    ImportReceipt,
    ImportReceiptDetail,
    InternalTask,
    Message,
    Payment,
    Product,
    Role,
    Shipment,
    Stocktake,
    StocktakeDetail,
    StockTransfer,
    StockTransferDetail,
    Supplier,
    User,
    UserPermissionDelegation,
    Warehouse,
    WarehouseLocation,
    Notification,
)


def serialize_user_delegation(delegation: UserPermissionDelegation):
    return {
        "id": delegation.id,
        "permission_id": delegation.permission_id,
        "permission_name": delegation.permission.permission_name if delegation.permission else None,
        "target_user_id": delegation.target_user_id,
        "target_username": delegation.target_user.username if delegation.target_user else None,
        "target_user_name": delegation.target_user.full_name if delegation.target_user else None,
        "target_role_id": delegation.target_role_id,
        "target_role_name": delegation.target_role.role_name if delegation.target_role else None,
        "grantor_user_id": delegation.grantor_user_id,
        "grantor_user_name": delegation.grantor_user.full_name if delegation.grantor_user else None,
        "grantor_role_id": delegation.grantor_role_id,
        "grantor_role_name": delegation.grantor_role.role_name if delegation.grantor_role else None,
        "note": delegation.note,
        "expires_at": delegation.expires_at.isoformat() if delegation.expires_at else None,
        "revoked_at": delegation.revoked_at.isoformat() if delegation.revoked_at else None,
        "revoked_by_user_id": delegation.revoked_by_user_id,
        "revoked_by_user_name": delegation.revoked_by_user.full_name if delegation.revoked_by_user else None,
        "revoke_reason": delegation.revoke_reason,
        "status": delegation.status,
        "created_at": delegation.created_at.isoformat() if delegation.created_at else None,
        "updated_at": delegation.updated_at.isoformat() if delegation.updated_at else None,
    }


def serialize_role(role: Role):
    data = role.to_dict()
    data["base_permissions"] = [permission.permission_name for permission in role.permissions]
    data["delegated_permissions"] = []
    data["effective_permissions"] = list(data["base_permissions"])
    data["user_count"] = len(role.users)
    return data


def serialize_user(user: User):
    data = user.to_dict(exclude={"password_hash"})
    data["role"] = user.role.role_name if user.role else None
    data["employee_id"] = user.employee.id if user.employee else None
    data["employee_code"] = user.employee.employee_code if user.employee else None
    data["permissions"] = user.permission_names
    data["must_change_password"] = user.must_change_password
    data["delegated_permission_sources"] = [
        serialize_user_delegation(delegation)
        for delegation in sorted(
            [item for item in user.delegations_received if item.is_active],
            key=lambda item: (
                item.permission.permission_name if item.permission else "",
                item.grantor_user.full_name if item.grantor_user else "",
            ),
        )
    ]
    return data


def serialize_user_summary(user: User):
    return {
        "id": user.id,
        "username": user.username,
        "full_name": user.full_name,
        "email": user.email,
        "phone": user.phone,
        "status": user.status,
        "role_id": user.role_id,
        "role_name": user.role.role_name if user.role else None,
        "employee_id": user.employee.id if user.employee else None,
        "employee_code": user.employee.employee_code if user.employee else None,
        "can_receive_delegation_manage": bool(
            user.role and ROLE_DELEGATION_ALLOWED_TARGETS.get(user.role.role_name, [])
        ),
    }


def serialize_management_user(user: User):
    return {
        "id": user.id,
        "username": user.username,
        "full_name": user.full_name,
        "email": user.email,
        "phone": user.phone,
        "status": user.status,
        "role_id": user.role_id,
        "role": user.role.role_name if user.role else None,
        "employee_id": user.employee.id if user.employee else None,
        "employee_code": user.employee.employee_code if user.employee else None,
        "must_change_password": user.must_change_password,
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
        "password_changed_at": user.password_changed_at.isoformat() if user.password_changed_at else None,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "updated_at": user.updated_at.isoformat() if user.updated_at else None,
    }


def serialize_employee(employee: Employee):
    return {
        "id": employee.id,
        "employee_code": employee.employee_code,
        "user_id": employee.user_id,
        "username": employee.user.username if employee.user else None,
        "full_name": employee.full_name,
        "department": employee.department,
        "position": employee.position,
        "phone": employee.phone,
        "email": employee.email,
        "role": employee.user.role.role_name if employee.user and employee.user.role else None,
        "status": employee.status,
        "created_at": employee.created_at.isoformat() if employee.created_at else None,
        "updated_at": employee.updated_at.isoformat() if employee.updated_at else None,
    }


def serialize_category(category: Category):
    return {
        "id": category.id,
        "category_name": category.category_name,
        "description": category.description,
        "created_at": category.created_at.isoformat() if category.created_at else None,
        "updated_at": category.updated_at.isoformat() if category.updated_at else None,
    }


def serialize_supplier(supplier: Supplier):
    return {
        "id": supplier.id,
        "supplier_code": supplier.supplier_code,
        "supplier_name": supplier.supplier_name,
        "email": supplier.email,
        "phone": supplier.phone,
        "address": supplier.address,
        "status": supplier.status,
        "created_at": supplier.created_at.isoformat() if supplier.created_at else None,
        "updated_at": supplier.updated_at.isoformat() if supplier.updated_at else None,
    }


def serialize_customer(customer: Customer):
    return {
        "id": customer.id,
        "customer_code": customer.customer_code,
        "customer_name": customer.customer_name,
        "email": customer.email,
        "phone": customer.phone,
        "address": customer.address,
        "status": customer.status,
        "created_at": customer.created_at.isoformat() if customer.created_at else None,
        "updated_at": customer.updated_at.isoformat() if customer.updated_at else None,
    }


def serialize_bank_account(bank_account: BankAccount):
    return {
        "id": bank_account.id,
        "bank_name": bank_account.bank_name,
        "account_number": bank_account.account_number,
        "account_holder": bank_account.account_holder,
        "branch": bank_account.branch,
        "status": bank_account.status,
        "created_at": bank_account.created_at.isoformat() if bank_account.created_at else None,
        "updated_at": bank_account.updated_at.isoformat() if bank_account.updated_at else None,
    }


def serialize_warehouse(warehouse: Warehouse):
    return {
        "id": warehouse.id,
        "warehouse_code": warehouse.warehouse_code,
        "warehouse_name": warehouse.warehouse_name,
        "address": warehouse.address,
        "status": warehouse.status,
        "created_at": warehouse.created_at.isoformat() if warehouse.created_at else None,
        "updated_at": warehouse.updated_at.isoformat() if warehouse.updated_at else None,
    }


def serialize_warehouse_location(location: WarehouseLocation):
    return {
        "id": location.id,
        "warehouse_id": location.warehouse_id,
        "warehouse_code": location.warehouse.warehouse_code if location.warehouse else None,
        "warehouse_name": location.warehouse.warehouse_name if location.warehouse else None,
        "location_code": location.location_code,
        "location_name": location.location_name,
        "status": location.status,
        "created_at": location.created_at.isoformat() if location.created_at else None,
        "updated_at": location.updated_at.isoformat() if location.updated_at else None,
    }


def serialize_product(product: Product):
    return {
        "id": product.id,
        "product_code": product.product_code,
        "product_name": product.product_name,
        "category_id": product.category_id,
        "category_name": product.category.category_name if product.category else None,
        "quantity_total": product.quantity_total,
        "min_stock": product.min_stock,
        "status": product.status,
        "description": product.description,
        "is_below_min_stock": product.quantity_total <= product.min_stock,
        "created_at": product.created_at.isoformat() if product.created_at else None,
        "updated_at": product.updated_at.isoformat() if product.updated_at else None,
    }


def get_inventory_stock_status(quantity, min_stock):
    quantity = float(quantity or 0)
    min_stock = float(min_stock or 0)
    shortage_quantity = max(min_stock - quantity, 0)

    if quantity <= 0:
        return {
            "stock_status": "out_of_stock",
            "stock_status_label": "Hết hàng",
            "is_low_stock": True,
            "shortage_quantity": shortage_quantity,
        }

    if quantity <= min_stock:
        return {
            "stock_status": "low_stock",
            "stock_status_label": "Tồn thấp",
            "is_low_stock": True,
            "shortage_quantity": shortage_quantity,
        }

    return {
        "stock_status": "in_stock",
        "stock_status_label": "Đủ hàng",
        "is_low_stock": False,
        "shortage_quantity": 0,
    }


def serialize_inventory_row(inventory: Inventory):
    payload = {
        "id": inventory.id,
        "warehouse_id": inventory.warehouse_id,
        "warehouse_code": inventory.warehouse.warehouse_code if inventory.warehouse else None,
        "warehouse_name": inventory.warehouse.warehouse_name if inventory.warehouse else None,
        "location_id": inventory.location_id,
        "location_code": inventory.location.location_code if inventory.location else None,
        "location_name": inventory.location.location_name if inventory.location else None,
        "product_id": inventory.product_id,
        "product_code": inventory.product.product_code if inventory.product else None,
        "product_name": inventory.product.product_name if inventory.product else None,
        "category_id": inventory.product.category_id if inventory.product else None,
        "category_name": (
            inventory.product.category.category_name
            if inventory.product and inventory.product.category
            else None
        ),
        "min_stock": inventory.product.min_stock if inventory.product else 0,
        "quantity": inventory.quantity,
        "updated_at": inventory.updated_at.isoformat() if inventory.updated_at else None,
        "created_at": inventory.created_at.isoformat() if inventory.created_at else None,
    }
    payload.update(
        get_inventory_stock_status(
            inventory.quantity,
            inventory.product.min_stock if inventory.product else 0,
        )
    )
    return payload


def serialize_inventory_movement(movement: InventoryMovement):
    return {
        "id": movement.id,
        "warehouse_id": movement.warehouse_id,
        "warehouse_code": movement.warehouse.warehouse_code if movement.warehouse else None,
        "warehouse_name": movement.warehouse.warehouse_name if movement.warehouse else None,
        "location_id": movement.location_id,
        "location_code": movement.location.location_code if movement.location else None,
        "location_name": movement.location.location_name if movement.location else None,
        "product_id": movement.product_id,
        "product_code": movement.product.product_code if movement.product else None,
        "product_name": movement.product.product_name if movement.product else None,
        "movement_type": movement.movement_type,
        "reference_type": movement.reference_type,
        "reference_id": movement.reference_id,
        "quantity_before": movement.quantity_before,
        "quantity_change": movement.quantity_change,
        "quantity_after": movement.quantity_after,
        "performed_by": movement.performed_by,
        "performer_name": movement.performer.full_name if movement.performer else None,
        "note": movement.note,
        "created_at": movement.created_at.isoformat() if movement.created_at else None,
        "updated_at": movement.updated_at.isoformat() if movement.updated_at else None,
    }


def serialize_import_receipt_detail(detail: ImportReceiptDetail):
    return {
        "id": detail.id,
        "product_id": detail.product_id,
        "product_code": detail.product.product_code if detail.product else None,
        "product_name": detail.product.product_name if detail.product else None,
        "location_id": detail.location_id,
        "location_code": detail.location.location_code if detail.location else None,
        "location_name": detail.location.location_name if detail.location else None,
        "quantity": detail.quantity,
        "created_at": detail.created_at.isoformat() if detail.created_at else None,
        "updated_at": detail.updated_at.isoformat() if detail.updated_at else None,
    }


def serialize_import_receipt(receipt: ImportReceipt):
    total_quantity = sum(detail.quantity for detail in receipt.details)
    return {
        "id": receipt.id,
        "receipt_code": receipt.receipt_code,
        "warehouse_id": receipt.warehouse_id,
        "warehouse_code": receipt.warehouse.warehouse_code if receipt.warehouse else None,
        "warehouse_name": receipt.warehouse.warehouse_name if receipt.warehouse else None,
        "supplier_id": receipt.supplier_id,
        "supplier_code": receipt.supplier.supplier_code if receipt.supplier else None,
        "supplier_name": receipt.supplier.supplier_name if receipt.supplier else None,
        "created_by": receipt.created_by,
        "created_by_name": receipt.creator.full_name if receipt.creator else None,
        "confirmed_by": receipt.confirmed_by,
        "confirmed_by_name": receipt.confirmer.full_name if receipt.confirmer else None,
        "status": receipt.status,
        "note": receipt.note,
        "detail_count": len(receipt.details),
        "total_quantity": total_quantity,
        "confirmed_at": receipt.confirmed_at.isoformat() if receipt.confirmed_at else None,
        "created_at": receipt.created_at.isoformat() if receipt.created_at else None,
        "updated_at": receipt.updated_at.isoformat() if receipt.updated_at else None,
        "details": [serialize_import_receipt_detail(detail) for detail in receipt.details],
    }


def serialize_export_receipt_detail(detail: ExportReceiptDetail):
    return {
        "id": detail.id,
        "product_id": detail.product_id,
        "product_code": detail.product.product_code if detail.product else None,
        "product_name": detail.product.product_name if detail.product else None,
        "location_id": detail.location_id,
        "location_code": detail.location.location_code if detail.location else None,
        "location_name": detail.location.location_name if detail.location else None,
        "quantity": detail.quantity,
        "created_at": detail.created_at.isoformat() if detail.created_at else None,
        "updated_at": detail.updated_at.isoformat() if detail.updated_at else None,
    }


def serialize_export_receipt(receipt: ExportReceipt):
    total_quantity = sum(detail.quantity for detail in receipt.details)
    return {
        "id": receipt.id,
        "receipt_code": receipt.receipt_code,
        "warehouse_id": receipt.warehouse_id,
        "warehouse_code": receipt.warehouse.warehouse_code if receipt.warehouse else None,
        "warehouse_name": receipt.warehouse.warehouse_name if receipt.warehouse else None,
        "customer_id": receipt.customer_id,
        "customer_code": receipt.customer.customer_code if receipt.customer else None,
        "customer_name": receipt.customer.customer_name if receipt.customer else None,
        "created_by": receipt.created_by,
        "created_by_name": receipt.creator.full_name if receipt.creator else None,
        "confirmed_by": receipt.confirmed_by,
        "confirmed_by_name": receipt.confirmer.full_name if receipt.confirmer else None,
        "status": receipt.status,
        "note": receipt.note,
        "detail_count": len(receipt.details),
        "total_quantity": total_quantity,
        "confirmed_at": receipt.confirmed_at.isoformat() if receipt.confirmed_at else None,
        "created_at": receipt.created_at.isoformat() if receipt.created_at else None,
        "updated_at": receipt.updated_at.isoformat() if receipt.updated_at else None,
        "details": [serialize_export_receipt_detail(detail) for detail in receipt.details],
    }


def serialize_shipment(shipment: Shipment):
    receipt = shipment.export_receipt
    total_quantity = sum(detail.quantity for detail in receipt.details) if receipt else 0
    return {
        "id": shipment.id,
        "shipment_code": shipment.shipment_code,
        "export_receipt_id": shipment.export_receipt_id,
        "export_receipt_code": receipt.receipt_code if receipt else None,
        "warehouse_id": receipt.warehouse_id if receipt else None,
        "warehouse_code": receipt.warehouse.warehouse_code if receipt and receipt.warehouse else None,
        "warehouse_name": receipt.warehouse.warehouse_name if receipt and receipt.warehouse else None,
        "customer_id": receipt.customer_id if receipt else None,
        "customer_code": receipt.customer.customer_code if receipt and receipt.customer else None,
        "customer_name": receipt.customer.customer_name if receipt and receipt.customer else None,
        "shipper_id": shipment.shipper_id,
        "shipper_name": shipment.shipper.full_name if shipment.shipper else None,
        "created_by": shipment.created_by,
        "created_by_name": shipment.creator.full_name if shipment.creator else None,
        "status": shipment.status,
        "note": shipment.note,
        "detail_count": len(receipt.details) if receipt else 0,
        "total_quantity": total_quantity,
        "assigned_at": shipment.assigned_at.isoformat() if shipment.assigned_at else None,
        "in_transit_at": shipment.in_transit_at.isoformat() if shipment.in_transit_at else None,
        "delivered_at": shipment.delivered_at.isoformat() if shipment.delivered_at else None,
        "cancelled_at": shipment.cancelled_at.isoformat() if shipment.cancelled_at else None,
        "created_at": shipment.created_at.isoformat() if shipment.created_at else None,
        "updated_at": shipment.updated_at.isoformat() if shipment.updated_at else None,
        "details": [serialize_export_receipt_detail(detail) for detail in receipt.details] if receipt else [],
    }


def serialize_invoice_detail(detail: InvoiceDetail):
    return {
        "id": detail.id,
        "export_receipt_detail_id": detail.export_receipt_detail_id,
        "product_id": detail.product_id,
        "product_code": detail.product.product_code if detail.product else None,
        "product_name": detail.product.product_name if detail.product else None,
        "location_id": detail.location_id,
        "location_code": detail.location.location_code if detail.location else None,
        "location_name": detail.location.location_name if detail.location else None,
        "quantity": detail.quantity,
        "unit_price": detail.unit_price,
        "line_total": detail.line_total,
        "created_at": detail.created_at.isoformat() if detail.created_at else None,
        "updated_at": detail.updated_at.isoformat() if detail.updated_at else None,
    }


def serialize_payment(payment: Payment):
    return {
        "id": payment.id,
        "payment_code": payment.payment_code,
        "invoice_id": payment.invoice_id,
        "invoice_code": payment.invoice.invoice_code if payment.invoice else None,
        "invoice_status": payment.invoice.status if payment.invoice else None,
        "bank_account_id": payment.bank_account_id,
        "bank_name": payment.bank_account.bank_name if payment.bank_account else None,
        "bank_account_number": (
            payment.bank_account.account_number if payment.bank_account else None
        ),
        "created_by": payment.created_by,
        "created_by_name": payment.creator.full_name if payment.creator else None,
        "amount": payment.amount,
        "payment_method": payment.payment_method,
        "paid_at": payment.paid_at.isoformat() if payment.paid_at else None,
        "note": payment.note,
        "created_at": payment.created_at.isoformat() if payment.created_at else None,
        "updated_at": payment.updated_at.isoformat() if payment.updated_at else None,
    }


def serialize_notification(notification: Notification):
    return {
        "id": notification.id,
        "sender_id": notification.sender_id,
        "sender_name": notification.sender.full_name if notification.sender else "System",
        "receiver_id": notification.receiver_id,
        "receiver_name": notification.receiver.full_name if notification.receiver else None,
        "title": notification.title,
        "content": notification.content,
        "type": notification.type,
        "is_read": notification.is_read,
        "read_at": notification.read_at.isoformat() if notification.read_at else None,
        "created_at": notification.created_at.isoformat() if notification.created_at else None,
        "updated_at": notification.updated_at.isoformat() if notification.updated_at else None,
    }


def serialize_task(task: InternalTask):
    return {
        "id": task.id,
        "task_code": task.task_code,
        "title": task.title,
        "description": task.description,
        "assigned_to_id": task.assigned_to_id,
        "assigned_to_name": task.assignee.full_name if task.assignee else None,
        "assigned_to_role": task.assignee.role.role_name if task.assignee and task.assignee.role else None,
        "created_by": task.created_by,
        "created_by_name": task.creator.full_name if task.creator else None,
        "status": task.status,
        "priority": task.priority,
        "due_at": task.due_at.isoformat() if task.due_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "cancelled_at": task.cancelled_at.isoformat() if task.cancelled_at else None,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "updated_at": task.updated_at.isoformat() if task.updated_at else None,
    }


def serialize_chat_message(message: Message):
    return {
        "id": message.id,
        "conversation_id": message.conversation_id,
        "sender_id": message.sender_id,
        "sender_name": message.sender.full_name if message.sender else None,
        "content": message.content,
        "sent_at": message.sent_at.isoformat() if message.sent_at else None,
        "created_at": message.created_at.isoformat() if message.created_at else None,
        "updated_at": message.updated_at.isoformat() if message.updated_at else None,
    }


def serialize_chat_conversation(conversation: Conversation, current_user_id: int):
    peer = None
    for participant in conversation.participants:
        if participant.user_id != current_user_id:
            peer = participant.user
            break

    last_message = conversation.messages[-1] if conversation.messages else None
    return {
        "id": conversation.id,
        "conversation_type": conversation.conversation_type,
        "participant_ids": [participant.user_id for participant in conversation.participants],
        "peer": serialize_user_summary(peer) if peer else None,
        "last_message": serialize_chat_message(last_message) if last_message else None,
        "created_at": conversation.created_at.isoformat() if conversation.created_at else None,
        "updated_at": conversation.updated_at.isoformat() if conversation.updated_at else None,
    }


def serialize_invoice(invoice: Invoice):
    total_quantity = sum(detail.quantity for detail in invoice.details)
    paid_amount = sum(float(payment.amount or 0) for payment in invoice.payments)
    remaining_amount = max(float(invoice.total_amount or 0) - paid_amount, 0)
    return {
        "id": invoice.id,
        "invoice_code": invoice.invoice_code,
        "export_receipt_id": invoice.export_receipt_id,
        "export_receipt_code": (
            invoice.export_receipt.receipt_code if invoice.export_receipt else None
        ),
        "warehouse_id": invoice.export_receipt.warehouse_id if invoice.export_receipt else None,
        "warehouse_code": (
            invoice.export_receipt.warehouse.warehouse_code
            if invoice.export_receipt and invoice.export_receipt.warehouse
            else None
        ),
        "warehouse_name": (
            invoice.export_receipt.warehouse.warehouse_name
            if invoice.export_receipt and invoice.export_receipt.warehouse
            else None
        ),
        "customer_id": invoice.customer_id,
        "customer_code": invoice.customer.customer_code if invoice.customer else None,
        "customer_name": invoice.customer.customer_name if invoice.customer else None,
        "bank_account_id": invoice.bank_account_id,
        "bank_name": invoice.bank_account.bank_name if invoice.bank_account else None,
        "bank_account_number": (
            invoice.bank_account.account_number if invoice.bank_account else None
        ),
        "bank_account_holder": (
            invoice.bank_account.account_holder if invoice.bank_account else None
        ),
        "created_by": invoice.created_by,
        "created_by_name": invoice.creator.full_name if invoice.creator else None,
        "status": invoice.status,
        "note": invoice.note,
        "detail_count": len(invoice.details),
        "total_quantity": total_quantity,
        "total_amount": invoice.total_amount,
        "paid_amount": paid_amount,
        "remaining_amount": remaining_amount,
        "issued_at": invoice.issued_at.isoformat() if invoice.issued_at else None,
        "created_at": invoice.created_at.isoformat() if invoice.created_at else None,
        "updated_at": invoice.updated_at.isoformat() if invoice.updated_at else None,
        "details": [serialize_invoice_detail(detail) for detail in invoice.details],
        "payments": [serialize_payment(payment) for payment in invoice.payments],
    }


def serialize_stock_transfer_detail(detail: StockTransferDetail):
    return {
        "id": detail.id,
        "product_id": detail.product_id,
        "product_code": detail.product.product_code if detail.product else None,
        "product_name": detail.product.product_name if detail.product else None,
        "source_location_id": detail.source_location_id,
        "source_location_code": detail.source_location.location_code if detail.source_location else None,
        "source_location_name": detail.source_location.location_name if detail.source_location else None,
        "target_location_id": detail.target_location_id,
        "target_location_code": detail.target_location.location_code if detail.target_location else None,
        "target_location_name": detail.target_location.location_name if detail.target_location else None,
        "quantity": detail.quantity,
        "created_at": detail.created_at.isoformat() if detail.created_at else None,
        "updated_at": detail.updated_at.isoformat() if detail.updated_at else None,
    }


def serialize_stock_transfer(transfer: StockTransfer):
    total_quantity = sum(detail.quantity for detail in transfer.details)
    return {
        "id": transfer.id,
        "transfer_code": transfer.transfer_code,
        "source_warehouse_id": transfer.source_warehouse_id,
        "source_warehouse_code": (
            transfer.source_warehouse.warehouse_code if transfer.source_warehouse else None
        ),
        "source_warehouse_name": (
            transfer.source_warehouse.warehouse_name if transfer.source_warehouse else None
        ),
        "target_warehouse_id": transfer.target_warehouse_id,
        "target_warehouse_code": (
            transfer.target_warehouse.warehouse_code if transfer.target_warehouse else None
        ),
        "target_warehouse_name": (
            transfer.target_warehouse.warehouse_name if transfer.target_warehouse else None
        ),
        "created_by": transfer.created_by,
        "created_by_name": transfer.creator.full_name if transfer.creator else None,
        "confirmed_by": transfer.confirmed_by,
        "confirmed_by_name": transfer.confirmer.full_name if transfer.confirmer else None,
        "status": transfer.status,
        "note": transfer.note,
        "detail_count": len(transfer.details),
        "total_quantity": total_quantity,
        "confirmed_at": transfer.confirmed_at.isoformat() if transfer.confirmed_at else None,
        "created_at": transfer.created_at.isoformat() if transfer.created_at else None,
        "updated_at": transfer.updated_at.isoformat() if transfer.updated_at else None,
        "details": [serialize_stock_transfer_detail(detail) for detail in transfer.details],
    }


def serialize_stocktake_detail(detail: StocktakeDetail):
    return {
        "id": detail.id,
        "product_id": detail.product_id,
        "product_code": detail.product.product_code if detail.product else None,
        "product_name": detail.product.product_name if detail.product else None,
        "location_id": detail.location_id,
        "location_code": detail.location.location_code if detail.location else None,
        "location_name": detail.location.location_name if detail.location else None,
        "system_quantity": detail.system_quantity,
        "actual_quantity": detail.actual_quantity,
        "difference_quantity": detail.difference_quantity,
        "note": detail.note,
        "created_at": detail.created_at.isoformat() if detail.created_at else None,
        "updated_at": detail.updated_at.isoformat() if detail.updated_at else None,
    }


def serialize_stocktake(stocktake: Stocktake):
    total_difference = sum(detail.difference_quantity for detail in stocktake.details)
    total_actual_quantity = sum(detail.actual_quantity for detail in stocktake.details)
    return {
        "id": stocktake.id,
        "stocktake_code": stocktake.stocktake_code,
        "warehouse_id": stocktake.warehouse_id,
        "warehouse_code": stocktake.warehouse.warehouse_code if stocktake.warehouse else None,
        "warehouse_name": stocktake.warehouse.warehouse_name if stocktake.warehouse else None,
        "created_by": stocktake.created_by,
        "created_by_name": stocktake.creator.full_name if stocktake.creator else None,
        "confirmed_by": stocktake.confirmed_by,
        "confirmed_by_name": stocktake.confirmer.full_name if stocktake.confirmer else None,
        "cancelled_by": stocktake.cancelled_by,
        "cancelled_by_name": stocktake.canceller.full_name if stocktake.canceller else None,
        "status": stocktake.status,
        "note": stocktake.note,
        "detail_count": len(stocktake.details),
        "total_actual_quantity": total_actual_quantity,
        "total_difference_quantity": total_difference,
        "confirmed_at": stocktake.confirmed_at.isoformat() if stocktake.confirmed_at else None,
        "cancelled_at": stocktake.cancelled_at.isoformat() if stocktake.cancelled_at else None,
        "created_at": stocktake.created_at.isoformat() if stocktake.created_at else None,
        "updated_at": stocktake.updated_at.isoformat() if stocktake.updated_at else None,
        "details": [serialize_stocktake_detail(detail) for detail in stocktake.details],
    }


def serialize_audit_log(audit_log: AuditLog):
    return {
        "id": audit_log.id,
        "action": audit_log.action,
        "entity_type": audit_log.entity_type,
        "entity_id": audit_log.entity_id,
        "entity_label": audit_log.entity_label,
        "description": audit_log.description,
        "ip_address": audit_log.ip_address,
        "actor_user_id": audit_log.actor_user_id,
        "actor_user_name": audit_log.actor_user.full_name if audit_log.actor_user else None,
        "actor_username": audit_log.actor_user.username if audit_log.actor_user else None,
        "target_user_id": audit_log.target_user_id,
        "target_user_name": audit_log.target_user.full_name if audit_log.target_user else None,
        "target_username": audit_log.target_user.username if audit_log.target_user else None,
        "created_at": audit_log.created_at.isoformat() if audit_log.created_at else None,
    }
