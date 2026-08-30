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
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0
        self.closed = False

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1

    def close(self) -> None:
        self.closed = True


def test_default_v1_snapshot_keeps_scheduler_in_legacy_mode():
    from src.schedule import importer

    assert importer._default_review_bundle() is None


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


def test_invalid_default_review_bundle_never_calls_parser_only_import(monkeypatch):
    from src.schedule import importer

    called = False

    def invalid_bundle():
        raise RuntimeError("invalid reviewed snapshot")

    def forbidden_import(*args, **kwargs):
        nonlocal called
        called = True

    session = _FakeSession()
    monkeypatch.setattr(importer, "_default_review_bundle", invalid_bundle)
    monkeypatch.setattr(importer, "import_all", forbidden_import)
    monkeypatch.setattr(importer, "notify_admin", lambda message: None)

    result = importer.run_schedule_import(session_factory=lambda: session)

    assert "invalid reviewed snapshot" in result["error"]
    assert called is False
    assert session.commits == 0
    assert session.rollbacks == 1
    assert session.closed is True


def test_valid_default_review_bundle_is_passed_atomically_and_committed(monkeypatch):
    from src.schedule import importer

    bundle = object()
    captured = {}
    report = importer.ImportReport()

    def fake_import(session, fetcher, **kwargs):
        captured.update(kwargs)
        return report

    session = _FakeSession()
    monkeypatch.setattr(importer, "_default_review_bundle", lambda: bundle)
    monkeypatch.setattr(importer, "import_all", fake_import)

    result = importer.run_schedule_import(
        session_factory=lambda: session,
        fetcher=object(),
    )

    assert "summary" in result
    assert captured == {"review_bundle": bundle, "atomic": True}
    assert session.commits == 1
    assert session.rollbacks == 0
    assert session.closed is True


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
