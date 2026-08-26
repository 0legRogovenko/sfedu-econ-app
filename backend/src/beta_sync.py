"""One-shot data refresh for the free beta backend.

The web API runs as a serverless function, so long-lived APScheduler jobs are
not appropriate there.  GitHub Actions invokes this module against the same
PostgreSQL database instead.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from src.database import SessionLocal
from src.maintenance import purge_old_assistant_logs
from src.parsers.econ_staff_runner import main as run_staff_import
from src.parsers.runner import run_news_parsers
from src.schedule.importer import run_schedule_import


class BetaSyncFailed(RuntimeError):
    def __init__(self, failed_sources: list[str], result: dict[str, Any]):
        self.result = result
        super().__init__("beta sync failed: " + ", ".join(failed_sources))


def _redact_error_values(value: Any) -> Any:
    """Keep machine-readable status without leaking provider/DB details."""
    if isinstance(value, dict):
        return {
            key: "source failed" if key == "error" else _redact_error_values(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact_error_values(item) for item in value]
    return value


def _purge_expired_assistant_logs() -> int:
    db = SessionLocal()
    try:
        return purge_old_assistant_logs(db)
    finally:
        db.close()


def run_beta_sync(
    *,
    news: Callable[[], dict[str, Any]] = run_news_parsers,
    staff: Callable[[], None] = run_staff_import,
    schedule: Callable[[], dict[str, Any]] = run_schedule_import,
    cleanup: Callable[[], int] = _purge_expired_assistant_logs,
) -> dict[str, Any]:
    """Refresh every source, then fail once with a complete source summary."""
    result: dict[str, Any] = {}
    failed: list[str] = []

    try:
        news_result = news()
        result["news"] = _redact_error_values(news_result)
        if any(
            isinstance(source_result, dict) and "error" in source_result
            for source_result in news_result.values()
        ):
            failed.append("news")
    except Exception as error:  # noqa: BLE001 - continue with other sources
        result["news"] = {"error": type(error).__name__}
        failed.append("news")

    try:
        staff()
        result["staff"] = {"status": "ok"}
    except Exception as error:  # noqa: BLE001 - continue with other sources
        result["staff"] = {"error": type(error).__name__}
        failed.append("staff")

    try:
        schedule_result = schedule()
        result["schedule"] = _redact_error_values(schedule_result)
        if (
            "error" in schedule_result
            or int(schedule_result.get("failed", 0)) > 0
            or bool(schedule_result.get("missing"))
        ):
            failed.append("schedule")
    except Exception as error:  # noqa: BLE001 - report after all sources ran
        result["schedule"] = {"error": type(error).__name__}
        failed.append("schedule")

    try:
        result["assistant_logs"] = {"removed": cleanup()}
    except Exception as error:  # noqa: BLE001 - report after all sources ran
        result["assistant_logs"] = {"error": type(error).__name__}
        failed.append("assistant_logs")

    if failed:
        raise BetaSyncFailed(failed, result)
    return result


def main() -> None:
    try:
        result = run_beta_sync()
    except BetaSyncFailed as error:
        print(json.dumps(error.result, ensure_ascii=False, sort_keys=True))
        raise
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":  # pragma: no cover
    main()
