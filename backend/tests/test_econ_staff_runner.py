"""Автозабор справочника: изоляция ошибок и защита записей админа."""

from pathlib import Path

import pytest
from sqlalchemy import select

from src.models import Contact, ContactSource
from src.parsers import econ_staff, econ_staff_runner

FIXTURES = Path(__file__).parent / "fixtures" / "econ_staff"


def _fx(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _fetch_ok(url: str) -> str:
    """Деканат + каталог кафедр + одна кафедра (ссылки берутся из каталога)."""
    if url == econ_staff.DEANERY_URL:
        return _fx("about-us.html")
    if url == econ_staff.DEPARTMENTS_URL:
        return _fx("kafedry.html")
    return _fx("kafedra-teoria.html")


def test_fills_deanery_and_departments(db_session):
    count = econ_staff_runner.sync(db_session, fetch=_fetch_ok)

    assert count > 20
    sections = set(db_session.scalars(select(Contact.section)).all())
    assert "Деканат" in sections
    assert "Экономическая теория" in sections


def test_head_goes_first_in_department(db_session):
    econ_staff_runner.sync(db_session, fetch=_fetch_ok)

    rows = db_session.scalars(
        select(Contact)
        .where(Contact.section == "Экономическая теория")
        .order_by(Contact.sort_order)
    ).all()
    assert "Заведующий кафедрой" in rows[0].role


def test_manual_contacts_survive(db_session):
    """Записи админа автозабор не трогает — там кабинеты и часы приёма."""
    db_session.add(
        Contact(
            section="Деканат",
            name="Иванова Елена Петровна",
            role="секретарь",
            office="201",
            office_hours="пн–пт 10:00–16:00",
            source=ContactSource.MANUAL,
        )
    )
    db_session.flush()

    econ_staff_runner.sync(db_session, fetch=_fetch_ok)

    manual = db_session.scalars(
        select(Contact).where(Contact.source == ContactSource.MANUAL)
    ).all()
    assert len(manual) == 1
    assert manual[0].office == "201"


def test_rerun_replaces_only_own_rows(db_session):
    """Повторный запуск не плодит дубли и не копит устаревшие записи."""
    first = econ_staff_runner.sync(db_session, fetch=_fetch_ok)
    second = econ_staff_runner.sync(db_session, fetch=_fetch_ok)

    assert first == second
    rows = db_session.scalars(
        select(Contact).where(Contact.source == ContactSource.ECON_SITE)
    ).all()
    assert len(rows) == second


def test_broken_department_does_not_lose_the_rest(db_session, monkeypatch):
    """Одна недоступная кафедра не отменяет остальные и не роняет синк."""
    calls = {"n": 0}

    def flaky(url: str) -> str:
        if url == econ_staff.DEANERY_URL:
            return _fx("about-us.html")
        if url == econ_staff.DEPARTMENTS_URL:
            return _fx("kafedry.html")
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("сеть отвалилась")
        return _fx("kafedra-teoria.html")

    alerts: list[str] = []
    monkeypatch.setattr(
        econ_staff_runner, "notify_admin", lambda text: alerts.append(text)
    )

    count = econ_staff_runner.sync(db_session, fetch=flaky)

    assert count > 20  # остальные кафедры на месте
    assert any("не удалось скачать" in a for a in alerts)


def test_empty_parse_does_not_wipe_directory(db_session, monkeypatch):
    """Сайт отдал пустые страницы — прежний справочник остаётся на месте."""
    db_session.add(
        Contact(
            section="Деканат",
            name="Старая запись",
            source=ContactSource.ECON_SITE,
        )
    )
    db_session.flush()

    alerts: list[str] = []
    monkeypatch.setattr(
        econ_staff_runner, "notify_admin", lambda text: alerts.append(text)
    )

    count = econ_staff_runner.sync(db_session, fetch=lambda url: "<html></html>")

    assert count == 0
    survived = db_session.scalars(select(Contact.name)).all()
    assert "Старая запись" in survived
    assert any("обновление отменено" in a for a in alerts)


def test_layout_change_alerts_admin(db_session, monkeypatch):
    """Страница скачалась, но людей ноль — это сигнал, а не пустой результат."""
    alerts: list[str] = []
    monkeypatch.setattr(
        econ_staff_runner, "notify_admin", lambda text: alerts.append(text)
    )

    def fetch(url: str) -> str:
        if url == econ_staff.DEANERY_URL:
            return "<html><body>вёрстка сменилась</body></html>"
        if url == econ_staff.DEPARTMENTS_URL:
            return _fx("kafedry.html")
        return _fx("kafedra-teoria.html")

    econ_staff_runner.sync(db_session, fetch=fetch)

    assert any("деканата" in a for a in alerts)


@pytest.mark.parametrize("url", [econ_staff.DEANERY_URL, econ_staff.DEPARTMENTS_URL])
def test_key_page_failure_propagates(db_session, url):
    """Сбой деканата или каталога — исключение: молча синкать нечего."""

    def fetch(requested: str) -> str:
        if requested == url:
            raise RuntimeError("сеть отвалилась")
        return _fx("about-us.html")

    with pytest.raises(RuntimeError):
        econ_staff_runner.sync(db_session, fetch=fetch)
