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

import time

from src.alerts import notify_admin
from src.database import SessionLocal
from src.models import Contact, ContactSource
from src.parsers import econ_staff
from src.parsers.econ_staff import Person

logger = logging.getLogger(__name__)

DEANERY_SECTION = "Деканат"

# robots.txt sfedu.ru: Crawl-delay: 30. Личные страницы там же, поэтому
# соблюдаем ту же паузу, что и импорт расписания.
SFEDU_CRAWL_DELAY_SECONDS = 30


def _default_fetch(url: str) -> str:
    # Импорт внутри функции: тесты подменяют fetch и не должны тянуть сеть.
    import ssl

    import httpx
    import truststore

    # Системное хранилище, а не certifi: цепочку GlobalSign у sfedu.ru certifi
    # не достраивает, и без этого КАЖДЫЙ запрос к личным страницам падал на
    # проверке сертификата — молча, потому что ошибку глотал общий except.
    # Тот же приём уже используют парсер новостей и импорт расписания.
    context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)

    response = httpx.get(
        url,
        timeout=30,
        follow_redirects=True,
        verify=context,
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


# Проверять подстроку "sfedu.ru" нельзя: она входит и в "econ-sfedu.ru", и мы
# бы ходили за почтой на страницы кафедр — по 30 секунд паузы впустую.
#
# Старый формат ссылки `/www/stat_pages22.show?...p_per_id=N` НЕ включён
# намеренно: на 2026-07-19 он отдаёт 404 для всех без исключения id (проверено
# на 10 разных), сайт переехал на /s7/person/. Часть карточек на econ-sfedu.ru
# всё ещё ссылается по-старому — ходить туда значит десять раз за прогон
# стучаться в заведомо мёртвую ручку с паузой в полминуты. Логин для нового
# формата из p_per_id не выводится, а угадывать его по фамилии нельзя: цена
# ошибки — письмо постороннему человеку.
_PERSON_PAGE_MARKERS = ("sfedu.ru/s7/person/",)


def _person_page_urls(people: list[Person]) -> dict[str, str]:
    """ФИО → ссылка на личную страницу sfedu.ru (у кого она есть)."""
    return {
        p.name: p.profile_url
        for p in people
        if p.profile_url
        and any(marker in p.profile_url for marker in _PERSON_PAGE_MARKERS)
    }


def fill_emails(
    rows: list[Contact],
    people: list[Person],
    fetch: Callable[[str], str],
    known: dict[str, str] | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> int:
    """Проставляет почты с личных страниц. Возвращает число заполненных.

    Инкрементально: у кого почта уже известна с прошлого запуска, страницу
    заново не дёргаем — иначе каждый суточный прогон стучался бы в sfedu.ru
    восемь десятков раз подряд.
    """
    known = known or {}
    urls = _person_page_urls(people)
    filled = 0
    fetched_any = False

    for row in rows:
        cached = known.get(row.name)
        if cached:
            row.email = cached
            filled += 1
            continue

        url = urls.get(row.name)
        if not url:
            continue

        if fetched_any:
            sleep(SFEDU_CRAWL_DELAY_SECONDS)
        try:
            page = fetch(url)
        except Exception as error:  # noqa: BLE001 — один не роняет остальных
            # С причиной: без неё сбой TLS выглядел так же, как 404, и
            # «0 почт из 85» было нечем объяснить.
            logger.warning("Личная страница недоступна: %s (%s)", url, error)
            fetched_any = True
            continue
        fetched_any = True

        email = econ_staff.parse_person_email(page)
        if email:
            row.email = email
            filled += 1

    return filled


def collect(fetch: Callable[[str], str]) -> tuple[list[Contact], list[Person]]:
    """Скачивает и разбирает все страницы. Возвращает строки для вставки.

    Сбой ОДНОЙ кафедры не отменяет остальные: её страница пропускается с
    сигналом админу. Сбой страницы деканата или каталога кафедр —
    исключение, его обрабатывает вызывающий.
    """
    rows: list[Contact] = []
    everyone: list[Person] = []

    deanery = econ_staff.parse_deanery(fetch(econ_staff.DEANERY_URL))
    if not deanery:
        # Страница скачалась, но людей ноль — почти наверняка сменилась
        # вёрстка. Молча отдать пустой деканат нельзя.
        notify_admin(
            "Справочник econ-sfedu.ru: страница деканата скачалась, но 0 "
            "человек распарсилось — вероятно, сменилась вёрстка сайта."
        )
    rows += _rows(DEANERY_SECTION, deanery, start_order=0)
    everyone += deanery

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
        everyone += people

    return rows, everyone


def sync(
    session,
    fetch: Callable[[str], str] = _default_fetch,
    with_emails: bool = True,
    sleep: Callable[[float], None] = time.sleep,
) -> int:
    """Обновляет автозабранную часть справочника. Возвращает число строк."""
    rows, people = collect(fetch)

    if with_emails and rows:
        # Почты, добытые в прошлый раз: их не перезапрашиваем.
        known = {
            name: email
            for name, email in session.execute(
                select(Contact.name, Contact.email).where(
                    Contact.source == ContactSource.ECON_SITE,
                    Contact.email.is_not(None),
                )
            ).all()
        }
        filled = fill_emails(rows, people, fetch, known=known, sleep=sleep)
        logger.info("Почт проставлено: %s из %s", filled, len(rows))
        if filled == 0 and people:
            notify_admin(
                "Справочник econ-sfedu.ru: ни одной почты не удалось "
                "получить. Причина в логе: либо личные страницы sfedu.ru "
                "недоступны (сеть, сертификат), либо на них сменилась "
                "вёрстка. Справочник при этом обновлён, но без почт."
            )

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
