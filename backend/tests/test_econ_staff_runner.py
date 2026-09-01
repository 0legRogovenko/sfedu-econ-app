"""Автозабор справочника: изоляция ошибок и защита записей админа."""

import ssl
from pathlib import Path

import httpx
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
    count = econ_staff_runner.sync(db_session, fetch=_fetch_ok, with_emails=False)

    assert count > 20
    sections = set(db_session.scalars(select(Contact.section)).all())
    assert "Деканат" in sections
    assert "Экономическая теория" in sections


def test_dean_is_moved_from_department_to_deanery():
    rows = econ_staff_runner._rows(
        "Экономическая кибернетика",
        [
            econ_staff.Person(
                name="Косолапова Наталья Алексеевна",
                role="д.э.н., декан",
                profile_url="https://sfedu.ru/s7/person/ru/nakosolapova",
            )
        ],
        start_order=100,
    )

    assert rows[0].section == "Деканат"


def test_head_goes_first_in_department(db_session):
    econ_staff_runner.sync(db_session, fetch=_fetch_ok, with_emails=False)

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

    econ_staff_runner.sync(db_session, fetch=_fetch_ok, with_emails=False)

    manual = db_session.scalars(
        select(Contact).where(Contact.source == ContactSource.MANUAL)
    ).all()
    assert len(manual) == 1
    assert manual[0].office == "201"


def test_rerun_replaces_only_own_rows(db_session):
    """Повторный запуск не плодит дубли и не копит устаревшие записи."""
    first = econ_staff_runner.sync(db_session, fetch=_fetch_ok, with_emails=False)
    second = econ_staff_runner.sync(db_session, fetch=_fetch_ok, with_emails=False)

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

    count = econ_staff_runner.sync(db_session, fetch=flaky, with_emails=False)

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

    count = econ_staff_runner.sync(db_session, fetch=lambda url: "<html></html>", with_emails=False)

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

    econ_staff_runner.sync(db_session, fetch=fetch, with_emails=False)

    assert any("деканата" in a for a in alerts)


@pytest.mark.parametrize("url", [econ_staff.DEANERY_URL, econ_staff.DEPARTMENTS_URL])
def test_key_page_failure_propagates(db_session, url):
    """Сбой деканата или каталога — исключение: молча синкать нечего."""

    def fetch(requested: str) -> str:
        if requested == url:
            raise RuntimeError("сеть отвалилась")
        return _fx("about-us.html")

    with pytest.raises(RuntimeError):
        econ_staff_runner.sync(db_session, fetch=fetch, with_emails=False)


class TestEmails:
    """Почты берутся с личных страниц sfedu.ru, где они спрятаны в base64."""

    _PERSON_PAGE = (FIXTURES / "person-sfedu.html").read_text(encoding="utf-8")

    def _fetch(self, url: str) -> str:
        if url == econ_staff.DEANERY_URL:
            return _fx("about-us.html")
        if url == econ_staff.DEPARTMENTS_URL:
            return _fx("kafedry.html")
        if "sfedu.ru/s7/person" in url or "stat_pages22" in url:
            return self._PERSON_PAGE
        return _fx("kafedra-teoria.html")

    def test_email_lands_in_contact(self, db_session):
        econ_staff_runner.sync(
            db_session, fetch=self._fetch, sleep=lambda _: None
        )

        emails = db_session.scalars(
            select(Contact.email).where(Contact.email.is_not(None))
        ).all()
        assert emails
        assert all("sfedu-university.com" not in e for e in emails)
        assert "obelokrylova@sfedu.ru" in emails

    def test_crawl_delay_is_respected(self, db_session):
        """robots.txt sfedu.ru просит 30 секунд между запросами."""
        pauses: list[float] = []
        econ_staff_runner.sync(
            db_session, fetch=self._fetch, sleep=pauses.append
        )

        assert pauses, "паузы между личными страницами не делались"
        assert all(p == econ_staff_runner.SFEDU_CRAWL_DELAY_SECONDS for p in pauses)

    def test_known_emails_are_not_refetched(self, db_session):
        """Суточный прогон не должен заново дёргать восемь десятков страниц."""
        econ_staff_runner.sync(
            db_session, fetch=self._fetch, sleep=lambda _: None
        )
        db_session.flush()

        hits: list[str] = []

        def counting_fetch(url: str) -> str:
            if "person" in url or "stat_pages22" in url:
                hits.append(url)
            return self._fetch(url)

        econ_staff_runner.sync(
            db_session, fetch=counting_fetch, sleep=lambda _: None
        )
        assert hits == []

    def test_person_page_failure_keeps_the_rest(self, db_session):
        def flaky(url: str) -> str:
            if "sfedu.ru/s7/person" in url:
                raise RuntimeError("страница недоступна")
            return self._fetch(url)

        count = econ_staff_runner.sync(
            db_session, fetch=flaky, sleep=lambda _: None
        )
        assert count > 20  # справочник на месте, просто без почт


def test_default_person_fetch_uses_shared_verified_tls_context(monkeypatch):
    expected_context = ssl.create_default_context()
    captured: dict[str, object] = {}

    class Response:
        text = "<html></html>"

        @staticmethod
        def raise_for_status():
            return None

    def fake_get(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return Response()

    monkeypatch.setattr(
        econ_staff_runner, "make_sfedu_ssl_context", lambda: expected_context
    )
    monkeypatch.setattr(httpx, "get", fake_get)

    assert econ_staff_runner._default_fetch("https://sfedu.ru/s7/person/ru/test")
    assert captured["verify"] is expected_context


def test_known_email_query_releases_connection_before_slow_fetch(monkeypatch):
    events: list[str] = []

    class Result:
        @staticmethod
        def all():
            return []

    class Session:
        def execute(self, _statement):
            events.append("execute")
            return Result()

        def rollback(self):
            events.append("rollback")

        def add_all(self, _rows):
            events.append("add_all")

        def flush(self):
            events.append("flush")

    rows = [
        Contact(
            section="Преподаватели",
            name="Иванов Иван Иванович",
            source=ContactSource.ECON_SITE,
        )
    ]
    people = [
        econ_staff.Person(
            name="Иванов Иван Иванович",
            role="Доцент",
            profile_url="https://sfedu.ru/s7/person/ru/test",
        )
    ]
    monkeypatch.setattr(econ_staff_runner, "collect", lambda _fetch: (rows, people))

    def slow_network_phase(*_args, **_kwargs):
        assert "rollback" in events
        events.append("network")
        return 1

    monkeypatch.setattr(econ_staff_runner, "fill_emails", slow_network_phase)

    assert econ_staff_runner.sync(Session(), fetch=lambda _url: "") == 1
    assert events.index("rollback") < events.index("network")


def test_zero_emails_alerts_admin(db_session, monkeypatch):
    """«0 почт из 85» обязано быть слышно.

    Именно этот сигнал поймал реальный сбой: личные страницы sfedu.ru не
    открывались из-за проверки сертификата, и без алерта справочник тихо
    обновился бы без единой почты.
    """
    alerts: list[str] = []
    monkeypatch.setattr(
        econ_staff_runner, "notify_admin", lambda text: alerts.append(text)
    )

    def no_person_pages(url: str) -> str:
        if url == econ_staff.DEANERY_URL:
            return _fx("about-us.html")
        if url == econ_staff.DEPARTMENTS_URL:
            return _fx("kafedry.html")
        # Осторожно с подстрокой: "sfedu.ru" входит и в "econ-sfedu.ru".
        if "sfedu.ru/s7/person" in url or "stat_pages22" in url:
            raise RuntimeError("сертификат не проверился")
        return _fx("kafedra-teoria.html")

    count = econ_staff_runner.sync(
        db_session, fetch=no_person_pages, sleep=lambda _: None
    )

    assert count > 20  # справочник обновлён
    assert any("ни одной почты" in a for a in alerts)


def test_only_personal_pages_are_fetched():
    """Страницы кафедр — не личные страницы, ходить за почтой туда незачем."""
    from src.parsers.econ_staff import Person

    urls = econ_staff_runner._person_page_urls(
        [
            Person(name="А Б В", role="", profile_url="https://sfedu.ru/s7/person/ru/x"),
            # Старый формат мёртв (404 у всех id) — за ним не ходим.
            Person(
                name="Г Д Е",
                role="",
                profile_url="https://sfedu.ru/www/stat_pages22.show?p=UNI/s1/D",
            ),
            # Подстрока "sfedu.ru" тут есть, но это страница кафедры.
            Person(
                name="Ж З И",
                role="",
                profile_url="https://econ-sfedu.ru/pages/kafedry.html",
            ),
            Person(name="К Л М", role="", profile_url=None),
        ]
    )

    assert set(urls) == {"А Б В"}


def test_phones_are_not_stored(db_session):
    """Телефоны с сайта не сохраняем.

    На econ-sfedu.ru у деканата указан общий коммутатор с добавочным
    (+78632184000-13009): набирается только основной номер, добавочный всё
    равно приходится донабирать вручную — пользы от такой кнопки нет.
    Поле phone у контакта остаётся: админ может вписать нормальный номер.
    """
    econ_staff_runner.sync(db_session, fetch=_fetch_ok, with_emails=False)

    phones = db_session.scalars(
        select(Contact.phone).where(Contact.source == ContactSource.ECON_SITE)
    ).all()
    assert all(p is None for p in phones)


def test_overrides_survive_resync(db_session):
    """Скрытие человека переживает повторный автозабор.

    Автозабор льёт contacts заново, но правки справочника живут в отдельной
    таблице и применяются на чтении — поэтому скрытый человек не возвращается,
    сколько бы раз ни синкали.
    """
    from src.models import DirectoryOverride
    from src.persons.directory import build_directory

    econ_staff_runner.sync(db_session, fetch=_fetch_ok, with_emails=False)
    db_session.add(DirectoryOverride(match_name="Вольчик В.В.", hidden=True))
    db_session.flush()
    assert "Вольчик В.В." not in {p.short_name for p in build_directory(db_session)}

    # повторный синк — правка на месте
    econ_staff_runner.sync(db_session, fetch=_fetch_ok, with_emails=False)
    assert "Вольчик В.В." not in {p.short_name for p in build_directory(db_session)}
