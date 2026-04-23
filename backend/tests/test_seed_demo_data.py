from app.models import (
    BankAccount,
    Category,
    Customer,
    ExportReceipt,
    ExportReceiptDetail,
    Inventory,
    InventoryMovement,
    ImportReceipt,
    ImportReceiptDetail,
    Product,
    StockTransfer,
    StockTransferDetail,
    Supplier,
    Warehouse,
    WarehouseLocation,
)


def test_seed_all_creates_richer_demo_dataset(app):
    with app.app_context():
        assert Category.query.count() >= 4
        assert Supplier.query.count() >= 4
        assert Customer.query.count() >= 4
        assert BankAccount.query.count() >= 3
        assert Warehouse.query.count() >= 2
        assert WarehouseLocation.query.count() >= 6
        assert Product.query.count() >= 7
        assert Inventory.query.count() >= 9
        assert InventoryMovement.query.count() >= 11
        assert ImportReceipt.query.count() >= 1
        assert ImportReceiptDetail.query.count() >= 2
        assert ExportReceipt.query.count() >= 1
        assert ExportReceiptDetail.query.count() >= 2
        assert StockTransfer.query.count() >= 1
        assert StockTransferDetail.query.count() >= 1

        warehouse_names = {item.warehouse_name for item in Warehouse.query.all()}
        assert "Kho Trung Tam" in warehouse_names
        assert "Kho Mien Nam" in warehouse_names

        low_stock_codes = {
            item.product_code
            for item in Product.query.all()
            if item.quantity_total <= item.min_stock
        }
        assert {"PRD002", "PRD005", "PRD007"}.issubset(low_stock_codes)

        receipt_codes = {item.receipt_code for item in ImportReceipt.query.all()}
        assert "IMP-DEMO-001" in receipt_codes
        export_receipt_codes = {item.receipt_code for item in ExportReceipt.query.all()}
        assert "EXP-DEMO-001" in export_receipt_codes
        transfer_codes = {item.transfer_code for item in StockTransfer.query.all()}
        assert "TRF-DEMO-001" in transfer_codes
