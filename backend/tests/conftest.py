import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app import create_app
from app.extensions import db
from app.seed import seed_all


@pytest.fixture()
def app():
    app = create_app("test")
    with app.app_context():
        db.create_all()
        seed_all()
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def auth_headers(client):
    def factory(username="admin", password="Admin@123"):
        response = client.post(
            "/auth/login",
            json={"username": username, "password": password},
        )
        token = response.get_json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    return factory
