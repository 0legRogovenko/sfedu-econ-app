"""Уведомления администратору о сбоях фоновых задач.

Никогда не бросает исключений — сбой алерта не должен ронять вызывающий код.
Если Telegram не сконфигурирован (нет токена/чата) — пишет только в лог.
"""

from __future__ import annotations

import logging

import requests

from src.config import settings

logger = logging.getLogger(__name__)


def notify_admin(text: str) -> None:
    """Отправляет текст админу в Telegram; при любой ошибке — только лог."""
    logger.warning("admin alert: %s", text)

    token = settings.telegram_alert_bot_token
    chat_id = settings.telegram_alert_chat_id
    if not token or not chat_id:
        return

    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=10,
        )
    except Exception:  # noqa: BLE001 — алерт не должен ронять вызывающий код
        logger.exception("Не удалось отправить Telegram-алерт")
