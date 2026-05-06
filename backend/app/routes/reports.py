from __future__ import annotations

from collections import defaultdict

from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required

from ..models import (
    ExportReceiptDetail,
    ExportReceipt,
    ImportReceipt,
    Inventory,
    InventoryMovement,
    Invoice,
    Payment,
    Product,
    Shipment,
    Stocktake,
    StockTransfer,
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


@reports_bp.get("/summary")
@jwt_required()
@permission_required("reports.view")
def summary():
    inventory_rows = Inventory.query.all()
    total_inventory_quantity = sum(row.quantity for row in inventory_rows)
    low_stock_lines = 0
    out_of_stock_lines = 0
    for row in inventory_rows:
        quantity = float(row.quantity or 0)
        min_stock = float(row.product.min_stock or 0) if row.product else 0
        if quantity <= 0:
            out_of_stock_lines += 1
        elif quantity <= min_stock:
            low_stock_lines += 1

    draft_documents = (
        ImportReceipt.query.filter_by(status="draft").count()
        + ExportReceipt.query.filter_by(status="draft").count()
        + StockTransfer.query.filter_by(status="draft").count()
        + Stocktake.query.filter_by(status="draft").count()
    )
    active_shipments = Shipment.query.filter(Shipment.status.in_(["assigned", "in_transit"])).count()
    total_revenue = sum(float(invoice.total_amount or 0) for invoice in Invoice.query.all())
    paid_amount = sum(float(payment.amount or 0) for payment in Payment.query.all())
    outstanding_amount = max(total_revenue - paid_amount, 0)

    metrics = [
        {
            "key": "total_inventory_quantity",
            "label": "Tổng tồn kho",
            "value": total_inventory_quantity,
            "suffix": "đơn vị",
            "tone": "primary",
        },
        {
            "key": "stock_alert_lines",
            "label": "Dòng tồn cần chú ý",
            "value": low_stock_lines + out_of_stock_lines,
            "suffix": "dòng",
            "tone": "warning",
        },
        {
            "key": "draft_documents",
            "label": "Chứng từ nháp",
            "value": draft_documents,
            "suffix": "phiếu",
            "tone": "teal",
        },
        {
            "key": "active_shipments",
            "label": "Đơn đang giao",
            "value": active_shipments,
            "suffix": "đơn",
            "tone": "success",
        },
        {
            "key": "total_revenue",
            "label": "Doanh thu hóa đơn",
            "value": total_revenue,
            "format": "currency",
            "tone": "danger",
        },
        {
            "key": "outstanding_amount",
            "label": "Công nợ còn lại",
            "value": outstanding_amount,
            "format": "currency",
            "tone": "warning",
        },
    ]

    return jsonify(
        {
            "metrics": metrics,
            "summary": {
                "total_inventory_quantity": total_inventory_quantity,
                "low_stock_lines": low_stock_lines,
                "out_of_stock_lines": out_of_stock_lines,
                "draft_documents": draft_documents,
                "active_shipments": active_shipments,
                "total_revenue": total_revenue,
                "paid_amount": paid_amount,
                "outstanding_amount": outstanding_amount,
            },
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
