from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required

from ..models import (
    ExportReceiptDetail,
    ExportReceipt,
    ImportReceipt,
    Inventory,
    InventoryMovement,
    Invoice,
    Product,
    Shipment,
    Warehouse,
)
from ..permissions import permission_required

reports_bp = Blueprint("reports", __name__)


def month_key(value):
    if not value:
        return "Unknown"
    return value.strftime("%Y-%m")


@reports_bp.get("/dashboard")
@jwt_required()
@permission_required("dashboard.view")
def dashboard():
    pending_receipts = ImportReceipt.query.filter_by(status="draft").count()
    pending_exports = ExportReceipt.query.filter_by(status="draft").count()
    active_shipments = Shipment.query.filter(Shipment.status.in_(["assigned", "in_transit"])).count()
    low_stock = Product.query.filter(Product.quantity_total <= Product.min_stock).count()
    return jsonify(
        {
            "metrics": {
                "products": Product.query.count(),
                "warehouses": Warehouse.query.count(),
                "pending_receipts": pending_receipts + pending_exports,
                "active_shipments": active_shipments,
                "low_stock_products": low_stock,
                "invoices": Invoice.query.count(),
            }
        }
    )


@reports_bp.get("/inventory-by-warehouse")
@jwt_required()
@permission_required("reports.view")
def inventory_by_warehouse():
    grouped = defaultdict(float)
    for row in Inventory.query.all():
        grouped[row.warehouse.warehouse_name if row.warehouse else "Unknown"] += row.quantity
    items = [{"warehouse_name": name, "quantity": quantity} for name, quantity in grouped.items()]
    return jsonify({"items": items})


@reports_bp.get("/stock-movement")
@jwt_required()
@permission_required("reports.view")
def stock_movement():
    imports = defaultdict(float)
    exports = defaultdict(float)
    for row in InventoryMovement.query.all():
        key = month_key(row.created_at)
        if row.quantity_change >= 0:
            imports[key] += row.quantity_change
        else:
            exports[key] += abs(row.quantity_change)
    keys = sorted(set(imports) | set(exports))
    items = [
        {"month": key, "import_quantity": imports.get(key, 0), "export_quantity": exports.get(key, 0)}
        for key in keys
    ]
    return jsonify({"items": items})


@reports_bp.get("/top-products")
@jwt_required()
@permission_required("reports.view")
def top_products():
    grouped = defaultdict(float)
    name_lookup = {}
    for detail in ExportReceiptDetail.query.all():
        grouped[detail.product_id] += detail.quantity
        if detail.product:
            name_lookup[detail.product_id] = detail.product.product_name
    items = sorted(
        [
            {
                "product_id": product_id,
                "product_name": name_lookup.get(product_id, f"Product {product_id}"),
                "quantity": quantity,
            }
            for product_id, quantity in grouped.items()
        ],
        key=lambda item: item["quantity"],
        reverse=True,
    )[:5]
    return jsonify({"items": items})


@reports_bp.get("/shipment-performance")
@jwt_required()
@permission_required("reports.view")
def shipment_performance():
    assigned = 0
    in_transit = 0
    delivered = 0
    cancelled = 0
    for shipment in Shipment.query.all():
        if shipment.status == "assigned":
            assigned += 1
        elif shipment.status == "in_transit":
            in_transit += 1
        elif shipment.status == "delivered":
            delivered += 1
        elif shipment.status == "cancelled":
            cancelled += 1
        else:
            assigned += 1
    return jsonify(
        {
            "items": [
                {"status": "assigned", "status_label": "Đã phân công", "count": assigned},
                {"status": "in_transit", "status_label": "Đang giao", "count": in_transit},
                {"status": "delivered", "status_label": "Đã giao", "count": delivered},
                {"status": "cancelled", "status_label": "Đã hủy", "count": cancelled},
            ]
        }
    )


@reports_bp.get("/revenue")
@jwt_required()
@permission_required("reports.view")
def revenue():
    revenue_map = defaultdict(float)
    payment_status_map = defaultdict(int)
    for invoice in Invoice.query.all():
        revenue_map[month_key(invoice.created_at)] += float(invoice.total_amount or 0)
        payment_status_map[invoice.status] += 1
    revenue_items = [
        {"month": month, "revenue": amount}
        for month, amount in sorted(revenue_map.items())
    ]
    payment_items = [
        {"status": status, "count": count}
        for status, count in payment_status_map.items()
    ]
    return jsonify({"revenue": revenue_items, "payment_status": payment_items})
