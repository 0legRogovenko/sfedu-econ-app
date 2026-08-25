import pytest


def test_beta_sync_runs_every_source_even_when_one_fails():
    from src.beta_sync import BetaSyncFailed, run_beta_sync

    calls: list[str] = []

    def news():
        calls.append("news")
        return {"sfedu": {"error": "listing unavailable"}}

    def staff():
        calls.append("staff")

    def schedule():
        calls.append("schedule")
        return {"documents": 29}

    with pytest.raises(BetaSyncFailed, match="news"):
        run_beta_sync(news=news, staff=staff, schedule=schedule, cleanup=lambda: 0)

    assert calls == ["news", "staff", "schedule"]


def test_beta_sync_reports_schedule_failure_after_other_sources_finish():
    from src.beta_sync import BetaSyncFailed, run_beta_sync

    calls: list[str] = []

    def news():
        calls.append("news")
        return {"sfedu": {"new": 2}}

    def staff():
        calls.append("staff")

    def schedule():
        calls.append("schedule")
        return {"error": "official page unavailable"}

    with pytest.raises(BetaSyncFailed, match="schedule"):
        run_beta_sync(news=news, staff=staff, schedule=schedule, cleanup=lambda: 0)

    assert calls == ["news", "staff", "schedule"]


def test_beta_sync_fails_when_schedule_has_partial_document_failures():
    from src.beta_sync import BetaSyncFailed, run_beta_sync

    with pytest.raises(BetaSyncFailed, match="schedule"):
        run_beta_sync(
            news=lambda: {},
            staff=lambda: None,
            schedule=lambda: {
                "summary": "документов 29 ({'imported': 28, 'failed': 1})",
                "failed": 1,
            },
            cleanup=lambda: 0,
        )


def test_beta_sync_fails_when_official_schedule_documents_disappear():
    from src.beta_sync import BetaSyncFailed, run_beta_sync

    with pytest.raises(BetaSyncFailed, match="schedule"):
        run_beta_sync(
            news=lambda: {},
            staff=lambda: None,
            schedule=lambda: {"failed": 0, "missing": ["14001"]},
            cleanup=lambda: 0,
        )


def test_beta_sync_returns_a_machine_readable_summary_on_success():
    from src.beta_sync import run_beta_sync

    result = run_beta_sync(
        news=lambda: {"sfedu": {"new": 3}},
        staff=lambda: None,
        schedule=lambda: {"documents": 29},
        cleanup=lambda: 0,
    )

    assert result == {
        "news": {"sfedu": {"new": 3}},
        "staff": {"status": "ok"},
        "schedule": {"documents": 29},
        "assistant_logs": {"removed": 0},
    }


def test_beta_sync_purges_expired_assistant_logs():
    from src.beta_sync import run_beta_sync

    calls: list[str] = []

    result = run_beta_sync(
        news=lambda: {},
        staff=lambda: None,
        schedule=lambda: {},
        cleanup=lambda: calls.append("cleanup") or 4,
    )

    assert calls == ["cleanup"]
    assert result["assistant_logs"] == {"removed": 4}


def test_beta_sync_redacts_exception_messages():
    from src.beta_sync import BetaSyncFailed, run_beta_sync

    secret = "postgresql://user:password@database.example/db"

    def broken_news():
        raise RuntimeError(secret)

    with pytest.raises(BetaSyncFailed) as raised:
        run_beta_sync(
            news=broken_news,
            staff=lambda: None,
            schedule=lambda: {},
            cleanup=lambda: 0,
        )

    assert secret not in str(raised.value.result)
    assert raised.value.result["news"] == {"error": "RuntimeError"}


def test_beta_sync_redacts_errors_returned_by_sources():
    from src.beta_sync import BetaSyncFailed, run_beta_sync

    secret = "postgresql://user:password@database.example/db"

    with pytest.raises(BetaSyncFailed) as raised:
        run_beta_sync(
            news=lambda: {"sfedu": {"error": secret}},
            staff=lambda: None,
            schedule=lambda: {"error": secret},
            cleanup=lambda: 0,
        )

    assert secret not in str(raised.value.result)
    assert raised.value.result["news"]["sfedu"] == {"error": "source failed"}
    assert raised.value.result["schedule"] == {"error": "source failed"}
