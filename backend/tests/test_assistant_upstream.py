from fastapi import FastAPI
from fastapi.testclient import TestClient
from requests import Timeout

from src.api import assistant_upstream


def make_client():
    app = FastAPI()
    app.include_router(assistant_upstream.router, prefix="/api")
    return TestClient(app)


class UpstreamResponse:
    def __init__(self, status, payload):
        self.status_code = status
        self.payload = payload

    def json(self):
        return self.payload


def test_question_keeps_upstream_rate_limit(monkeypatch):
    def request(method, url, *, json, params, timeout, allow_redirects):
        assert method == "POST"
        assert url == "https://econ-yufu-api.vercel.app/api/assistant/ask"
        assert json == {"question": "Тестовый вопрос", "device_id": "test-device"}
        assert params is None
        assert allow_redirects is False
        return UpstreamResponse(429, {"detail": "Лимит исчерпан"})

    monkeypatch.setattr(assistant_upstream.requests, "request", request)
    with make_client() as client:
        response = client.post(
            "/api/assistant/ask",
            json={"question": "  Тестовый вопрос  ", "device_id": "test-device"},
        )
    assert response.status_code == 429
    assert response.json() == {"detail": "Лимит исчерпан"}


def test_delete_passes_through_to_the_same_service(monkeypatch):
    def request(method, url, *, json, params, timeout, allow_redirects):
        assert method == "DELETE"
        assert url == "https://econ-yufu-api.vercel.app/api/assistant/data"
        assert json is None
        assert params == {"device_id": "test-device"}
        assert allow_redirects is False
        return UpstreamResponse(200, {"deleted": 1})

    monkeypatch.setattr(assistant_upstream.requests, "request", request)
    with make_client() as client:
        response = client.delete("/api/assistant/data?device_id=test-device")
    assert response.status_code == 200
    assert response.json() == {"deleted": 1}


def test_timeout_reports_unavailable_without_retrying(monkeypatch):
    count = 0

    def request(*args, **kwargs):
        nonlocal count
        count += 1
        raise Timeout()

    monkeypatch.setattr(assistant_upstream.requests, "request", request)
    with make_client() as client:
        response = client.post(
            "/api/assistant/ask",
            json={"question": "Тестовый вопрос", "device_id": "test-device"},
        )
    assert response.status_code == 503
    assert count == 1
