from __future__ import annotations

import os

from flask import Flask, jsonify
from flask_migrate import upgrade
from marshmallow import ValidationError

from .config import Config, TestConfig
from .extensions import bcrypt, cors, db, jwt, migrate, socketio
from .routes import register_blueprints
from .seed import seed_all


def create_app(config_object=None):
    app = Flask(__name__)
    config_name = config_object or os.getenv("FLASK_CONFIG", "default")
    if config_name == "test":
        app.config.from_object(TestConfig)
    elif isinstance(config_name, str) and config_name != "default":
        app.config.from_object(config_name)
    else:
        app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    bcrypt.init_app(app)
    cors.init_app(
        app,
        resources={r"/*": {"origins": [app.config["FRONTEND_URL"], "*"]}},
        supports_credentials=True,
    )
    socketio.init_app(
        app,
        cors_allowed_origins=app.config["SOCKETIO_CORS_ALLOWED_ORIGINS"],
    )

    register_blueprints(app)

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    @app.cli.command("init-db")
    def init_db_command():
        upgrade()
        seed_all()
        print("Database upgraded and seeded.")

    @app.cli.command("seed-db")
    def seed_db_command():
        seed_all()
        print("Database seeded.")

    @app.errorhandler(400)
    @app.errorhandler(401)
    @app.errorhandler(403)
    @app.errorhandler(404)
    @app.errorhandler(409)
    @app.errorhandler(422)
    @app.errorhandler(ValidationError)
    @app.errorhandler(500)
    def handle_error(error):
        code = getattr(error, "code", 500)
        if isinstance(error, ValidationError):
            return jsonify({"message": error.normalized_messages()}), 422
        return jsonify({"message": getattr(error, "description", str(error))}), code

    return app
