import os


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "warehouse-secret")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "warehouse-jwt-secret")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "sqlite:///warehouse.db",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
    SOCKETIO_CORS_ALLOWED_ORIGINS = os.getenv(
        "SOCKETIO_CORS_ALLOWED_ORIGINS",
        FRONTEND_URL,
    )
    DEFAULT_PASSWORD = os.getenv("DEFAULT_PASSWORD", "Password123!")


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    JWT_SECRET_KEY = "test-secret-key-with-32-plus-characters"
    SECRET_KEY = "test-secret-key-with-32-plus-characters"
