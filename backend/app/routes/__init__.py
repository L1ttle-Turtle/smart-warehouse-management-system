from .catalogs import catalogs_bp
from .auth import auth_bp
from .insights import insights_bp
from .inventory import inventory_bp
from .people import people_bp
from .products import products_bp
from .rbac import rbac_bp


def register_blueprints(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(catalogs_bp)
    app.register_blueprint(insights_bp)
    app.register_blueprint(inventory_bp, url_prefix="/inventory")
    app.register_blueprint(people_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(rbac_bp)
