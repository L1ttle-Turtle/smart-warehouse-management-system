from .auth import auth_bp
from .rbac import rbac_bp


def register_blueprints(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(rbac_bp)
