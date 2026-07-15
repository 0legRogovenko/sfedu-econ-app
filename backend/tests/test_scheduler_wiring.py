from fastapi.testclient import TestClient


def test_scheduler_disabled_by_default_in_tests():
    from src.config import settings

    assert settings.enable_scheduler is False


def test_app_starts_without_scheduler():
    # lifespan не должен поднимать планировщик при enable_scheduler=False;
    # приложение стартует и /health отвечает
    from src.main import app

    with TestClient(app) as client:
        assert client.get("/health").status_code == 200


def test_create_scheduler_has_news_job():
    from src.scheduler import create_scheduler

    scheduler = create_scheduler()
    try:
        job = scheduler.get_job("news_parsers")
        assert job is not None
    finally:
        scheduler.shutdown(wait=False) if scheduler.running else None


def test_notify_admin_never_raises_without_config(monkeypatch):
    # без токена/чата notify_admin молчит и не бросает
    from src import alerts

    monkeypatch.setattr(alerts.settings, "telegram_alert_bot_token", None)
    monkeypatch.setattr(alerts.settings, "telegram_alert_chat_id", None)
    alerts.notify_admin("тест")  # не должно бросить
