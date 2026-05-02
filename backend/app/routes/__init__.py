from .catalogs import catalogs_bp
from .auth import auth_bp
from .communications import communications_bp
from .export_receipts import export_receipts_bp
from .import_receipts import import_receipts_bp
from .insights import insights_bp
from .invoices import invoices_bp
from .inventory import inventory_bp
from .payments import payments_bp
from .people import people_bp
from .products import products_bp
from .rbac import rbac_bp
from .shipments import shipments_bp
from .stock_transfers import stock_transfers_bp
from .stocktakes import stocktakes_bp
from .warehouses import warehouses_bp


def register_blueprints(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(catalogs_bp)
    app.register_blueprint(communications_bp)
    app.register_blueprint(export_receipts_bp)
    app.register_blueprint(import_receipts_bp)
    app.register_blueprint(insights_bp)
    app.register_blueprint(invoices_bp)
    app.register_blueprint(inventory_bp, url_prefix="/inventory")
    app.register_blueprint(payments_bp)
    app.register_blueprint(people_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(rbac_bp)
    app.register_blueprint(shipments_bp)
    app.register_blueprint(stock_transfers_bp)
    app.register_blueprint(stocktakes_bp)
    app.register_blueprint(warehouses_bp)
