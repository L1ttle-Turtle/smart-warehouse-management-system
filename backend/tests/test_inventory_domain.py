from app.extensions import db
from app.models import Inventory, InventoryMovement, Product, Warehouse, WarehouseLocation
from app.serializers import serialize_inventory_movement, serialize_inventory_row, serialize_product


def test_inventory_core_models_and_serializers(app):
    with app.app_context():
        warehouse = Warehouse(
            warehouse_code="WH-TST-001",
            warehouse_name="Kho Test Serializer",
            address="99 Le Loi",
            status="active",
        )
        location = WarehouseLocation(
            warehouse=warehouse,
            location_code="T-01",
            location_name="Ke T-01",
            status="active",
        )
        product = Product(
            product_code="PRD-TST-001",
            product_name="San pham test kho",
            quantity_total=12,
            min_stock=3,
            status="active",
        )
        inventory_row = Inventory(
            warehouse=warehouse,
            location=location,
            product=product,
            quantity=12,
        )
        movement = InventoryMovement(
            warehouse=warehouse,
            location=location,
            product=product,
            movement_type="adjustment",
            reference_type="test",
            reference_id=1,
            quantity_before=0,
            quantity_change=12,
            quantity_after=12,
            note="Inventory serializer test",
        )

        db.session.add_all([warehouse, location, product, inventory_row, movement])
        db.session.commit()

        assert warehouse.locations[0].location_code == "T-01"
        assert product.inventory_rows[0].quantity == 12

        serialized_product = serialize_product(product)
        serialized_inventory = serialize_inventory_row(inventory_row)
        serialized_movement = serialize_inventory_movement(movement)

        assert serialized_product["product_code"] == "PRD-TST-001"
        assert serialized_product["quantity_total"] == 12
        assert serialized_inventory["warehouse_name"] == "Kho Test Serializer"
        assert serialized_inventory["location_name"] == "Ke T-01"
        assert serialized_inventory["product_name"] == "San pham test kho"
        assert serialized_inventory["quantity"] == 12
        assert serialized_movement["movement_type"] == "adjustment"
        assert serialized_movement["reference_type"] == "test"
        assert serialized_movement["quantity_after"] == 12
