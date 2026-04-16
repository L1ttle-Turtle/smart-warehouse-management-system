from __future__ import annotations

from flask import Blueprint, abort, jsonify, request
from flask_jwt_extended import jwt_required

from ..extensions import db
from ..models import (
    BankAccount,
    Customer,
    ExportReceipt,
    ExportReceiptDetail,
    ImportReceipt,
    ImportReceiptDetail,
    Invoice,
    Payment,
    Shipment,
    StockTransfer,
    StockTransferDetail,
)
from ..permissions import get_current_user, permission_required
from ..schemas import (
    InvoiceSchema,
    PaymentSchema,
    ReceiptSchema,
    ShipmentSchema,
    ShipmentStatusSchema,
    TransferSchema,
)
from ..serializers import (
    serialize_export_receipt,
    serialize_import_receipt,
    serialize_invoice,
    serialize_payment,
    serialize_shipment,
    serialize_transfer,
)
from ..services.communications import create_notification, notify_roles
from ..services.inventory import (
    confirm_export_receipt,
    confirm_import_receipt,
    confirm_stock_transfer,
    refresh_invoice_payment_status,
)
from ..utils import generate_code, utc_now

operations_bp = Blueprint("operations", __name__)

SHIPMENT_TRANSITIONS = {
    "pending": {"preparing"},
    "preparing": {"delivering"},
    "delivering": {"delivered", "failed", "returned"},
    "delivered": set(),
    "failed": set(),
    "returned": set(),
}


def require_items(payload):
    if not payload.get("items"):
        abort(400, description="At least one item is required.")


def sync_receipt_items(receipt, items, detail_model, location_source="location_id"):
    receipt.details.clear()
    db.session.flush()
    for item in items:
        detail_kwargs = {
            "product_id": item["product_id"],
            "quantity": item["quantity"],
        }
        if detail_model in {ImportReceiptDetail, ExportReceiptDetail}:
            detail_kwargs["location_id"] = item["location_id"]
            detail_kwargs["unit_price"] = item["unit_price"]
            detail_kwargs["total_price"] = item["quantity"] * item["unit_price"]
        else:
            detail_kwargs["source_location_id"] = item["source_location_id"]
            detail_kwargs["destination_location_id"] = item["destination_location_id"]
        receipt.details.append(detail_model(**detail_kwargs))


@operations_bp.route("/import-receipts", methods=["GET", "POST"])
@jwt_required()
def import_receipts():
    if request.method == "GET":
        permission_required("receipts.view")(lambda: None)()
        items = ImportReceipt.query.order_by(ImportReceipt.import_date.desc()).all()
        return jsonify({"items": [serialize_import_receipt(item) for item in items]})

    permission_required("receipts.manage")(lambda: None)()
    payload = ReceiptSchema().load(request.get_json() or {})
    require_items(payload)
    user = get_current_user()
    receipt = ImportReceipt(
        receipt_code=generate_code("IMP"),
        warehouse_id=payload["warehouse_id"],
        created_by=user.id,
        supplier_id=payload.get("supplier_id"),
        note=payload.get("note"),
    )
    db.session.add(receipt)
    db.session.flush()
    for item in payload["items"]:
        receipt.details.append(
            ImportReceiptDetail(
                product_id=item["product_id"],
                location_id=item["location_id"],
                quantity=item["quantity"],
                unit_price=item["unit_price"],
                total_price=item["quantity"] * item["unit_price"],
            )
        )
    db.session.commit()
    notify_roles(
        user.id,
        ["admin", "manager"],
        "Phieu nhap moi",
        f"Phieu nhap {receipt.receipt_code} vua duoc tao.",
        "receipt",
    )
    db.session.commit()
    return jsonify({"item": serialize_import_receipt(receipt)}), 201


@operations_bp.route("/import-receipts/<int:receipt_id>", methods=["GET", "PUT"])
@jwt_required()
def import_receipt_detail(receipt_id):
    receipt = db.get_or_404(ImportReceipt, receipt_id)
    if request.method == "GET":
        permission_required("receipts.view")(lambda: None)()
        return jsonify({"item": serialize_import_receipt(receipt)})

    permission_required("receipts.manage")(lambda: None)()
    if receipt.status != "draft":
        abort(400, description="Only draft receipts can be edited.")
    payload = ReceiptSchema().load(request.get_json() or {})
    require_items(payload)
    receipt.warehouse_id = payload["warehouse_id"]
    receipt.supplier_id = payload.get("supplier_id")
    receipt.note = payload.get("note")
    sync_receipt_items(receipt, payload["items"], ImportReceiptDetail)
    db.session.commit()
    return jsonify({"item": serialize_import_receipt(receipt)})


@operations_bp.post("/import-receipts/<int:receipt_id>/confirm")
@jwt_required()
@permission_required("receipts.manage")
def confirm_import(receipt_id):
    receipt = db.get_or_404(ImportReceipt, receipt_id)
    user = get_current_user()
    try:
        confirm_import_receipt(receipt, user.id)
        db.session.commit()
    except ValueError as exc:
        db.session.rollback()
        abort(400, description=str(exc))
    notify_roles(
        user.id,
        ["admin", "manager"],
        "Nhap kho da duyet",
        f"Phieu nhap {receipt.receipt_code} da duoc xac nhan.",
        "receipt",
    )
    db.session.commit()
    return jsonify({"item": serialize_import_receipt(receipt)})


@operations_bp.post("/import-receipts/<int:receipt_id>/cancel")
@jwt_required()
@permission_required("receipts.manage")
def cancel_import(receipt_id):
    receipt = db.get_or_404(ImportReceipt, receipt_id)
    if receipt.status != "draft":
        abort(400, description="Only draft receipts can be cancelled.")
    receipt.status = "cancelled"
    db.session.commit()
    return jsonify({"item": serialize_import_receipt(receipt)})


@operations_bp.route("/export-receipts", methods=["GET", "POST"])
@jwt_required()
def export_receipts():
    if request.method == "GET":
        permission_required("receipts.view")(lambda: None)()
        items = ExportReceipt.query.order_by(ExportReceipt.export_date.desc()).all()
        return jsonify({"items": [serialize_export_receipt(item) for item in items]})

    permission_required("receipts.manage")(lambda: None)()
    payload = ReceiptSchema().load(request.get_json() or {})
    require_items(payload)
    user = get_current_user()
    receipt = ExportReceipt(
        receipt_code=generate_code("EXP"),
        warehouse_id=payload["warehouse_id"],
        created_by=user.id,
        customer_id=payload.get("customer_id"),
        note=payload.get("note"),
    )
    db.session.add(receipt)
    db.session.flush()
    for item in payload["items"]:
        receipt.details.append(
            ExportReceiptDetail(
                product_id=item["product_id"],
                location_id=item["location_id"],
                quantity=item["quantity"],
                unit_price=item["unit_price"],
                total_price=item["quantity"] * item["unit_price"],
            )
        )
    db.session.commit()
    notify_roles(
        user.id,
        ["admin", "manager"],
        "Phieu xuat moi",
        f"Phieu xuat {receipt.receipt_code} vua duoc tao.",
        "receipt",
    )
    db.session.commit()
    return jsonify({"item": serialize_export_receipt(receipt)}), 201


@operations_bp.route("/export-receipts/<int:receipt_id>", methods=["GET", "PUT"])
@jwt_required()
def export_receipt_detail(receipt_id):
    receipt = db.get_or_404(ExportReceipt, receipt_id)
    if request.method == "GET":
        permission_required("receipts.view")(lambda: None)()
        return jsonify({"item": serialize_export_receipt(receipt)})

    permission_required("receipts.manage")(lambda: None)()
    if receipt.status != "draft":
        abort(400, description="Only draft receipts can be edited.")
    payload = ReceiptSchema().load(request.get_json() or {})
    require_items(payload)
    receipt.warehouse_id = payload["warehouse_id"]
    receipt.customer_id = payload.get("customer_id")
    receipt.note = payload.get("note")
    sync_receipt_items(receipt, payload["items"], ExportReceiptDetail)
    db.session.commit()
    return jsonify({"item": serialize_export_receipt(receipt)})


@operations_bp.post("/export-receipts/<int:receipt_id>/confirm")
@jwt_required()
@permission_required("receipts.manage")
def confirm_export(receipt_id):
    receipt = db.get_or_404(ExportReceipt, receipt_id)
    user = get_current_user()
    try:
        confirm_export_receipt(receipt, user.id)
        db.session.commit()
    except ValueError as exc:
        db.session.rollback()
        abort(400, description=str(exc))
    notify_roles(
        user.id,
        ["admin", "manager"],
        "Xuat kho da duyet",
        f"Phieu xuat {receipt.receipt_code} da duoc xac nhan.",
        "receipt",
    )
    db.session.commit()
    return jsonify({"item": serialize_export_receipt(receipt)})


@operations_bp.post("/export-receipts/<int:receipt_id>/cancel")
@jwt_required()
@permission_required("receipts.manage")
def cancel_export(receipt_id):
    receipt = db.get_or_404(ExportReceipt, receipt_id)
    if receipt.status != "draft":
        abort(400, description="Only draft receipts can be cancelled.")
    receipt.status = "cancelled"
    db.session.commit()
    return jsonify({"item": serialize_export_receipt(receipt)})


@operations_bp.route("/stock-transfers", methods=["GET", "POST"])
@jwt_required()
def stock_transfers():
    if request.method == "GET":
        permission_required("transfers.view")(lambda: None)()
        items = StockTransfer.query.order_by(StockTransfer.transfer_date.desc()).all()
        return jsonify({"items": [serialize_transfer(item) for item in items]})

    permission_required("transfers.manage")(lambda: None)()
    payload = TransferSchema().load(request.get_json() or {})
    require_items(payload)
    user = get_current_user()
    transfer = StockTransfer(
        transfer_code=generate_code("TRF"),
        source_warehouse_id=payload["source_warehouse_id"],
        destination_warehouse_id=payload["destination_warehouse_id"],
        created_by=user.id,
        note=payload.get("note"),
    )
    db.session.add(transfer)
    db.session.flush()
    for item in payload["items"]:
        transfer.details.append(
            StockTransferDetail(
                product_id=item["product_id"],
                source_location_id=item["source_location_id"],
                destination_location_id=item["destination_location_id"],
                quantity=item["quantity"],
            )
        )
    db.session.commit()
    return jsonify({"item": serialize_transfer(transfer)}), 201


@operations_bp.route("/stock-transfers/<int:transfer_id>", methods=["GET", "PUT"])
@jwt_required()
def stock_transfer_detail(transfer_id):
    transfer = db.get_or_404(StockTransfer, transfer_id)
    if request.method == "GET":
        permission_required("transfers.view")(lambda: None)()
        return jsonify({"item": serialize_transfer(transfer)})

    permission_required("transfers.manage")(lambda: None)()
    if transfer.status != "draft":
        abort(400, description="Only draft transfers can be edited.")
    payload = TransferSchema().load(request.get_json() or {})
    require_items(payload)
    transfer.source_warehouse_id = payload["source_warehouse_id"]
    transfer.destination_warehouse_id = payload["destination_warehouse_id"]
    transfer.note = payload.get("note")
    sync_receipt_items(transfer, payload["items"], StockTransferDetail)
    db.session.commit()
    return jsonify({"item": serialize_transfer(transfer)})


@operations_bp.post("/stock-transfers/<int:transfer_id>/confirm")
@jwt_required()
@permission_required("transfers.manage")
def confirm_transfer(transfer_id):
    transfer = db.get_or_404(StockTransfer, transfer_id)
    user = get_current_user()
    try:
        confirm_stock_transfer(transfer, user.id)
        db.session.commit()
    except ValueError as exc:
        db.session.rollback()
        abort(400, description=str(exc))
    return jsonify({"item": serialize_transfer(transfer)})


@operations_bp.post("/stock-transfers/<int:transfer_id>/cancel")
@jwt_required()
@permission_required("transfers.manage")
def cancel_transfer(transfer_id):
    transfer = db.get_or_404(StockTransfer, transfer_id)
    if transfer.status != "draft":
        abort(400, description="Only draft transfers can be cancelled.")
    transfer.status = "cancelled"
    db.session.commit()
    return jsonify({"item": serialize_transfer(transfer)})


@operations_bp.route("/shipments", methods=["GET", "POST"])
@jwt_required()
def shipments():
    user = get_current_user()
    if request.method == "GET":
        permission_required("shipments.view", "shipments.assigned", any_of=True)(lambda: None)()
        query = Shipment.query.order_by(Shipment.created_at.desc())
        if "shipments.manage" not in user.permission_names:
            query = query.filter(Shipment.assigned_to == user.id)
        items = query.all()
        return jsonify({"items": [serialize_shipment(item) for item in items]})

    permission_required("shipments.manage")(lambda: None)()
    payload = ShipmentSchema().load(request.get_json() or {})
    export_receipt = db.get_or_404(ExportReceipt, payload["export_receipt_id"])
    if export_receipt.status != "confirmed":
        abort(400, description="Shipment can only be created from confirmed export receipt.")
    shipment = Shipment(
        shipment_code=generate_code("SHP"),
        export_receipt_id=payload["export_receipt_id"],
        assigned_to=payload.get("assigned_to"),
        delivery_address=payload["delivery_address"],
        expected_delivery_at=payload.get("expected_delivery_at"),
        note=payload.get("note"),
    )
    db.session.add(shipment)
    db.session.commit()
    if shipment.assigned_to:
        create_notification(
            sender_id=user.id,
            receiver_id=shipment.assigned_to,
            title="Van don moi",
            content=f"Ban duoc gan van don {shipment.shipment_code}.",
            type="shipment",
        )
        db.session.commit()
    return jsonify({"item": serialize_shipment(shipment)}), 201


@operations_bp.route("/shipments/<int:shipment_id>", methods=["GET", "PUT"])
@jwt_required()
def shipment_detail(shipment_id):
    shipment = db.get_or_404(Shipment, shipment_id)
    user = get_current_user()
    if request.method == "GET":
        permission_required("shipments.view", "shipments.assigned", any_of=True)(lambda: None)()
        if "shipments.manage" not in user.permission_names and shipment.assigned_to != user.id:
            abort(403, description="You can only view your assigned shipment.")
        return jsonify({"item": serialize_shipment(shipment)})

    permission_required("shipments.manage")(lambda: None)()
    payload = request.get_json() or {}
    for field in ["assigned_to", "delivery_address", "expected_delivery_at", "note"]:
        if field not in payload:
            continue
        setattr(shipment, field, payload[field])
    db.session.commit()
    return jsonify({"item": serialize_shipment(shipment)})


@operations_bp.patch("/shipments/<int:shipment_id>/status")
@jwt_required()
@permission_required("shipments.manage", "shipments.assigned", any_of=True)
def update_shipment_status(shipment_id):
    shipment = db.get_or_404(Shipment, shipment_id)
    user = get_current_user()
    if "shipments.manage" not in user.permission_names and shipment.assigned_to != user.id:
        abort(403, description="You can only update your assigned shipment.")

    payload = ShipmentStatusSchema().load(request.get_json() or {})
    next_status = payload["shipping_status"]
    allowed_transitions = SHIPMENT_TRANSITIONS.get(shipment.shipping_status, set())
    if next_status != shipment.shipping_status and next_status not in allowed_transitions:
        abort(
            400,
            description=(
                f"Invalid shipment status transition: {shipment.shipping_status} -> {next_status}."
            ),
        )

    shipment.shipping_status = next_status
    shipment.note = payload.get("note") or shipment.note
    if shipment.shipping_status == "delivering" and not shipment.shipped_at:
        shipment.shipped_at = utc_now()
    if shipment.shipping_status in {"delivered", "failed", "returned"}:
        shipment.delivered_at = payload.get("delivered_at") or utc_now()
    db.session.commit()
    notify_roles(
        user.id,
        ["admin", "manager"],
        "Cap nhat van don",
        f"Van don {shipment.shipment_code} da chuyen sang {shipment.shipping_status}.",
        "shipment",
    )
    db.session.commit()
    return jsonify({"item": serialize_shipment(shipment)})


@operations_bp.route("/invoices", methods=["GET", "POST"])
@jwt_required()
def invoices():
    if request.method == "GET":
        permission_required("invoices.view")(lambda: None)()
        items = Invoice.query.order_by(Invoice.created_at.desc()).all()
        return jsonify({"items": [serialize_invoice(item) for item in items]})

    permission_required("invoices.manage")(lambda: None)()
    payload = InvoiceSchema().load(request.get_json() or {})
    user = get_current_user()
    export_receipt = db.get_or_404(ExportReceipt, payload["export_receipt_id"])
    if export_receipt.status != "confirmed":
        abort(400, description="Only confirmed export receipts can create invoices.")
    existing = Invoice.query.filter_by(export_receipt_id=export_receipt.id).first()
    if existing:
        abort(409, description="Invoice already exists for this export receipt.")

    total_amount = sum(detail.total_price for detail in export_receipt.details)
    tax_amount = total_amount * payload["tax_rate"]
    invoice = Invoice(
        invoice_code=generate_code("INV"),
        export_receipt_id=export_receipt.id,
        customer_id=payload["customer_id"],
        total_amount=total_amount,
        tax_amount=tax_amount,
        final_amount=total_amount + tax_amount,
        created_by=user.id,
    )
    db.session.add(invoice)
    db.session.commit()
    return jsonify({"item": serialize_invoice(invoice)}), 201


@operations_bp.get("/invoices/<int:invoice_id>")
@jwt_required()
@permission_required("invoices.view")
def invoice_detail(invoice_id):
    invoice = db.get_or_404(Invoice, invoice_id)
    return jsonify({"item": serialize_invoice(invoice)})


@operations_bp.route("/payments", methods=["GET", "POST"])
@jwt_required()
def payments():
    if request.method == "GET":
        permission_required("payments.view")(lambda: None)()
        items = Payment.query.order_by(Payment.paid_at.desc()).all()
        return jsonify({"items": [serialize_payment(item) for item in items]})

    permission_required("payments.manage")(lambda: None)()
    payload = PaymentSchema().load(request.get_json() or {})
    user = get_current_user()
    invoice = db.get_or_404(Invoice, payload["invoice_id"])
    db.get_or_404(BankAccount, payload["bank_account_id"])
    payment = Payment(
        invoice_id=payload["invoice_id"],
        bank_account_id=payload["bank_account_id"],
        payment_method=payload["payment_method"],
        transfer_code=payload["transfer_code"],
        amount=payload["amount"],
        paid_at=payload.get("paid_at") or utc_now(),
        created_by=user.id,
    )
    db.session.add(payment)
    db.session.flush()
    refresh_invoice_payment_status(invoice)
    db.session.commit()
    notify_roles(
        user.id,
        ["admin", "manager"],
        "Thanh toan cap nhat",
        f"Hoa don {invoice.invoice_code} dang o trang thai {invoice.payment_status}.",
        "payment",
    )
    db.session.commit()
    return jsonify({"item": serialize_payment(payment), "invoice": serialize_invoice(invoice)}), 201
