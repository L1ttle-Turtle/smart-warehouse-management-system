import os


DEFAULT_FRONTEND_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]


def parse_cors_origins(value):
    origins = [origin.strip() for origin in (value or "").split(",") if origin.strip()]
    for origin in DEFAULT_FRONTEND_ORIGINS:
        if origin not in origins:
            origins.append(origin)
    return origins


def get_runtime_config():
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
    socketio_origins = os.getenv("SOCKETIO_CORS_ALLOWED_ORIGINS", frontend_url)
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
        "FRONTEND_URL": frontend_url,
        "SOCKETIO_CORS_ALLOWED_ORIGINS": parse_cors_origins(socketio_origins),
        "DEFAULT_PASSWORD": os.getenv("DEFAULT_PASSWORD", "Password123!"),
    }


class Config:
    SECRET_KEY = "warehouse-secret-key-with-32-plus-characters"
    JWT_SECRET_KEY = "warehouse-jwt-secret-key-with-32-plus-characters"
    SQLALCHEMY_DATABASE_URI = "sqlite:///warehouse.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    FRONTEND_URL = "http://localhost:5173"
    SOCKETIO_CORS_ALLOWED_ORIGINS = DEFAULT_FRONTEND_ORIGINS
    DEFAULT_PASSWORD = "Password123!"


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    JWT_SECRET_KEY = "test-secret-key-with-32-plus-characters"
    SECRET_KEY = "test-secret-key-with-32-plus-characters"
