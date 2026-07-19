"""Автозабор справочника с econ-sfedu.ru: деканат и состав кафедр.

Владеет ТОЛЬКО строками `contacts` с `source='econ_site'` и при каждом
запуске заменяет именно их. Записи, заведённые админом руками (кабинеты,
часы приёма, почты — на сайте факультета их нет), не трогаются.

Замена идёт одной транзакцией и только если разбор дал непустой результат:
пустой ответ сайта не должен обнулять справочник. CLI-запуск:
``python -m src.parsers.econ_staff_runner``.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from sqlalchemy import delete, select

from src.alerts import notify_admin
from src.database import SessionLocal
from src.models import Contact, ContactSource
from src.parsers import econ_staff
from src.parsers.econ_staff import Person

logger = logging.getLogger(__name__)

DEANERY_SECTION = "Деканат"


def _default_fetch(url: str) -> str:
    # Импорт внутри функции: тесты подменяют fetch и не должны тянуть сеть.
    import httpx

    response = httpx.get(
        url,
        timeout=30,
        follow_redirects=True,
        # Только ASCII: httpx кодирует заголовки в ascii и на кириллице падает.
        headers={
            "User-Agent": (
                "sfedu-econ-app/1.0 (unofficial student app, SFedU econ faculty)"
            )
        },
    )
    response.raise_for_status()
    return response.text


def _rows(section: str, people: list[Person], start_order: int) -> list[Contact]:
    return [
        Contact(
            section=section,
            name=person.name,
            role=person.role or None,
            phone=person.phone,
            source=ContactSource.ECON_SITE,
            # Порядок с сайта осмысленный: заведующий первым, дальше состав.
            sort_order=start_order + index,
        )
        for index, person in enumerate(people)
    ]


def collect(fetch: Callable[[str], str]) -> list[Contact]:
    """Скачивает и разбирает все страницы. Возвращает строки для вставки.

    Сбой ОДНОЙ кафедры не отменяет остальные: её страница пропускается с
    сигналом админу. Сбой страницы деканата или каталога кафедр —
    исключение, его обрабатывает вызывающий.
    """
    rows: list[Contact] = []

    deanery = econ_staff.parse_deanery(fetch(econ_staff.DEANERY_URL))
    if not deanery:
        # Страница скачалась, но людей ноль — почти наверняка сменилась
        # вёрстка. Молча отдать пустой деканат нельзя.
        notify_admin(
            "Справочник econ-sfedu.ru: страница деканата скачалась, но 0 "
            "человек распарсилось — вероятно, сменилась вёрстка сайта."
        )
    rows += _rows(DEANERY_SECTION, deanery, start_order=0)

    links = econ_staff.parse_department_links(fetch(econ_staff.DEPARTMENTS_URL))
    if not links:
        notify_admin(
            "Справочник econ-sfedu.ru: каталог кафедр скачался, но ссылок на "
            "кафедры не нашлось — вероятно, сменилась вёрстка сайта."
        )

    for order, link in enumerate(links, start=1):
        try:
            department = econ_staff.parse_department(fetch(link))
        except Exception:  # noqa: BLE001 — одна кафедра не роняет остальные
            logger.exception("Кафедра %s: страница не скачалась", link)
            notify_admin(f"Справочник econ-sfedu.ru: не удалось скачать {link}")
            continue

        if not department.name:
            logger.warning("Кафедра %s: не распознано название", link)
            continue

        people = ([department.head] if department.head else []) + department.staff
        if not people:
            notify_admin(
                f"Справочник econ-sfedu.ru: кафедра «{department.name}» "
                "скачалась, но состав не распарсился."
            )
            continue

        rows += _rows(department.name, people, start_order=order * 100)

    return rows


def sync(session, fetch: Callable[[str], str] = _default_fetch) -> int:
    """Обновляет автозабранную часть справочника. Возвращает число строк."""
    rows = collect(fetch)

    if not rows:
        # Ничего не разобралось — оставляем прежний справочник как есть.
        # Пустой результат парсера не должен стирать данные (тот же принцип,
        # что в импорте расписания).
        logger.warning("Справочник econ-sfedu.ru: 0 строк, замена отменена")
        notify_admin(
            "Справочник econ-sfedu.ru: разбор дал 0 записей — обновление "
            "отменено, показывается прежний справочник."
        )
        return 0

    session.execute(
        delete(Contact).where(Contact.source == ContactSource.ECON_SITE)
    )
    session.add_all(rows)
    session.flush()
    return len(rows)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    with SessionLocal() as session:
        count = sync(session)
        session.commit()
        manual = session.scalar(
            select(Contact)
            .where(Contact.source == ContactSource.MANUAL)
            .limit(1)
        )
        logger.info(
            "Справочник обновлён: %s записей с сайта%s",
            count,
            "; записи админа сохранены" if manual else "",
        )


if __name__ == "__main__":
    main()
