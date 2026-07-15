"""Фоновый планировщик парсеров новостей (APScheduler).

Стартует только когда settings.enable_scheduler=True — то есть в контейнере
api, но не в тестах и не при alembic.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler

from src.config import settings
from src.parsers.runner import run_news_parsers

logger = logging.getLogger(__name__)


def create_scheduler() -> BackgroundScheduler:
    """Создаёт планировщик с задачей парсинга новостей (не запускает его)."""
    scheduler = BackgroundScheduler(timezone="Europe/Moscow")
    scheduler.add_job(
        _run_news_job,
        trigger="interval",
        minutes=settings.news_poll_minutes,
        next_run_time=datetime.now() + timedelta(seconds=30),
        id="news_parsers",
        max_instances=1,
        coalesce=True,
    )
    return scheduler


def _run_news_job() -> None:
    logger.info("Запуск парсеров новостей по расписанию")
    result = run_news_parsers()
    logger.info("Парсеры новостей завершены: %s", result)
