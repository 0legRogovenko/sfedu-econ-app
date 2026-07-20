"""Обслуживающие задачи: авточистка старых данных (для приватности)."""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from src.config import settings
from src.models import AssistantLog


def purge_old_assistant_logs(db: Session) -> int:
    """Удаляет логи помощника старше assistant_log_retention_days.

    Возвращает число удалённых строк. Границу окна считает та же СУБД, что пишет
    created_at (как и rate-limit), поэтому часы процесса и БД не расходятся.
    """
    cutoff = db.scalar(select(func.now())) - timedelta(
        days=settings.assistant_log_retention_days
    )
    result = db.execute(delete(AssistantLog).where(AssistantLog.created_at < cutoff))
    db.commit()
    return result.rowcount
