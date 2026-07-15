"""Оркестрация парсеров новостей: фетч, дедуп, вставка, изоляция ошибок.

Ошибка одного источника (или одной статьи) не роняет остальное и не трогает
уже сохранённые данные. CLI-запуск: ``python -m src.parsers.runner``.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from sqlalchemy import select

from src.alerts import notify_admin
from src.database import SessionLocal
from src.models import News, NewsSource
from src.parsers import sfedu_news
from src.parsers.sfedu_news import _default_fetch

logger = logging.getLogger(__name__)


def _sync_sfedu(session, fetch: Callable[[str], str]) -> int:
    """Синхронизирует источник sfedu, возвращает число новых записей.

    Бросает исключение только при сбое фетча листинга (обрабатывается выше).
    """
    listing_html = fetch(sfedu_news.LISTING_URL)
    candidates = sfedu_news.parse_listing(listing_html)

    if not candidates:
        # листинг скачался, но ничего не распарсилось — вероятно, сменилась
        # вёрстка sfedu.ru; сигналим админу, но не считаем это ошибкой
        logger.warning("sfedu: листинг скачан, но 0 новостей распарсилось")
        notify_admin(
            "Парсер новостей sfedu: страница скачалась, но 0 элементов "
            "распарсилось — вероятно, сменилась вёрстка sfedu.ru."
        )
        return 0

    existing = set(
        session.scalars(
            select(News.url).where(News.source == NewsSource.SFEDU)
        ).all()
    )

    new_count = 0
    for candidate in candidates:
        if candidate.url in existing:
            continue

        body = candidate.snippet or candidate.title
        try:
            article_html = fetch(candidate.url)
            article_text = sfedu_news.parse_article(article_html)
            if article_text:
                body = article_text
        except Exception:  # noqa: BLE001 — падение одной статьи не роняет цикл
            logger.warning("Не удалось загрузить статью %s", candidate.url)

        session.add(
            News(
                title=candidate.title,
                body=body,
                source=NewsSource.SFEDU,
                url=candidate.url,
                image_url=candidate.image_url,
                published_at=candidate.published_at,
            )
        )
        existing.add(candidate.url)
        new_count += 1

    if new_count:
        session.commit()
    return new_count


_SOURCES: dict[str, Callable] = {"sfedu": _sync_sfedu}


def run_news_parsers(
    session_factory: Callable = SessionLocal,
    fetch: Callable[[str], str] = _default_fetch,
) -> dict:
    """Запускает все источники, изолируя ошибки. Возвращает сводку по каждому."""
    result: dict[str, dict] = {}
    for name, sync in _SOURCES.items():
        session = session_factory()
        try:
            new_count = sync(session, fetch)
            result[name] = {"new": new_count}
        except Exception as exc:  # noqa: BLE001 — источник изолирован
            session.rollback()
            logger.exception("Парсер %s упал", name)
            notify_admin(f"Парсер новостей «{name}» упал: {exc}")
            result[name] = {"error": str(exc)}
        finally:
            session.close()
    return result


if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(level=logging.INFO)
    print(run_news_parsers())
