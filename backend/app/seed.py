from __future__ import annotations

from .constants import DEFAULT_ROLE_PASSWORDS, RESOURCE_PERMISSIONS, ROLE_PERMISSION_MAP
from .extensions import db
from .models import (
    BankAccount,
    BankTransactionLog,
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
    Payment,
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
from .services.inventory import (
    confirm_export_receipt,
    confirm_import_receipt,
    confirm_stock_transfer,
    confirm_stocktake,
)
from .utils import utc_now


def _get_or_create(model, lookup, defaults=None):
    item = model.query.filter_by(**lookup).first()
    data = defaults or {}
    if item:
        for key, value in data.items():
            setattr(item, key, value)
        return item, False

    create_data = dict(data)
    create_data.update(lookup)
    item = model(**create_data)
    db.session.add(item)
    db.session.flush()
    return item, True


def _warehouse_by_code(warehouse_code):
    return Warehouse.query.filter_by(warehouse_code=warehouse_code).first()


def _location_by_code(warehouse_code, location_code):
    warehouse = _warehouse_by_code(warehouse_code)
    if not warehouse:
        return None
    return WarehouseLocation.query.filter_by(
        warehouse_id=warehouse.id,
        location_code=location_code,
    ).first()


def _product_by_code(product_code):
    return Product.query.filter_by(product_code=product_code).first()


def _sync_product_quantity_totals():
    for product in Product.query.all():
        total = (
            db.session.query(db.func.coalesce(db.func.sum(Inventory.quantity), 0))
            .filter(Inventory.product_id == product.id)
            .scalar()
        )
        product.quantity_total = float(total or 0)


def _ensure_inventory_row(warehouse_code, location_code, product_code, quantity, reference_id, note):
    manager_user = User.query.filter_by(username="manager").first()
    warehouse = _warehouse_by_code(warehouse_code)
    location = _location_by_code(warehouse_code, location_code)
    product = _product_by_code(product_code)
    if not all([warehouse, location, product]):
        return

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
            quantity=quantity,
        )
        db.session.add(row)
    else:
        row.quantity = quantity

    movement = InventoryMovement.query.filter_by(
        warehouse_id=warehouse.id,
        location_id=location.id,
        product_id=product.id,
        movement_type="adjustment",
        reference_type="seed_dense",
        reference_id=reference_id,
    ).first()
    if not movement:
        db.session.add(
            InventoryMovement(
                warehouse_id=warehouse.id,
                location_id=location.id,
                product_id=product.id,
                movement_type="adjustment",
                reference_type="seed_dense",
                reference_id=reference_id,
                quantity_before=0,
                quantity_change=quantity,
                quantity_after=quantity,
                performed_by=manager_user.id if manager_user else None,
                note=note,
            )
        )


def _direct_conversation_for(user_ids):
    user_id_set = set(user_ids)
    conversations = (
        Conversation.query.join(ConversationParticipant)
        .filter(ConversationParticipant.user_id.in_(user_id_set))
        .all()
    )
    for conversation in conversations:
        participant_ids = {participant.user_id for participant in conversation.participants}
        if participant_ids == user_id_set:
            return conversation
    return None


def _ensure_direct_conversation(usernames, messages):
    users = [User.query.filter_by(username=username).first() for username in usernames]
    if not all(users):
        return

    conversation = _direct_conversation_for([user.id for user in users])
    if not conversation:
        conversation = Conversation(conversation_type="direct")
        conversation.participants = [
            ConversationParticipant(user_id=user.id)
            for user in users
        ]
        db.session.add(conversation)
        db.session.flush()

    user_lookup = {user.username: user for user in users}
    for item in messages:
        sender = user_lookup.get(item["sender"])
        if not sender:
            continue
        existing_message = Message.query.filter_by(
            conversation_id=conversation.id,
            sender_id=sender.id,
            content=item["content"],
        ).first()
        if existing_message:
            continue
        db.session.add(
            Message(
                conversation_id=conversation.id,
                sender_id=sender.id,
                content=item["content"],
                sent_at=utc_now(),
            )
        )


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


def seed_dense_catalogs():
    categories = [
        {"category_name": "Thiet bi kho", "description": "Thiet bi van hanh va kiem soat trong kho."},
        {"category_name": "Vat tu ve sinh", "description": "Vat tu ve sinh, bao tri thiet bi kho."},
        {"category_name": "An toan lao dong", "description": "Do bao ho va dung cu an toan cho nhan su kho."},
        {"category_name": "Linh kien thay the", "description": "Linh kien thay the cho thiet bi kho."},
    ]
    for item in categories:
        _get_or_create(
            Category,
            {"category_name": item["category_name"]},
            {"description": item["description"]},
        )
    db.session.flush()

    suppliers = [
        {
            "supplier_code": "SUP005",
            "supplier_name": "Nam Viet Packaging",
            "email": "namviet@supplier.local",
            "phone": "0905555555",
            "address": "19 Truong Chinh, Ha Noi",
            "status": "active",
        },
        {
            "supplier_code": "SUP006",
            "supplier_name": "Kho Van Hoa Phat",
            "email": "hoaphat@supplier.local",
            "phone": "0906666666",
            "address": "KCN Tan Tao, HCM",
            "status": "active",
        },
        {
            "supplier_code": "SUP007",
            "supplier_name": "Viet Safety",
            "email": "safety@supplier.local",
            "phone": "0907777777",
            "address": "77 Dien Bien Phu, Binh Duong",
            "status": "active",
        },
        {
            "supplier_code": "SUP008",
            "supplier_name": "BlueTech Device",
            "email": "bluetech@supplier.local",
            "phone": "0908888888",
            "address": "05 Nguyen Van Linh, Da Nang",
            "status": "active",
        },
        {
            "supplier_code": "SUP009",
            "supplier_name": "Dai Tin Spare Parts",
            "email": "daitin@supplier.local",
            "phone": "0909999999",
            "address": "32 Tran Nao, HCM",
            "status": "inactive",
        },
        {
            "supplier_code": "SUP010",
            "supplier_name": "GreenClean Warehouse",
            "email": "greenclean@supplier.local",
            "phone": "0901010101",
            "address": "10 Le Duan, Hai Phong",
            "status": "active",
        },
    ]
    for item in suppliers:
        _get_or_create(Supplier, {"supplier_code": item["supplier_code"]}, item)

    customers = [
        {
            "customer_code": "CUS005",
            "customer_name": "Chuoi cua hang CityMart",
            "email": "citymart@customer.local",
            "phone": "0915555555",
            "address": "88 Pham Van Dong, Ha Noi",
            "status": "active",
        },
        {
            "customer_code": "CUS006",
            "customer_name": "Nha may Tan Phu",
            "email": "tanphu@customer.local",
            "phone": "0916666666",
            "address": "KCN Song Than, Binh Duong",
            "status": "active",
        },
        {
            "customer_code": "CUS007",
            "customer_name": "Trung tam phan phoi An Hoa",
            "email": "anhoa@customer.local",
            "phone": "0917777777",
            "address": "16 Nguyen Tat Thanh, Da Nang",
            "status": "active",
        },
        {
            "customer_code": "CUS008",
            "customer_name": "Dai ly Gia Bao",
            "email": "giabao@customer.local",
            "phone": "0918888888",
            "address": "41 Ly Thuong Kiet, Hue",
            "status": "inactive",
        },
        {
            "customer_code": "CUS009",
            "customer_name": "Phong mua hang Sai Gon",
            "email": "muahangsg@customer.local",
            "phone": "0919999999",
            "address": "23 Nguyen Huu Canh, HCM",
            "status": "active",
        },
        {
            "customer_code": "CUS010",
            "customer_name": "Kho trung chuyen Mekong",
            "email": "mekonghub@customer.local",
            "phone": "0910101010",
            "address": "Lo B2 KCN Tra Noc, Can Tho",
            "status": "active",
        },
    ]
    for item in customers:
        _get_or_create(Customer, {"customer_code": item["customer_code"]}, item)

    bank_accounts = [
        {
            "bank_name": "MB Bank",
            "account_number": "4455667788",
            "account_holder": "Cong ty Kho Thong Minh",
            "branch": "Chi nhanh Bac Ninh",
            "status": "active",
        },
        {
            "bank_name": "VPBank",
            "account_number": "2233445566",
            "account_holder": "Cong ty Kho Thong Minh",
            "branch": "Chi nhanh Binh Duong",
            "status": "active",
        },
    ]
    for item in bank_accounts:
        _get_or_create(BankAccount, {"account_number": item["account_number"]}, item)


def seed_dense_inventory_demo():
    category_lookup = {
        category.category_name: category
        for category in Category.query.order_by(Category.id.asc()).all()
    }

    warehouses = [
        {
            "warehouse_code": "WH003",
            "warehouse_name": "Kho Mien Bac",
            "address": "KCN Yen Phong, Bac Ninh",
            "status": "active",
            "locations": [
                {"location_code": "A-01", "location_name": "Day A - Hang nhanh", "status": "active"},
                {"location_code": "A-02", "location_name": "Day A - Hang du tru", "status": "active"},
                {"location_code": "B-01", "location_name": "Day B - Vat tu an toan", "status": "active"},
                {"location_code": "QC-01", "location_name": "Khu kiem tra chat luong", "status": "active"},
            ],
        },
        {
            "warehouse_code": "WH004",
            "warehouse_name": "Kho Hang Loi Va Bao Hanh",
            "address": "Lo R2 KCN Tan Binh, HCM",
            "status": "active",
            "locations": [
                {"location_code": "RET-01", "location_name": "Hang doi kiem tra", "status": "active"},
                {"location_code": "RET-02", "location_name": "Hang cho xu ly", "status": "active"},
                {"location_code": "HOLD-01", "location_name": "Hang tam giu", "status": "active"},
            ],
        },
    ]
    for warehouse_item in warehouses:
        warehouse, _ = _get_or_create(
            Warehouse,
            {"warehouse_code": warehouse_item["warehouse_code"]},
            {
                "warehouse_name": warehouse_item["warehouse_name"],
                "address": warehouse_item["address"],
                "status": warehouse_item["status"],
            },
        )
        for location_item in warehouse_item["locations"]:
            _get_or_create(
                WarehouseLocation,
                {
                    "warehouse_id": warehouse.id,
                    "location_code": location_item["location_code"],
                },
                {
                    "location_name": location_item["location_name"],
                    "status": location_item["status"],
                },
            )
    db.session.flush()

    products = [
        ("PRD008", "Camera quet ma QR cong nghiep", "Thiet bi kho", 6, "Thiet bi doc QR cho cong doan nhap xuat hang."),
        ("PRD009", "Pallet nhua xanh", "Phu kien kho", 25, "Pallet nhua dung cho khu hang nhanh."),
        ("PRD010", "Bang keo trong 48mm", "Dong goi", 120, "Bang keo dong thung carton so luong lon."),
        ("PRD011", "Thung carton size M", "Dong goi", 200, "Thung carton size M cho don hang ban le."),
        ("PRD012", "Ao phan quang kho", "An toan lao dong", 30, "Ao phan quang cho nhan su lam ca dem."),
        ("PRD013", "Gang tay chong cat", "An toan lao dong", 80, "Gang tay bao ho khi xu ly kien hang sac canh."),
        ("PRD014", "Ke sat lap rap 5 tang", "Phu kien kho", 10, "Ke sat lap rap cho khu hang nho le."),
        ("PRD015", "Pin thay the may quet", "Linh kien thay the", 25, "Pin du phong cho may quet ma vach."),
        ("PRD016", "Dung dich ve sinh dau in", "Vat tu ve sinh", 15, "Dung dich ve sinh dau in tem ma van."),
        ("PRD017", "Seal niem phong container", "Dong goi", 500, "Seal nhua danh so cho container va xe tai."),
        ("PRD018", "Bo router wifi kho", "Dien tu", 4, "Router wifi phu song khu vuc kho hang."),
        ("PRD019", "Xe nang tay 2.5 tan", "Phu kien kho", 3, "Xe nang tay phuc vu di chuyen pallet nang."),
        ("PRD020", "May tinh bang kiem kho", "Dien tu", 8, "May tinh bang cho nhan vien kiem ke di dong."),
    ]
    for product_code, product_name, category_name, min_stock, description in products:
        category = category_lookup.get(category_name)
        _get_or_create(
            Product,
            {"product_code": product_code},
            {
                "product_name": product_name,
                "category_id": category.id if category else None,
                "min_stock": min_stock,
                "status": "active",
                "description": description,
            },
        )
    db.session.flush()

    inventory_rows = [
        ("WH001", "A-01", "PRD008", 7, 3001, "Seed dense stock for QR camera at central warehouse"),
        ("WH001", "C-01", "PRD010", 180, 3002, "Seed dense stock for packing tape at central warehouse"),
        ("WH001", "C-01", "PRD011", 260, 3003, "Seed dense stock for carton boxes at central warehouse"),
        ("WH001", "B-01", "PRD012", 18, 3004, "Seed low stock safety vest at central warehouse"),
        ("WH001", "B-01", "PRD015", 12, 3005, "Seed low stock scanner batteries at central warehouse"),
        ("WH002", "A-01", "PRD008", 12, 3006, "Seed QR camera at south warehouse"),
        ("WH002", "B-01", "PRD009", 42, 3007, "Seed pallets at south warehouse"),
        ("WH002", "C-01", "PRD014", 14, 3008, "Seed shelving at south warehouse"),
        ("WH002", "C-01", "PRD017", 820, 3009, "Seed container seals at south warehouse"),
        ("WH003", "A-01", "PRD009", 70, 3010, "Seed pallets for north fast lane"),
        ("WH003", "A-01", "PRD012", 36, 3011, "Seed safety vests for north warehouse"),
        ("WH003", "A-02", "PRD010", 320, 3012, "Seed packing tape reserve at north warehouse"),
        ("WH003", "A-02", "PRD011", 450, 3013, "Seed carton reserve at north warehouse"),
        ("WH003", "B-01", "PRD013", 95, 3014, "Seed cut-resistant gloves at north warehouse"),
        ("WH003", "B-01", "PRD015", 28, 3015, "Seed replacement batteries at north warehouse"),
        ("WH003", "QC-01", "PRD016", 0, 3016, "Seed out-of-stock printer cleaning liquid"),
        ("WH003", "QC-01", "PRD018", 3, 3017, "Seed low stock warehouse routers"),
        ("WH004", "RET-01", "PRD001", 2, 3018, "Seed returned barcode scanners awaiting check"),
        ("WH004", "RET-01", "PRD002", 1, 3019, "Seed returned thermal printer awaiting check"),
        ("WH004", "RET-02", "PRD019", 2, 3020, "Seed low stock pallet truck in warranty area"),
        ("WH004", "HOLD-01", "PRD020", 0, 3021, "Seed out-of-stock inventory tablets in hold area"),
    ]
    for warehouse_code, location_code, product_code, quantity, reference_id, note in inventory_rows:
        _ensure_inventory_row(
            warehouse_code,
            location_code,
            product_code,
            quantity,
            reference_id,
            note,
        )
    _sync_product_quantity_totals()


def _add_import_receipt(code, warehouse_code, supplier_code, status, details, note):
    if ImportReceipt.query.filter_by(receipt_code=code).first():
        return

    manager_user = User.query.filter_by(username="manager").first()
    warehouse = _warehouse_by_code(warehouse_code)
    supplier = Supplier.query.filter_by(supplier_code=supplier_code).first()
    if not all([manager_user, warehouse, supplier]):
        return

    receipt = ImportReceipt(
        receipt_code=code,
        warehouse_id=warehouse.id,
        supplier_id=supplier.id,
        created_by=manager_user.id,
        status="draft",
        note=note,
    )
    for item in details:
        product = _product_by_code(item["product_code"])
        location = _location_by_code(warehouse_code, item["location_code"])
        if not all([product, location]):
            return
        receipt.details.append(
            ImportReceiptDetail(
                product_id=product.id,
                location_id=location.id,
                quantity=item["quantity"],
            )
        )
    db.session.add(receipt)
    db.session.flush()

    if status == "confirmed":
        confirm_import_receipt(receipt, manager_user.id)


def _add_export_receipt(code, warehouse_code, customer_code, status, details, note):
    if ExportReceipt.query.filter_by(receipt_code=code).first():
        return

    manager_user = User.query.filter_by(username="manager").first()
    warehouse = _warehouse_by_code(warehouse_code)
    customer = Customer.query.filter_by(customer_code=customer_code).first()
    if not all([manager_user, warehouse, customer]):
        return

    receipt = ExportReceipt(
        receipt_code=code,
        warehouse_id=warehouse.id,
        customer_id=customer.id,
        created_by=manager_user.id,
        status="draft",
        note=note,
    )
    for item in details:
        product = _product_by_code(item["product_code"])
        location = _location_by_code(warehouse_code, item["location_code"])
        if not all([product, location]):
            return
        receipt.details.append(
            ExportReceiptDetail(
                product_id=product.id,
                location_id=location.id,
                quantity=item["quantity"],
            )
        )
    db.session.add(receipt)
    db.session.flush()

    if status == "confirmed":
        confirm_export_receipt(receipt, manager_user.id)


def _add_stock_transfer(code, source_warehouse_code, target_warehouse_code, status, details, note):
    if StockTransfer.query.filter_by(transfer_code=code).first():
        return

    manager_user = User.query.filter_by(username="manager").first()
    source_warehouse = _warehouse_by_code(source_warehouse_code)
    target_warehouse = _warehouse_by_code(target_warehouse_code)
    if not all([manager_user, source_warehouse, target_warehouse]):
        return

    transfer = StockTransfer(
        transfer_code=code,
        source_warehouse_id=source_warehouse.id,
        target_warehouse_id=target_warehouse.id,
        created_by=manager_user.id,
        status="draft",
        note=note,
    )
    for item in details:
        product = _product_by_code(item["product_code"])
        source_location = _location_by_code(source_warehouse_code, item["source_location_code"])
        target_location = _location_by_code(target_warehouse_code, item["target_location_code"])
        if not all([product, source_location, target_location]):
            return
        transfer.details.append(
            StockTransferDetail(
                product_id=product.id,
                source_location_id=source_location.id,
                target_location_id=target_location.id,
                quantity=item["quantity"],
            )
        )
    db.session.add(transfer)
    db.session.flush()

    if status == "confirmed":
        confirm_stock_transfer(transfer, manager_user.id)


def _add_stocktake(code, warehouse_code, status, details, note):
    if Stocktake.query.filter_by(stocktake_code=code).first():
        return

    manager_user = User.query.filter_by(username="manager").first()
    warehouse = _warehouse_by_code(warehouse_code)
    if not all([manager_user, warehouse]):
        return

    stocktake = Stocktake(
        stocktake_code=code,
        warehouse_id=warehouse.id,
        created_by=manager_user.id,
        status="draft",
        note=note,
    )
    for item in details:
        product = _product_by_code(item["product_code"])
        location = _location_by_code(warehouse_code, item["location_code"])
        if not all([product, location]):
            return
        inventory = Inventory.query.filter_by(
            warehouse_id=warehouse.id,
            product_id=product.id,
            location_id=location.id,
        ).first()
        system_quantity = float(inventory.quantity if inventory else 0)
        actual_quantity = float(item["actual_quantity"])
        stocktake.details.append(
            StocktakeDetail(
                product_id=product.id,
                location_id=location.id,
                system_quantity=system_quantity,
                actual_quantity=actual_quantity,
                difference_quantity=actual_quantity - system_quantity,
                note=item.get("note"),
            )
        )
    db.session.add(stocktake)
    db.session.flush()

    if status == "confirmed":
        confirm_stocktake(stocktake, manager_user.id)


def seed_dense_operations_demo():
    _add_import_receipt(
        "IMP-DEMO-002",
        "WH003",
        "SUP005",
        "draft",
        [
            {"product_code": "PRD010", "location_code": "A-02", "quantity": 60},
            {"product_code": "PRD011", "location_code": "A-02", "quantity": 90},
            {"product_code": "PRD013", "location_code": "B-01", "quantity": 30},
        ],
        "Phieu nhap nhap so luong lon cho kho mien Bac.",
    )
    _add_import_receipt(
        "IMP-DEMO-003",
        "WH003",
        "SUP008",
        "confirmed",
        [
            {"product_code": "PRD008", "location_code": "A-01", "quantity": 8},
            {"product_code": "PRD015", "location_code": "B-01", "quantity": 15},
        ],
        "Phieu nhap da xac nhan de demo movement tang ton.",
    )

    _add_export_receipt(
        "EXP-DEMO-002",
        "WH002",
        "CUS007",
        "draft",
        [
            {"product_code": "PRD009", "location_code": "B-01", "quantity": 12},
            {"product_code": "PRD014", "location_code": "C-01", "quantity": 2},
        ],
        "Phieu xuat nhap cho dai ly mien Trung.",
    )
    _add_export_receipt(
        "EXP-DEMO-003",
        "WH003",
        "CUS005",
        "confirmed",
        [
            {"product_code": "PRD010", "location_code": "A-02", "quantity": 30},
            {"product_code": "PRD011", "location_code": "A-02", "quantity": 60},
        ],
        "Phieu xuat da xac nhan cho chuoi cua hang CityMart.",
    )
    _add_export_receipt(
        "EXP-DEMO-004",
        "WH003",
        "CUS006",
        "confirmed",
        [
            {"product_code": "PRD012", "location_code": "A-01", "quantity": 6},
            {"product_code": "PRD013", "location_code": "B-01", "quantity": 20},
        ],
        "Phieu xuat da xac nhan cho nha may Tan Phu.",
    )

    _add_stock_transfer(
        "TRF-DEMO-002",
        "WH003",
        "WH001",
        "confirmed",
        [
            {
                "product_code": "PRD010",
                "source_location_code": "A-02",
                "target_location_code": "C-01",
                "quantity": 20,
            },
            {
                "product_code": "PRD011",
                "source_location_code": "A-02",
                "target_location_code": "C-01",
                "quantity": 40,
            },
        ],
        "Dieu chuyen da xac nhan bo sung vat tu dong goi ve kho trung tam.",
    )
    _add_stock_transfer(
        "TRF-DEMO-003",
        "WH002",
        "WH003",
        "draft",
        [
            {
                "product_code": "PRD009",
                "source_location_code": "B-01",
                "target_location_code": "A-01",
                "quantity": 15,
            }
        ],
        "Phieu dieu chuyen nhap cho pallet nhua.",
    )

    _add_stocktake(
        "STK-DEMO-002",
        "WH003",
        "draft",
        [
            {
                "product_code": "PRD010",
                "location_code": "A-02",
                "actual_quantity": 260,
                "note": "Dang doi doi chieu lai lo bang keo moi nhap.",
            },
            {
                "product_code": "PRD018",
                "location_code": "QC-01",
                "actual_quantity": 3,
                "note": "Router trong khu QC khop voi he thong.",
            },
        ],
        "Phieu kiem ke nhap nhieu dong cho kho mien Bac.",
    )
    _add_stocktake(
        "STK-DEMO-003",
        "WH004",
        "confirmed",
        [
            {
                "product_code": "PRD019",
                "location_code": "RET-02",
                "actual_quantity": 1,
                "note": "Mot xe nang tay chuyen sang bao tri ngoai.",
            },
            {
                "product_code": "PRD020",
                "location_code": "HOLD-01",
                "actual_quantity": 0,
                "note": "Chua nhan lai may tinh bang kiem kho.",
            },
        ],
        "Kiem ke da xac nhan cho khu hang loi va bao hanh.",
    )
    _sync_product_quantity_totals()


def _create_invoice_for_export(invoice_code, receipt_code, status, payment_amount=None, payment_code=None):
    accountant_user = User.query.filter_by(username="accountant").first()
    manager_user = User.query.filter_by(username="manager").first()
    bank_account = BankAccount.query.filter_by(account_number="4455667788").first()
    receipt = ExportReceipt.query.filter_by(receipt_code=receipt_code).first()
    actor_user = accountant_user or manager_user
    if not all([actor_user, receipt, receipt.customer]):
        return
    if receipt.status != "confirmed":
        return

    invoice = Invoice.query.filter_by(invoice_code=invoice_code).first()
    if not invoice:
        if receipt.invoice:
            return
        invoice = Invoice(
            invoice_code=invoice_code,
            export_receipt_id=receipt.id,
            customer_id=receipt.customer_id,
            bank_account_id=bank_account.id if bank_account and bank_account.status == "active" else None,
            created_by=actor_user.id,
            status="unpaid",
            note=f"Hoa don demo tao tu {receipt.receipt_code}.",
            issued_at=utc_now(),
            total_amount=0,
        )
        db.session.add(invoice)
        db.session.flush()

        unit_prices = {
            "PRD010": 28000,
            "PRD011": 15500,
            "PRD012": 125000,
            "PRD013": 45000,
        }
        total_amount = 0.0
        for detail in receipt.details:
            product_code = detail.product.product_code if detail.product else ""
            unit_price = float(unit_prices.get(product_code, 100000))
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
        db.session.flush()

    if payment_amount is not None and payment_code:
        payment = Payment.query.filter_by(payment_code=payment_code).first()
        if not payment:
            db.session.add(
                Payment(
                    payment_code=payment_code,
                    invoice_id=invoice.id,
                    bank_account_id=invoice.bank_account_id,
                    created_by=actor_user.id,
                    amount=float(payment_amount),
                    payment_method="bank_transfer",
                    paid_at=utc_now(),
                    note=f"Thanh toan demo cho {invoice.invoice_code}.",
                )
            )
            db.session.flush()

    paid_amount = float(
        db.session.query(db.func.coalesce(db.func.sum(Payment.amount), 0))
        .filter(Payment.invoice_id == invoice.id)
        .scalar()
        or 0
    )
    if paid_amount <= 0:
        invoice.status = "unpaid"
    elif paid_amount >= float(invoice.total_amount or 0):
        invoice.status = "paid"
    else:
        invoice.status = "partial"

    if status in {"unpaid", "partial", "paid"}:
        invoice.status = status


def seed_dense_business_demo():
    manager_user = User.query.filter_by(username="manager").first()
    shipper_user = User.query.filter_by(username="shipper").first()
    if not manager_user or not shipper_user:
        return

    shipment_specs = [
        ("SHP-DEMO-002", "EXP-DEMO-003", "in_transit", "Shipment dang giao cho CityMart."),
        ("SHP-DEMO-003", "EXP-DEMO-004", "delivered", "Shipment da giao thanh cong cho Tan Phu."),
    ]
    for shipment_code, receipt_code, status, note in shipment_specs:
        if Shipment.query.filter_by(shipment_code=shipment_code).first():
            continue
        receipt = ExportReceipt.query.filter_by(receipt_code=receipt_code).first()
        if not receipt or receipt.status != "confirmed" or receipt.shipment:
            continue
        shipment = Shipment(
            shipment_code=shipment_code,
            export_receipt_id=receipt.id,
            shipper_id=shipper_user.id,
            created_by=manager_user.id,
            status=status,
            note=note,
            assigned_at=utc_now(),
        )
        if status in {"in_transit", "delivered"}:
            shipment.in_transit_at = utc_now()
        if status == "delivered":
            shipment.delivered_at = utc_now()
        db.session.add(shipment)

    _create_invoice_for_export(
        "INV-DEMO-002",
        "EXP-DEMO-003",
        "partial",
        payment_amount=900000,
        payment_code="PAY-DEMO-001",
    )
    receipt = ExportReceipt.query.filter_by(receipt_code="EXP-DEMO-004").first()
    paid_amount = 0
    if receipt and receipt.details:
        paid_amount = (6 * 125000) + (20 * 45000)
    _create_invoice_for_export(
        "INV-DEMO-003",
        "EXP-DEMO-004",
        "paid",
        payment_amount=paid_amount,
        payment_code="PAY-DEMO-002",
    )


def seed_bank_transaction_demo():
    accountant_user = User.query.filter_by(username="accountant").first()
    manager_user = User.query.filter_by(username="manager").first()
    actor_user = accountant_user or manager_user
    bank_account = BankAccount.query.filter_by(account_number="4455667788").first()
    partially_paid_invoice = Invoice.query.filter_by(invoice_code="INV-DEMO-002").first()
    unpaid_invoice = Invoice.query.filter_by(invoice_code="INV-DEMO-001").first()
    if not actor_user:
        return

    transaction_specs = [
        {
            "transaction_code": "BNK-DEMO-001",
            "invoice": partially_paid_invoice,
            "amount": 500000,
            "description": "Khach CityMart chuyen khoan bo sung cho INV-DEMO-002",
            "status": "matched",
            "note": "Giao dich da khop hoa don, san sang doi soat trong demo.",
        },
        {
            "transaction_code": "BNK-DEMO-002",
            "invoice": None,
            "amount": 350000,
            "description": "Khoan chuyen chua co ma hoa don",
            "status": "pending",
            "note": "Can ke toan kiem tra noi dung chuyen khoan.",
        },
        {
            "transaction_code": "BNK-DEMO-003",
            "invoice": unpaid_invoice,
            "amount": 700000,
            "description": "Thanh toan mot phan hoa don INV-DEMO-001",
            "status": "matched",
            "note": "Dung de demo ghi nhan doi soat mot phan.",
        },
    ]

    for item in transaction_specs:
        if BankTransactionLog.query.filter_by(transaction_code=item["transaction_code"]).first():
            continue
        db.session.add(
            BankTransactionLog(
                transaction_code=item["transaction_code"],
                invoice_id=item["invoice"].id if item["invoice"] else None,
                bank_account_id=bank_account.id if bank_account else None,
                created_by=actor_user.id,
                amount=float(item["amount"]),
                description=item["description"],
                status=item["status"],
                received_at=utc_now(),
                note=item["note"],
            )
        )


def seed_dense_collaboration_demo():
    manager_user = User.query.filter_by(username="manager").first()
    staff_user = User.query.filter_by(username="staff").first()
    accountant_user = User.query.filter_by(username="accountant").first()
    shipper_user = User.query.filter_by(username="shipper").first()
    admin_user = User.query.filter_by(username="admin").first()
    if not manager_user:
        return

    tasks = [
        {
            "task_code": "TSK-DEMO-002",
            "title": "Doi chieu ton thap khu WH003-QC",
            "description": "Kiem tra PRD016, PRD018 truoc khi lap de xuat mua bo sung.",
            "assigned_to": staff_user,
            "status": "todo",
            "priority": "high",
        },
        {
            "task_code": "TSK-DEMO-003",
            "title": "Kiem tra thanh toan INV-DEMO-002",
            "description": "Hoa don dang thanh toan mot phan, can nhac khach thanh toan phan con lai.",
            "assigned_to": accountant_user,
            "status": "in_progress",
            "priority": "medium",
        },
        {
            "task_code": "TSK-DEMO-004",
            "title": "Cap nhat trang thai SHP-DEMO-002",
            "description": "Shipment dang giao, can cap nhat sau khi tai xe den diem giao.",
            "assigned_to": shipper_user,
            "status": "todo",
            "priority": "medium",
        },
        {
            "task_code": "TSK-DEMO-005",
            "title": "Review quyen uy quyen demo",
            "description": "Kiem tra lich su uy quyen truoc buoi bao ve.",
            "assigned_to": admin_user,
            "status": "done",
            "priority": "low",
        },
    ]
    for item in tasks:
        assignee = item["assigned_to"]
        if not assignee:
            continue
        task, created = _get_or_create(
            InternalTask,
            {"task_code": item["task_code"]},
            {
                "title": item["title"],
                "description": item["description"],
                "assigned_to_id": assignee.id,
                "created_by": manager_user.id,
                "status": item["status"],
                "priority": item["priority"],
                "due_at": utc_now(),
                "completed_at": utc_now() if item["status"] == "done" else None,
            },
        )
        if created:
            db.session.add(
                Notification(
                    sender_id=manager_user.id,
                    receiver_id=assignee.id,
                    title=f"Cong viec moi {task.task_code}",
                    content=task.title,
                    type="task",
                )
            )

    notifications = [
        (staff_user, "Can kiem tra ton thap", "PRD016 dang het hang tai kho mien Bac.", "inventory"),
        (accountant_user, "Hoa don thanh toan mot phan", "INV-DEMO-002 can theo doi phan con lai.", "payment"),
        (shipper_user, "Shipment dang giao", "SHP-DEMO-002 can cap nhat khi giao xong.", "shipment"),
    ]
    for receiver, title, content, notification_type in notifications:
        if not receiver:
            continue
        existing_notification = Notification.query.filter_by(
            receiver_id=receiver.id,
            title=title,
            content=content,
        ).first()
        if existing_notification:
            continue
        db.session.add(
            Notification(
                sender_id=manager_user.id,
                receiver_id=receiver.id,
                title=title,
                content=content,
                type=notification_type,
            )
        )

    _ensure_direct_conversation(
        ["manager", "accountant"],
        [
            {
                "sender": "manager",
                "content": "Nho ban theo doi giup hoa don INV-DEMO-002 dang thanh toan mot phan.",
            },
            {
                "sender": "accountant",
                "content": "Da ro, minh se ghi nhan them payment khi khach chuyen khoan tiep.",
            },
        ],
    )
    _ensure_direct_conversation(
        ["manager", "shipper"],
        [
            {
                "sender": "manager",
                "content": "SHP-DEMO-002 dang o trang thai dang giao, cap nhat giup khi den noi nhe.",
            },
            {
                "sender": "shipper",
                "content": "Em dang tren tuyen giao, xong se chuyen sang da giao.",
            },
        ],
    )
    _ensure_direct_conversation(
        ["staff", "shipper"],
        [
            {
                "sender": "staff",
                "content": "Phieu xuat EXP-DEMO-003 da xac nhan, hang da o khu giao nhan.",
            },
            {
                "sender": "shipper",
                "content": "Da nhan thong tin, em se kiem lai so kien truoc khi xuat xe.",
            },
        ],
    )


def seed_all():
    seed_roles_and_permissions()
    seed_default_users()
    seed_default_employees()
    seed_catalogs()
    seed_dense_catalogs()
    seed_inventory_demo()
    seed_dense_inventory_demo()
    seed_import_receipt_demo()
    seed_export_receipt_demo()
    seed_stock_transfer_demo()
    seed_stocktake_demo()
    seed_dense_operations_demo()
    seed_shipment_demo()
    seed_invoice_demo()
    seed_dense_business_demo()
    seed_bank_transaction_demo()
    seed_tasks_notifications_demo()
    seed_chat_demo()
    seed_dense_collaboration_demo()
    _sync_product_quantity_totals()
    db.session.commit()
