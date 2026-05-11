from app.models import (
    BankAccount,
    BankTransactionLog,
    Category,
    Customer,
    Conversation,
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
    Notification,
    Payment,
    Product,
    Shipment,
    Stocktake,
    StocktakeDetail,
    StockTransfer,
    StockTransferDetail,
    Supplier,
    Warehouse,
    WarehouseLocation,
)


def test_seed_all_creates_richer_demo_dataset(app):
    with app.app_context():
        assert Category.query.count() >= 8
        assert Supplier.query.count() >= 10
        assert Customer.query.count() >= 10
        assert BankAccount.query.count() >= 5
        assert Warehouse.query.count() >= 4
        assert WarehouseLocation.query.count() >= 13
        assert Product.query.count() >= 20
        assert Inventory.query.count() >= 30
        assert InventoryMovement.query.count() >= 40
        assert ImportReceipt.query.count() >= 3
        assert ImportReceiptDetail.query.count() >= 7
        assert ExportReceipt.query.count() >= 5
        assert ExportReceiptDetail.query.count() >= 9
        assert StockTransfer.query.count() >= 3
        assert StockTransferDetail.query.count() >= 4
        assert Stocktake.query.count() >= 3
        assert StocktakeDetail.query.count() >= 6
        assert Shipment.query.count() >= 3
        assert Invoice.query.count() >= 3
        assert InvoiceDetail.query.count() >= 5
        assert Payment.query.count() >= 2
        assert BankTransactionLog.query.count() >= 3
        assert InternalTask.query.count() >= 5
        assert Notification.query.count() >= 8
        assert Conversation.query.count() >= 4
        assert Message.query.count() >= 8

        warehouse_names = {item.warehouse_name for item in Warehouse.query.all()}
        assert "Kho Trung Tam" in warehouse_names
        assert "Kho Mien Nam" in warehouse_names
        assert "Kho Mien Bac" in warehouse_names
        assert "Kho Hang Loi Va Bao Hanh" in warehouse_names

        low_stock_codes = {
            item.product_code
            for item in Product.query.all()
            if item.quantity_total <= item.min_stock
        }
        assert {
            "PRD002",
            "PRD005",
            "PRD007",
            "PRD016",
            "PRD018",
            "PRD019",
            "PRD020",
        }.issubset(low_stock_codes)

        receipt_codes = {item.receipt_code for item in ImportReceipt.query.all()}
        assert {"IMP-DEMO-001", "IMP-DEMO-002", "IMP-DEMO-003"}.issubset(receipt_codes)
        export_receipt_codes = {item.receipt_code for item in ExportReceipt.query.all()}
        assert {
            "EXP-DEMO-001",
            "EXP-DEMO-002",
            "EXP-DEMO-003",
            "EXP-DEMO-004",
            "EXP-SHP-001",
        }.issubset(export_receipt_codes)
        transfer_codes = {item.transfer_code for item in StockTransfer.query.all()}
        assert {"TRF-DEMO-001", "TRF-DEMO-002", "TRF-DEMO-003"}.issubset(transfer_codes)
        stocktake_codes = {item.stocktake_code for item in Stocktake.query.all()}
        assert {"STK-DEMO-001", "STK-DEMO-002", "STK-DEMO-003"}.issubset(stocktake_codes)
        shipment_codes = {item.shipment_code for item in Shipment.query.all()}
        assert {"SHP-DEMO-001", "SHP-DEMO-002", "SHP-DEMO-003"}.issubset(shipment_codes)
        invoice_codes = {item.invoice_code for item in Invoice.query.all()}
        assert {"INV-DEMO-001", "INV-DEMO-002", "INV-DEMO-003"}.issubset(invoice_codes)
        payment_codes = {item.payment_code for item in Payment.query.all()}
        assert {"PAY-DEMO-001", "PAY-DEMO-002"}.issubset(payment_codes)
        bank_transaction_codes = {
            item.transaction_code for item in BankTransactionLog.query.all()
        }
        assert {
            "BNK-DEMO-001",
            "BNK-DEMO-002",
            "BNK-DEMO-003",
        }.issubset(bank_transaction_codes)
