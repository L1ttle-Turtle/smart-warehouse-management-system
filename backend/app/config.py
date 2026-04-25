import os


def get_runtime_config():
    return {
        "SECRET_KEY": os.getenv(
            "SECRET_KEY",
            "warehouse-secret-key-with-32-plus-characters",
        ),
        "JWT_SECRET_KEY": os.getenv(
            "JWT_SECRET_KEY",
            "warehouse-jwt-secret-key-with-32-plus-characters",
        ),
        "SQLALCHEMY_DATABASE_URI": os.getenv(
            "DATABASE_URL",
            "sqlite:///warehouse.db",
        ),
        "FRONTEND_URL": os.getenv("FRONTEND_URL", "http://localhost:5173"),
        "SOCKETIO_CORS_ALLOWED_ORIGINS": os.getenv(
            "SOCKETIO_CORS_ALLOWED_ORIGINS",
            os.getenv("FRONTEND_URL", "http://localhost:5173"),
        ),
        "DEFAULT_PASSWORD": os.getenv("DEFAULT_PASSWORD", "Password123!"),
    }


class Config:
    SECRET_KEY = "warehouse-secret-key-with-32-plus-characters"
    JWT_SECRET_KEY = "warehouse-jwt-secret-key-with-32-plus-characters"
    SQLALCHEMY_DATABASE_URI = "sqlite:///warehouse.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    FRONTEND_URL = "http://localhost:5173"
    SOCKETIO_CORS_ALLOWED_ORIGINS = FRONTEND_URL
    DEFAULT_PASSWORD = "Password123!"


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    JWT_SECRET_KEY = "test-secret-key-with-32-plus-characters"
    SECRET_KEY = "test-secret-key-with-32-plus-characters"
