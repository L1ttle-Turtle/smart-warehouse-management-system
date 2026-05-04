from __future__ import annotations

from .constants import DEFAULT_ROLE_PASSWORDS, RESOURCE_PERMISSIONS, ROLE_PERMISSION_MAP
from .extensions import db
from .models import (
    BankAccount,
    Category,
    Conversation,
    ConversationParticipant,
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
    Permission,
    Notification,
    Product,
    Role,
    Shipment,
    Stocktake,
    StocktakeDetail,
    StockTransfer,
    StockTransferDetail,
    Supplier,
    User,
    Warehouse,
    WarehouseLocation,
)
from .services.inventory import confirm_export_receipt
from .utils import utc_now


def seed_roles_and_permissions():
    permission_map = {}
    for permission_name in sorted(RESOURCE_PERMISSIONS):
        permission = Permission.query.filter_by(permission_name=permission_name).first()
        if not permission:
            permission = Permission(
                permission_name=permission_name,
                description=f"Permission for {permission_name}",
            )
            db.session.add(permission)
        permission_map[permission_name] = permission
    db.session.flush()

    for role_name, permissions in ROLE_PERMISSION_MAP.items():
        role = Role.query.filter_by(role_name=role_name).first()
        if not role:
            role = Role(
                role_name=role_name,
                description=f"{role_name.title()} role",
            )
            db.session.add(role)
        role.permissions = [permission_map[name] for name in permissions]
    db.session.flush()


def seed_default_users():
    role_lookup = {role.role_name: role for role in Role.query.all()}
    for index, role_name in enumerate(
        ["admin", "manager", "staff", "accountant", "shipper"],
        start=1,
    ):
        user = User.query.filter_by(username=role_name).first()
        if user:
            continue
        user = User(
            username=role_name,
            full_name=role_name.title(),
            email=f"{role_name}@warehouse.local",
            phone=f"09000000{index}",
            status="active",
            must_change_password=False,
            role=role_lookup[role_name],
        )
        user.set_password(DEFAULT_ROLE_PASSWORDS[role_name])
        db.session.add(user)


def seed_default_employees():
    seeded_users = User.query.order_by(User.id.asc()).all()
    for index, user in enumerate(seeded_users, start=1):
        employee = Employee.query.filter_by(user_id=user.id).first()
        if employee:
            continue
        employee = Employee(
            employee_code=f"EMP{index:03d}",
            user_id=user.id,
            full_name=user.full_name,
            department="Van hanh" if user.role.role_name in {"staff", "shipper"} else "Quan tri",
            position=user.role.role_name.title(),
            phone=user.phone,
            email=user.email,
            status="active",
        )
        db.session.add(employee)


def seed_catalogs():
    categories = [
        {"category_name": "Dien tu", "description": "Nhom hang thiet bi dien tu"},
        {"category_name": "Van phong pham", "description": "Nhom hang van phong pham"},
        {"category_name": "Dong goi", "description": "Nhom hang vat tu dong goi va dan nhan"},
        {"category_name": "Phu kien kho", "description": "Nhom hang phu kien va cong cu kho"},
    ]
    for item in categories:
        category = Category.query.filter_by(category_name=item["category_name"]).first()
        if category:
            continue
        db.session.add(Category(**item))
    db.session.flush()

    suppliers = [
        {
            "supplier_code": "SUP001",
            "supplier_name": "Cong ty Minh Phat",
            "email": "minhphat@supplier.local",
            "phone": "0901111111",
            "address": "12 Nguyen Trai, Ha Noi",
            "status": "active",
        },
        {
            "supplier_code": "SUP002",
            "supplier_name": "Nha cung cap An Khang",
            "email": "ankhang@supplier.local",
            "phone": "0902222222",
            "address": "88 Le Loi, Da Nang",
            "status": "inactive",
        },
        {
            "supplier_code": "SUP003",
            "supplier_name": "Sao Mai Logistics",
            "email": "saomai@supplier.local",
            "phone": "0903333333",
            "address": "15 Cach Mang Thang 8, HCM",
            "status": "active",
        },
        {
            "supplier_code": "SUP004",
            "supplier_name": "Bao Tin Equipment",
            "email": "baotin@supplier.local",
            "phone": "0904444444",
            "address": "44 Hung Vuong, Hai Phong",
            "status": "active",
        },
    ]
    for item in suppliers:
        supplier = Supplier.query.filter_by(supplier_code=item["supplier_code"]).first()
        if supplier:
            continue
        db.session.add(Supplier(**item))

    customers = [
        {
            "customer_code": "CUS001",
            "customer_name": "Cua hang Gia Huy",
            "email": "giahuy@customer.local",
            "phone": "0911111111",
            "address": "25 Tran Hung Dao, HCM",
            "status": "active",
        },
        {
            "customer_code": "CUS002",
            "customer_name": "Sieu thi Phuong Nam",
            "email": "phuongnam@customer.local",
            "phone": "0912222222",
            "address": "102 Bach Dang, Can Tho",
            "status": "inactive",
        },
        {
            "customer_code": "CUS003",
            "customer_name": "Cong ty Thien An",
            "email": "thienan@customer.local",
            "phone": "0913333333",
            "address": "48 Nguyen Van Cu, Hai Phong",
            "status": "active",
        },
        {
            "customer_code": "CUS004",
            "customer_name": "He thong Ban le Mekong",
            "email": "mekong@customer.local",
            "phone": "0914444444",
            "address": "08 Tran Phu, Can Tho",
            "status": "active",
        },
    ]
    for item in customers:
        customer = Customer.query.filter_by(customer_code=item["customer_code"]).first()
        if customer:
            continue
        db.session.add(Customer(**item))

    bank_accounts = [
        {
            "bank_name": "Vietcombank",
            "account_number": "0123456789",
            "account_holder": "Cong ty Kho Thong Minh",
            "branch": "Chi nhanh HCM",
            "status": "active",
        },
        {
            "bank_name": "ACB",
            "account_number": "9876543210",
            "account_holder": "Cong ty Kho Thong Minh",
            "branch": "Chi nhanh Ha Noi",
            "status": "inactive",
        },
        {
            "bank_name": "Techcombank",
            "account_number": "5566778899",
            "account_holder": "Cong ty Kho Thong Minh",
            "branch": "Chi nhanh Da Nang",
            "status": "active",
        },
    ]
    for item in bank_accounts:
        bank_account = BankAccount.query.filter_by(account_number=item["account_number"]).first()
        if bank_account:
            continue
        db.session.add(BankAccount(**item))


def seed_inventory_demo():
    category_lookup = {
        category.category_name: category
        for category in Category.query.order_by(Category.id.asc()).all()
    }

    warehouses = [
        {
            "warehouse_code": "WH001",
            "warehouse_name": "Kho Trung Tam",
            "address": "12 Nguyen Trai, Ha Noi",
            "status": "active",
            "locations": [
                {"location_code": "A-01", "location_name": "Ke A-01", "status": "active"},
                {"location_code": "B-01", "location_name": "Ke B-01", "status": "active"},
                {"location_code": "C-01", "location_name": "Ke C-01", "status": "active"},
            ],
        },
        {
            "warehouse_code": "WH002",
            "warehouse_name": "Kho Mien Nam",
            "address": "215 Vo Van Kiet, HCM",
            "status": "active",
            "locations": [
                {"location_code": "A-01", "location_name": "Day A-01", "status": "active"},
                {"location_code": "B-01", "location_name": "Day B-01", "status": "active"},
                {"location_code": "C-01", "location_name": "Day C-01", "status": "active"},
            ],
        },
    ]
    warehouse_lookup = {}
    location_lookup = {}
    for warehouse_item in warehouses:
        warehouse = Warehouse.query.filter_by(warehouse_code=warehouse_item["warehouse_code"]).first()
        if not warehouse:
            warehouse = Warehouse(
                warehouse_code=warehouse_item["warehouse_code"],
                warehouse_name=warehouse_item["warehouse_name"],
                address=warehouse_item["address"],
                status=warehouse_item["status"],
            )
            db.session.add(warehouse)
            db.session.flush()
        else:
            warehouse.warehouse_name = warehouse_item["warehouse_name"]
            warehouse.address = warehouse_item["address"]
            warehouse.status = warehouse_item["status"]
        warehouse_lookup[warehouse_item["warehouse_code"]] = warehouse

        for location_item in warehouse_item["locations"]:
            location = WarehouseLocation.query.filter_by(
                warehouse_id=warehouse.id,
                location_code=location_item["location_code"],
            ).first()
            if not location:
                location = WarehouseLocation(
                    warehouse_id=warehouse.id,
                    location_code=location_item["location_code"],
                    location_name=location_item["location_name"],
                    status=location_item["status"],
                )
                db.session.add(location)
                db.session.flush()
            else:
                location.location_name = location_item["location_name"]
                location.status = location_item["status"]
            location_lookup[(warehouse_item["warehouse_code"], location_item["location_code"])] = location

    products = [
        {
            "product_code": "PRD001",
            "product_name": "May quet ma vach",
            "category_name": "Dien tu",
            "min_stock": 10,
            "status": "active",
            "description": "Thiet bi quet ma vach dung cho dong goi va kiem ke.",
        },
        {
            "product_code": "PRD002",
            "product_name": "May in nhiet",
            "category_name": "Dien tu",
            "min_stock": 10,
            "status": "active",
            "description": "May in nhiet dung cho van don va tem san pham.",
        },
        {
            "product_code": "PRD003",
            "product_name": "Tem dan ma van",
            "category_name": "Dong goi",
            "min_stock": 50,
            "status": "active",
            "description": "Tem dan danh cho nhan kho va dan ma van.",
        },
        {
            "product_code": "PRD004",
            "product_name": "Bo dam kho",
            "category_name": "Dien tu",
            "min_stock": 12,
            "status": "active",
            "description": "Thiet bi lien lac noi bo cho nhan su kho.",
        },
        {
            "product_code": "PRD005",
            "product_name": "Xe day hang mini",
            "category_name": "Phu kien kho",
            "min_stock": 8,
            "status": "active",
            "description": "Xe day mini phuc vu di chuyen hang nhe trong kho.",
        },
        {
            "product_code": "PRD006",
            "product_name": "Mang PE quan pallet",
            "category_name": "Dong goi",
            "min_stock": 20,
            "status": "active",
            "description": "Vat tu quan pallet de co dinh kien hang khi van chuyen.",
        },
        {
            "product_code": "PRD007",
            "product_name": "Giay in kho A4",
            "category_name": "Van phong pham",
            "min_stock": 40,
            "status": "active",
            "description": "Giay in tai lieu kho, bien ban va danh sach kiem dem.",
        },
    ]
    product_lookup = {}
    for item in products:
        category = category_lookup.get(item["category_name"])
        product = Product.query.filter_by(product_code=item["product_code"]).first()
        if not product:
            product = Product(
                product_code=item["product_code"],
                product_name=item["product_name"],
                category_id=category.id if category else None,
                quantity_total=0,
                min_stock=item["min_stock"],
                status=item["status"],
                description=item["description"],
            )
            db.session.add(product)
            db.session.flush()
        else:
            product.product_name = item["product_name"]
            product.category_id = category.id if category else None
            product.min_stock = item["min_stock"]
            product.status = item["status"]
            product.description = item["description"]
        product_lookup[item["product_code"]] = product

    inventory_rows = [
        {"warehouse_code": "WH001", "location_code": "A-01", "product_code": "PRD001", "quantity": 24},
        {"warehouse_code": "WH002", "location_code": "A-01", "product_code": "PRD001", "quantity": 8},
        {"warehouse_code": "WH001", "location_code": "B-01", "product_code": "PRD002", "quantity": 6},
        {"warehouse_code": "WH001", "location_code": "C-01", "product_code": "PRD003", "quantity": 120},
        {"warehouse_code": "WH002", "location_code": "B-01", "product_code": "PRD003", "quantity": 60},
        {"warehouse_code": "WH001", "location_code": "A-01", "product_code": "PRD004", "quantity": 0},
        {"warehouse_code": "WH002", "location_code": "C-01", "product_code": "PRD004", "quantity": 14},
        {"warehouse_code": "WH001", "location_code": "B-01", "product_code": "PRD005", "quantity": 4},
        {"warehouse_code": "WH002", "location_code": "A-01", "product_code": "PRD006", "quantity": 48},
        {"warehouse_code": "WH001", "location_code": "C-01", "product_code": "PRD007", "quantity": 30},
    ]
    quantity_totals = {product_code: 0 for product_code in product_lookup}
    for item in inventory_rows:
        warehouse = warehouse_lookup[item["warehouse_code"]]
        location = location_lookup[(item["warehouse_code"], item["location_code"])]
        product = product_lookup[item["product_code"]]
        row = Inventory.query.filter_by(
            warehouse_id=warehouse.id,
            location_id=location.id,
            product_id=product.id,
        ).first()
        if not row:
            row = Inventory(
                warehouse_id=warehouse.id,
                location_id=location.id,
                product_id=product.id,
                quantity=item["quantity"],
            )
            db.session.add(row)
        else:
            row.quantity = item["quantity"]
        quantity_totals[item["product_code"]] += item["quantity"]

    for product_code, product in product_lookup.items():
        product.quantity_total = quantity_totals.get(product_code, 0)

    manager_user = User.query.filter_by(username="manager").first()
    movements = [
        {
            "warehouse_code": "WH001",
            "location_code": "A-01",
            "product_code": "PRD001",
            "movement_type": "adjustment",
            "reference_type": "seed",
            "reference_id": 2001,
            "quantity_before": 0,
            "quantity_change": 24,
            "quantity_after": 24,
            "note": "Seed opening stock for barcode scanner",
        },
        {
            "warehouse_code": "WH002",
            "location_code": "A-01",
            "product_code": "PRD001",
            "movement_type": "adjustment",
            "reference_type": "seed",
            "reference_id": 2002,
            "quantity_before": 0,
            "quantity_change": 8,
            "quantity_after": 8,
            "note": "Seed opening stock for barcode scanner at south warehouse",
        },
        {
            "warehouse_code": "WH001",
            "location_code": "B-01",
            "product_code": "PRD002",
            "movement_type": "adjustment",
            "reference_type": "seed",
            "reference_id": 2003,
            "quantity_before": 0,
            "quantity_change": 10,
            "quantity_after": 10,
            "note": "Seed opening stock for thermal printer",
        },
        {
            "warehouse_code": "WH001",
            "location_code": "B-01",
            "product_code": "PRD002",
            "movement_type": "adjustment",
            "reference_type": "stock_check",
            "reference_id": 2103,
            "quantity_before": 10,
            "quantity_change": -4,
            "quantity_after": 6,
            "note": "Seed stock recount adjusted thermal printer quantity",
        },
        {
            "warehouse_code": "WH001",
            "location_code": "C-01",
            "product_code": "PRD003",
            "movement_type": "adjustment",
            "reference_type": "seed",
            "reference_id": 2004,
            "quantity_before": 0,
            "quantity_change": 120,
            "quantity_after": 120,
            "note": "Seed opening stock for barcode labels",
        },
        {
            "warehouse_code": "WH002",
            "location_code": "B-01",
            "product_code": "PRD003",
            "movement_type": "adjustment",
            "reference_type": "seed",
            "reference_id": 2005,
            "quantity_before": 0,
            "quantity_change": 60,
            "quantity_after": 60,
            "note": "Seed opening stock for barcode labels at south warehouse",
        },
        {
            "warehouse_code": "WH002",
            "location_code": "C-01",
            "product_code": "PRD004",
            "movement_type": "adjustment",
            "reference_type": "seed",
            "reference_id": 2006,
            "quantity_before": 0,
            "quantity_change": 14,
            "quantity_after": 14,
            "note": "Seed opening stock for warehouse radios",
        },
        {
            "warehouse_code": "WH001",
            "location_code": "B-01",
            "product_code": "PRD005",
            "movement_type": "adjustment",
            "reference_type": "seed",
            "reference_id": 2007,
            "quantity_before": 0,
            "quantity_change": 6,
            "quantity_after": 6,
            "note": "Seed opening stock for mini trolleys",
        },
        {
            "warehouse_code": "WH001",
            "location_code": "B-01",
            "product_code": "PRD005",
            "movement_type": "adjustment",
            "reference_type": "stock_check",
            "reference_id": 2107,
            "quantity_before": 6,
            "quantity_change": -2,
            "quantity_after": 4,
            "note": "Seed stock recount adjusted trolley quantity",
        },
        {
            "warehouse_code": "WH002",
            "location_code": "A-01",
            "product_code": "PRD006",
            "movement_type": "adjustment",
            "reference_type": "seed",
            "reference_id": 2008,
            "quantity_before": 0,
            "quantity_change": 48,
            "quantity_after": 48,
            "note": "Seed opening stock for pallet wrap",
        },
        {
            "warehouse_code": "WH001",
            "location_code": "C-01",
            "product_code": "PRD007",
            "movement_type": "adjustment",
            "reference_type": "seed",
            "reference_id": 2009,
            "quantity_before": 0,
            "quantity_change": 30,
            "quantity_after": 30,
            "note": "Seed opening stock for warehouse paper",
        },
    ]
    for item in movements:
        warehouse = warehouse_lookup[item["warehouse_code"]]
        location = location_lookup[(item["warehouse_code"], item["location_code"])]
        product = product_lookup[item["product_code"]]
        movement = InventoryMovement.query.filter_by(
            warehouse_id=warehouse.id,
            location_id=location.id,
            product_id=product.id,
            movement_type=item["movement_type"],
            reference_type=item["reference_type"],
            reference_id=item["reference_id"],
        ).first()
        if movement:
            continue
        db.session.add(
            InventoryMovement(
                warehouse_id=warehouse.id,
                location_id=location.id,
                product_id=product.id,
                movement_type=item["movement_type"],
                reference_type=item["reference_type"],
                reference_id=item["reference_id"],
                quantity_before=item["quantity_before"],
                quantity_change=item["quantity_change"],
                quantity_after=item["quantity_after"],
                performed_by=manager_user.id if manager_user else None,
                note=item["note"],
            )
        )


def seed_import_receipt_demo():
    if ImportReceipt.query.filter_by(receipt_code="IMP-DEMO-001").first():
        return

    manager_user = User.query.filter_by(username="manager").first()
    warehouse = Warehouse.query.filter_by(warehouse_code="WH001").first()
    supplier = Supplier.query.filter_by(supplier_code="SUP001").first()
    printer = Product.query.filter_by(product_code="PRD002").first()
    paper = Product.query.filter_by(product_code="PRD007").first()
    printer_location = WarehouseLocation.query.filter_by(
        warehouse_id=warehouse.id if warehouse else None,
        location_code="B-01",
    ).first()
    paper_location = WarehouseLocation.query.filter_by(
        warehouse_id=warehouse.id if warehouse else None,
        location_code="C-01",
    ).first()

    if not all([manager_user, warehouse, supplier, printer, paper, printer_location, paper_location]):
        return

    receipt = ImportReceipt(
        receipt_code="IMP-DEMO-001",
        warehouse_id=warehouse.id,
        supplier_id=supplier.id,
        created_by=manager_user.id,
        status="draft",
        note="Phieu nhap nhap de demo buoc xac nhan tang ton kho.",
    )
    receipt.details.append(
        ImportReceiptDetail(
            product_id=printer.id,
            location_id=printer_location.id,
            quantity=5,
        )
    )
    receipt.details.append(
        ImportReceiptDetail(
            product_id=paper.id,
            location_id=paper_location.id,
            quantity=20,
        )
    )
    db.session.add(receipt)


def seed_export_receipt_demo():
    if ExportReceipt.query.filter_by(receipt_code="EXP-DEMO-001").first():
        return

    manager_user = User.query.filter_by(username="manager").first()
    warehouse = Warehouse.query.filter_by(warehouse_code="WH001").first()
    customer = Customer.query.filter_by(customer_code="CUS001").first()
    scanner = Product.query.filter_by(product_code="PRD001").first()
    labels = Product.query.filter_by(product_code="PRD003").first()
    scanner_location = WarehouseLocation.query.filter_by(
        warehouse_id=warehouse.id if warehouse else None,
        location_code="A-01",
    ).first()
    label_location = WarehouseLocation.query.filter_by(
        warehouse_id=warehouse.id if warehouse else None,
        location_code="C-01",
    ).first()

    if not all([manager_user, warehouse, customer, scanner, labels, scanner_location, label_location]):
        return

    receipt = ExportReceipt(
        receipt_code="EXP-DEMO-001",
        warehouse_id=warehouse.id,
        customer_id=customer.id,
        created_by=manager_user.id,
        status="draft",
        note="Phieu xuat nhap de demo buoc xac nhan tru ton kho.",
    )
    receipt.details.append(
        ExportReceiptDetail(
            product_id=scanner.id,
            location_id=scanner_location.id,
            quantity=2,
        )
    )
    receipt.details.append(
        ExportReceiptDetail(
            product_id=labels.id,
            location_id=label_location.id,
            quantity=15,
        )
    )
    db.session.add(receipt)


def seed_stock_transfer_demo():
    if StockTransfer.query.filter_by(transfer_code="TRF-DEMO-001").first():
        return

    manager_user = User.query.filter_by(username="manager").first()
    source_warehouse = Warehouse.query.filter_by(warehouse_code="WH001").first()
    target_warehouse = Warehouse.query.filter_by(warehouse_code="WH002").first()
    scanner = Product.query.filter_by(product_code="PRD001").first()
    source_location = WarehouseLocation.query.filter_by(
        warehouse_id=source_warehouse.id if source_warehouse else None,
        location_code="A-01",
    ).first()
    target_location = WarehouseLocation.query.filter_by(
        warehouse_id=target_warehouse.id if target_warehouse else None,
        location_code="A-01",
    ).first()

    if not all([manager_user, source_warehouse, target_warehouse, scanner, source_location, target_location]):
        return

    transfer = StockTransfer(
        transfer_code="TRF-DEMO-001",
        source_warehouse_id=source_warehouse.id,
        target_warehouse_id=target_warehouse.id,
        created_by=manager_user.id,
        status="draft",
        note="Phieu dieu chuyen nhap de demo giam kho nguon va tang kho dich.",
    )
    transfer.details.append(
        StockTransferDetail(
            product_id=scanner.id,
            source_location_id=source_location.id,
            target_location_id=target_location.id,
            quantity=3,
        )
    )
    db.session.add(transfer)


def seed_stocktake_demo():
    if Stocktake.query.filter_by(stocktake_code="STK-DEMO-001").first():
        return

    manager_user = User.query.filter_by(username="manager").first()
    warehouse = Warehouse.query.filter_by(warehouse_code="WH001").first()
    if not manager_user or not warehouse:
        return

    printer = Product.query.filter_by(product_code="PRD002").first()
    trolley = Product.query.filter_by(product_code="PRD005").first()
    printer_location = WarehouseLocation.query.filter_by(
        warehouse_id=warehouse.id,
        location_code="B-01",
    ).first()
    trolley_location = WarehouseLocation.query.filter_by(
        warehouse_id=warehouse.id,
        location_code="B-01",
    ).first()
    if not printer or not trolley or not printer_location or not trolley_location:
        return

    printer_inventory = Inventory.query.filter_by(
        warehouse_id=warehouse.id,
        product_id=printer.id,
        location_id=printer_location.id,
    ).first()
    trolley_inventory = Inventory.query.filter_by(
        warehouse_id=warehouse.id,
        product_id=trolley.id,
        location_id=trolley_location.id,
    ).first()

    stocktake = Stocktake(
        stocktake_code="STK-DEMO-001",
        warehouse_id=warehouse.id,
        created_by=manager_user.id,
        status="draft",
        note="Kiem ke nhap de demo chenh lech ton kho truoc khi xac nhan.",
    )
    stocktake.details = [
        StocktakeDetail(
            product_id=printer.id,
            location_id=printer_location.id,
            system_quantity=float(printer_inventory.quantity if printer_inventory else 0),
            actual_quantity=7,
            difference_quantity=7 - float(printer_inventory.quantity if printer_inventory else 0),
            note="Thuc te con 7 may in nhiet sau khi kiem dem lai.",
        ),
        StocktakeDetail(
            product_id=trolley.id,
            location_id=trolley_location.id,
            system_quantity=float(trolley_inventory.quantity if trolley_inventory else 0),
            actual_quantity=3,
            difference_quantity=3 - float(trolley_inventory.quantity if trolley_inventory else 0),
            note="Mot xe day dang bao tri nen chua tinh vao ton thuc te.",
        ),
    ]
    db.session.add(stocktake)


def seed_shipment_demo():
    if Shipment.query.filter_by(shipment_code="SHP-DEMO-001").first():
        return

    manager_user = User.query.filter_by(username="manager").first()
    shipper_user = User.query.filter_by(username="shipper").first()
    warehouse = Warehouse.query.filter_by(warehouse_code="WH002").first()
    customer = Customer.query.filter_by(customer_code="CUS002").first()
    handheld = Product.query.filter_by(product_code="PRD006").first()
    handheld_location = WarehouseLocation.query.filter_by(
        warehouse_id=warehouse.id if warehouse else None,
        location_code="A-01",
    ).first()

    if not all([manager_user, shipper_user, warehouse, customer, handheld, handheld_location]):
        return

    receipt = ExportReceipt.query.filter_by(receipt_code="EXP-SHP-001").first()
    if not receipt:
        receipt = ExportReceipt(
            receipt_code="EXP-SHP-001",
            warehouse_id=warehouse.id,
            customer_id=customer.id,
            created_by=manager_user.id,
            status="draft",
            note="Phieu xuat da xac nhan de mo luong shipment toi thieu.",
        )
        receipt.details.append(
            ExportReceiptDetail(
                product_id=handheld.id,
                location_id=handheld_location.id,
                quantity=2,
            )
        )
        db.session.add(receipt)
        db.session.flush()
        confirm_export_receipt(receipt, manager_user.id)

    shipment = Shipment(
        shipment_code="SHP-DEMO-001",
        export_receipt_id=receipt.id,
        shipper_id=shipper_user.id,
        created_by=manager_user.id,
        status="assigned",
        note="Shipment demo da giao cho shipper de tiep tuc Module 7.",
        assigned_at=utc_now(),
    )
    db.session.add(shipment)


def seed_invoice_demo():
    if Invoice.query.filter_by(invoice_code="INV-DEMO-001").first():
        return

    manager_user = User.query.filter_by(username="manager").first()
    bank_account = BankAccount.query.filter_by(account_number="0123456789").first()
    receipt = ExportReceipt.query.filter_by(receipt_code="EXP-SHP-001").first()

    if not all([manager_user, receipt, receipt.customer]):
        return

    if receipt.invoice:
        return

    invoice = Invoice(
        invoice_code="INV-DEMO-001",
        export_receipt_id=receipt.id,
        customer_id=receipt.customer_id,
        bank_account_id=bank_account.id if bank_account and bank_account.status == "active" else None,
        created_by=manager_user.id,
        status="unpaid",
        note="Hoa don demo tao tu phieu xuat da xac nhan de mo Module 8 toi thieu.",
        issued_at=utc_now(),
        total_amount=0,
    )
    db.session.add(invoice)
    db.session.flush()

    total_amount = 0.0
    for index, detail in enumerate(receipt.details, start=1):
        unit_price = float(1500000 if index == 1 else 120000)
        line_total = float(detail.quantity) * unit_price
        total_amount += line_total
        invoice.details.append(
            InvoiceDetail(
                export_receipt_detail_id=detail.id,
                product_id=detail.product_id,
                location_id=detail.location_id,
                quantity=float(detail.quantity),
                unit_price=unit_price,
                line_total=line_total,
            )
        )

    invoice.total_amount = total_amount


def seed_tasks_notifications_demo():
    if InternalTask.query.filter_by(task_code="TSK-DEMO-001").first():
        return

    manager_user = User.query.filter_by(username="manager").first()
    staff_user = User.query.filter_by(username="staff").first()
    accountant_user = User.query.filter_by(username="accountant").first()
    shipper_user = User.query.filter_by(username="shipper").first()

    if not manager_user or not staff_user:
        return

    task = InternalTask(
        task_code="TSK-DEMO-001",
        title="Kiểm tra lại tồn thấp tại Kho Trung Tâm",
        description="Ưu tiên kiểm tra các dòng tồn thấp trước ca xuất hàng chiều.",
        assigned_to_id=staff_user.id,
        created_by=manager_user.id,
        status="todo",
        priority="high",
        due_at=utc_now(),
    )
    db.session.add(task)
    db.session.flush()

    notifications = [
        Notification(
            sender_id=manager_user.id,
            receiver_id=staff_user.id,
            title="Công việc mới TSK-DEMO-001",
            content=task.title,
            type="task",
        ),
    ]
    if accountant_user:
        notifications.append(
            Notification(
                sender_id=manager_user.id,
                receiver_id=accountant_user.id,
                title="Nhắc kiểm tra hóa đơn demo",
                content="Có hóa đơn demo cần kiểm tra trạng thái thanh toán.",
                type="payment",
            )
        )
    if shipper_user:
        notifications.append(
            Notification(
                sender_id=manager_user.id,
                receiver_id=shipper_user.id,
                title="Nhắc cập nhật vận chuyển",
                content="Vui lòng cập nhật trạng thái shipment được giao trong ca hôm nay.",
                type="shipment",
            )
        )
    db.session.add_all(notifications)


def seed_chat_demo():
    manager_user = User.query.filter_by(username="manager").first()
    staff_user = User.query.filter_by(username="staff").first()
    if not manager_user or not staff_user:
        return

    existing_conversation = (
        Conversation.query.join(ConversationParticipant)
        .filter(ConversationParticipant.user_id == manager_user.id)
        .all()
    )
    for conversation in existing_conversation:
        participant_ids = {participant.user_id for participant in conversation.participants}
        if participant_ids == {manager_user.id, staff_user.id}:
            return

    conversation = Conversation(conversation_type="direct")
    conversation.participants = [
        ConversationParticipant(user_id=manager_user.id),
        ConversationParticipant(user_id=staff_user.id),
    ]
    db.session.add(conversation)
    db.session.flush()

    db.session.add_all(
        [
            Message(
                conversation_id=conversation.id,
                sender_id=manager_user.id,
                content="Nhờ bạn kiểm tra nhanh các dòng tồn thấp trước ca xuất hàng chiều.",
                sent_at=utc_now(),
            ),
            Message(
                conversation_id=conversation.id,
                sender_id=staff_user.id,
                content="Em đã nhận, sẽ đối chiếu ở màn Tồn kho và phản hồi lại sau khi kiểm kê.",
                sent_at=utc_now(),
            ),
        ]
    )


def seed_all():
    seed_roles_and_permissions()
    seed_default_users()
    seed_default_employees()
    seed_catalogs()
    seed_inventory_demo()
    seed_import_receipt_demo()
    seed_export_receipt_demo()
    seed_stock_transfer_demo()
    seed_stocktake_demo()
    seed_shipment_demo()
    seed_invoice_demo()
    seed_tasks_notifications_demo()
    seed_chat_demo()
    db.session.commit()
