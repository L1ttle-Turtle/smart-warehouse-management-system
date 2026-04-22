from app.models import (
    BankAccount,
    Category,
    Customer,
    Inventory,
    InventoryMovement,
    Product,
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

        warehouse_names = {item.warehouse_name for item in Warehouse.query.all()}
        assert "Kho Trung Tam" in warehouse_names
        assert "Kho Mien Nam" in warehouse_names

        low_stock_codes = {
            item.product_code
            for item in Product.query.all()
            if item.quantity_total <= item.min_stock
        }
        assert {"PRD002", "PRD005", "PRD007"}.issubset(low_stock_codes)
