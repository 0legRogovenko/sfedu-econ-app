from fastapi import FastAPI
from fastapi.testclient import TestClient


def _client(**kwargs) -> TestClient:
    from src.main import app

    return TestClient(app, **kwargs)


def test_admin_requires_login():
    client = _client(follow_redirects=False)
    response = client.get("/admin/")
    # без сессии — редирект на /admin/login
    assert response.status_code in (302, 307)
    assert "/admin/login" in response.headers["location"]


def test_admin_login_with_valid_credentials():
    client = _client()
    response = client.post(
        "/admin/login",
        data={"username": "admin", "password": "test-password"},
        follow_redirects=True,
    )
    assert response.status_code == 200

    response = client.get("/admin/")
    assert response.status_code == 200


def test_admin_login_with_wrong_password_rejected():
    client = _client(follow_redirects=False)
    client.post(
        "/admin/login",
        data={"username": "admin", "password": "wrong"},
    )
    response = client.get("/admin/")
    assert response.status_code in (302, 307)


def test_admin_routes_are_not_mounted_when_disabled(monkeypatch):
    from src import admin as admin_module

    app = FastAPI()
    monkeypatch.setattr(admin_module.settings, "admin_enabled", False)

    admin_module.setup_admin(app)

    assert not any(route.path.startswith("/admin") for route in app.routes)
