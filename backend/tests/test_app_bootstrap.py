from app import create_app


def test_create_app_loads_runtime_env_file(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "DATABASE_URL=sqlite:///runtime-bootstrap.db",
                "SECRET_KEY=runtime-secret-key-with-32-plus-characters",
                "JWT_SECRET_KEY=runtime-jwt-secret-key-with-32-plus-characters",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    monkeypatch.setenv("WAREHOUSE_ENV_FILE", str(env_file))

    app = create_app()

    assert app.config["SQLALCHEMY_DATABASE_URI"] == "sqlite:///runtime-bootstrap.db"
    assert app.config["SECRET_KEY"] == "runtime-secret-key-with-32-plus-characters"
    assert app.config["JWT_SECRET_KEY"] == "runtime-jwt-secret-key-with-32-plus-characters"
