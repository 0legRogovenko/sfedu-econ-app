"""Фоновый планировщик парсеров новостей и импорта расписания (APScheduler).

Стартует только когда settings.enable_scheduler=True — то есть в контейнере
api, но не в тестах и не при alembic.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.background import BackgroundScheduler

from src.config import settings
from src.parsers.runner import run_news_parsers
from src.parsers.econ_staff_runner import main as run_staff_import
from src.schedule.importer import run_schedule_import

logger = logging.getLogger(__name__)


def create_scheduler() -> BackgroundScheduler:
    """Создаёт планировщик с задачами новостей и расписания (не запускает его)."""
    scheduler = BackgroundScheduler(timezone="Europe/Moscow")
    scheduler.add_job(
        _run_news_job,
        trigger="interval",
        minutes=settings.news_poll_minutes,
        # tz-aware: наивный now() интерпретировался бы как MSK и на UTC-хосте
        # (Docker) промахивался бы мимо grace-окна прогрева (итог ревью)
        next_run_time=datetime.now(timezone.utc) + timedelta(seconds=30),
        id="news_parsers",
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        _run_schedule_job,
        trigger="interval",
        hours=settings.schedule_import_hours,
        # Прогрев позже новостей: цикл импорта — это 29 файлов с Crawl-delay 30,
        # то есть ~15 минут; на старте контейнера он не нужен первым.
        next_run_time=datetime.now(timezone.utc) + timedelta(minutes=5),
        id="schedule_import",
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        _run_staff_job,
        trigger="interval",
        hours=settings.staff_import_hours,
        # Ещё позже расписания: 10 страниц сайта факультета, спешить некуда.
        next_run_time=datetime.now(timezone.utc) + timedelta(minutes=10),
        id="staff_import",
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        _run_log_retention_job,
        trigger="interval",
        hours=24,
        # Приватность: раз в сутки чистим логи помощника старше срока хранения.
        next_run_time=datetime.now(timezone.utc) + timedelta(minutes=15),
        id="log_retention",
        max_instances=1,
        coalesce=True,
    )
    return scheduler


def _run_news_job() -> None:
    logger.info("Запуск парсеров новостей по расписанию")
    result = run_news_parsers()
    logger.info("Парсеры новостей завершены: %s", result)


def _run_staff_job() -> None:
    logger.info("Запуск обновления справочника сотрудников")
    run_staff_import()


def _run_schedule_job() -> None:
    logger.info("Запуск импорта расписания по расписанию")
    result = run_schedule_import()
    logger.info("Импорт расписания завершён: %s", result)


def _run_log_retention_job() -> None:
    from src.database import SessionLocal
    from src.maintenance import purge_old_assistant_logs

    db = SessionLocal()
    try:
        removed = purge_old_assistant_logs(db)
        logger.info("Авточистка логов помощника: удалено %d", removed)
    finally:
        db.close()
