from __future__ import annotations

from ..extensions import db
from ..models import (
    ExportReceipt,
    ImportReceipt,
    Inventory,
    InventoryMovement,
    Product,
    StockTransfer,
    WarehouseLocation,
)
from ..utils import utc_now


def validate_location_in_warehouse(location_id, warehouse_id):
    location = db.session.get(WarehouseLocation, location_id)
    if not location or location.warehouse_id != warehouse_id:
        raise ValueError("Vị trí kho không thuộc kho đã chọn.")
    return location


def ensure_inventory_record(warehouse_id, product_id, location_id):
    record = Inventory.query.filter_by(
        warehouse_id=warehouse_id,
        product_id=product_id,
        location_id=location_id,
    ).first()
    if not record:
        record = Inventory(
            warehouse_id=warehouse_id,
            product_id=product_id,
            location_id=location_id,
            quantity=0,
        )
        db.session.add(record)
        db.session.flush()
    return record


def refresh_product_quantity(product_id):
    product = db.session.get(Product, product_id)
    if not product:
        return
    total = (
        db.session.query(db.func.coalesce(db.func.sum(Inventory.quantity), 0))
        .filter(Inventory.product_id == product_id)
        .scalar()
    )
    product.quantity_total = float(total or 0)


def adjust_inventory(
    warehouse_id,
    location_id,
    product_id,
    delta,
    movement_type,
    reference_type,
    reference_id,
    actor_id,
    note="",
):
    validate_location_in_warehouse(location_id, warehouse_id)
    record = ensure_inventory_record(warehouse_id, product_id, location_id)
    quantity_before = float(record.quantity)
    quantity_after = quantity_before + float(delta)
    if quantity_after < 0:
        raise ValueError("Tồn kho không đủ cho thao tác này.")

    record.quantity = quantity_after
    movement = InventoryMovement(
        warehouse_id=warehouse_id,
        location_id=location_id,
        product_id=product_id,
        movement_type=movement_type,
        reference_type=reference_type,
        reference_id=reference_id,
        quantity_before=quantity_before,
        quantity_change=float(delta),
        quantity_after=quantity_after,
        performed_by=actor_id,
        note=note,
    )
    db.session.add(movement)
    refresh_product_quantity(product_id)
    return movement


def confirm_import_receipt(receipt: ImportReceipt, actor_id):
    if receipt.status != "draft":
        raise ValueError("Chỉ phiếu nhập ở trạng thái nháp mới có thể xác nhận.")
    if not receipt.details:
        raise ValueError("Phiếu nhập phải có ít nhất một dòng hàng trước khi xác nhận.")

    for detail in receipt.details:
        adjust_inventory(
            warehouse_id=receipt.warehouse_id,
            location_id=detail.location_id,
            product_id=detail.product_id,
            delta=detail.quantity,
            movement_type="import",
            reference_type="import_receipt",
            reference_id=receipt.id,
            actor_id=actor_id,
            note=receipt.note or "",
        )

    receipt.status = "confirmed"
    receipt.confirmed_by = actor_id
    receipt.confirmed_at = utc_now()


def confirm_export_receipt(receipt: ExportReceipt, actor_id):
    if receipt.status != "draft":
        raise ValueError("Chỉ phiếu xuất ở trạng thái nháp mới có thể xác nhận.")
    if not receipt.details:
        raise ValueError("Phiếu xuất phải có ít nhất một dòng hàng trước khi xác nhận.")

    for detail in receipt.details:
        adjust_inventory(
            warehouse_id=receipt.warehouse_id,
            location_id=detail.location_id,
            product_id=detail.product_id,
            delta=-detail.quantity,
            movement_type="export",
            reference_type="export_receipt",
            reference_id=receipt.id,
            actor_id=actor_id,
            note=receipt.note or "",
        )

    receipt.status = "confirmed"
    receipt.confirmed_by = actor_id
    receipt.confirmed_at = utc_now()


def confirm_stock_transfer(transfer: StockTransfer, actor_id):
    if transfer.status != "draft":
        raise ValueError("Chỉ phiếu điều chuyển ở trạng thái nháp mới có thể xác nhận.")
    if not transfer.details:
        raise ValueError("Phiếu điều chuyển phải có ít nhất một dòng hàng trước khi xác nhận.")
    if transfer.source_warehouse_id == transfer.target_warehouse_id:
        raise ValueError("Kho nguồn và kho đích phải khác nhau.")

    for detail in transfer.details:
        adjust_inventory(
            warehouse_id=transfer.source_warehouse_id,
            location_id=detail.source_location_id,
            product_id=detail.product_id,
            delta=-detail.quantity,
            movement_type="transfer_out",
            reference_type="stock_transfer",
            reference_id=transfer.id,
            actor_id=actor_id,
            note=transfer.note or "",
        )
        adjust_inventory(
            warehouse_id=transfer.target_warehouse_id,
            location_id=detail.target_location_id,
            product_id=detail.product_id,
            delta=detail.quantity,
            movement_type="transfer_in",
            reference_type="stock_transfer",
            reference_id=transfer.id,
            actor_id=actor_id,
            note=transfer.note or "",
        )

    transfer.status = "confirmed"
    transfer.confirmed_by = actor_id
    transfer.confirmed_at = utc_now()
