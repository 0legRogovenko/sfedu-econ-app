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
        # прогревочный запуск задан tz-aware временем (иначе на UTC-хосте
        # промахнётся мимо grace-окна) — итог ревью
        assert job.next_run_time.tzinfo is not None
    finally:
        scheduler.shutdown(wait=False) if scheduler.running else None


def test_create_scheduler_has_schedule_import_job():
    from src.scheduler import create_scheduler

    scheduler = create_scheduler()
    try:
        job = scheduler.get_job("schedule_import")
        assert job is not None
        assert job.next_run_time.tzinfo is not None
        # раз в сутки: один цикл — 29 файлов с Crawl-delay 30 (~15 минут
        # чтения чужого сайта), чаще ходить незачем и невежливо
        assert job.trigger.interval.total_seconds() == 24 * 3600
    finally:
        scheduler.shutdown(wait=False) if scheduler.running else None


class _FakeSession:
    def rollback(self) -> None: ...

    def close(self) -> None: ...


def test_schedule_import_failure_alerts_admin_and_does_not_raise(monkeypatch):
    # фоновая задача не роняет процесс: падение уезжает админу, как у новостей
    from src.schedule import importer

    def boom(*args, **kwargs):
        raise RuntimeError("сеть недоступна")

    alerts: list[str] = []
    monkeypatch.setattr(importer, "import_all", boom)
    monkeypatch.setattr(importer, "notify_admin", alerts.append)

    result = importer.run_schedule_import(session_factory=_FakeSession)
    assert "сеть недоступна" in result["error"]
    assert alerts and "сеть недоступна" in alerts[0]


def test_schedule_import_reports_partial_document_failures(monkeypatch):
    from src.schedule import importer

    report = importer.ImportReport(
        documents=[
            importer.DocumentReport(
                p_doc_id="1",
                section="Осень",
                label="1 курс",
                doc_type=importer.DocType.UNKNOWN,
                status=importer.STATUS_FAILED,
                error="broken document",
            )
        ]
    )
    monkeypatch.setattr(importer, "import_all", lambda *args, **kwargs: report)

    result = importer.run_schedule_import(session_factory=_FakeSession)

    assert result["failed"] == 1


def test_notify_admin_never_raises_without_config(monkeypatch):
    # без токена/чата notify_admin молчит и не бросает
    from src import alerts

    monkeypatch.setattr(alerts.settings, "telegram_alert_bot_token", None)
    monkeypatch.setattr(alerts.settings, "telegram_alert_chat_id", None)
    alerts.notify_admin("тест")  # не должно бросить
