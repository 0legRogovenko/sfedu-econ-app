"""Fallback-справочник с официальной страницы сотрудников ЮФУ."""

from __future__ import annotations

import importlib
import importlib.util

from sqlalchemy import select

from src.models import Contact
from src.parsers import econ_staff, econ_staff_runner

STAFF_HTML = """
<html><body><table>
  <tr class="tr1">
    <td><a href="//sfedu.ru/s7/person/ru/nakosolapova">Косолапова Наталья Алексеевна<a></td>
    <td>Декан</td><td>+7(863) 218-40-00 доб.13000</td>
    <td class="login">nakosolapova</td>
  </tr>
  <tr class="tr2">
    <td><a href="//sfedu.ru/s7/person/ru/volchik">Вольчик Вячеслав Витальевич<a></td>
    <td>Заведующий кафедрой</td><td>+7(863) 218-40-00 доб.13015</td>
    <td class="login">volchik</td>
  </tr>
  <tr class="tr1">
    <td><a href="//sfedu.ru/s7/person/ru/no-mail">Безпочты Иван Иванович<a></td>
    <td>Доцент</td><td></td><td class="login"></td>
  </tr>
</table></body></html>
"""


def _module():
    spec = importlib.util.find_spec("src.parsers.sfedu_staff")
    assert spec is not None, "нет fallback-парсера официального списка ЮФУ"
    return importlib.import_module("src.parsers.sfedu_staff")


def test_parses_names_roles_profiles_and_login_emails():
    staff = _module().parse_staff_page(STAFF_HTML)

    assert [(person.name, person.role, person.email) for person in staff] == [
        ("Косолапова Наталья Алексеевна", "Декан", "nakosolapova@sfedu.ru"),
        ("Вольчик Вячеслав Витальевич", "Заведующий кафедрой", "volchik@sfedu.ru"),
        ("Безпочты Иван Иванович", "Доцент", None),
    ]
    assert staff[1].profile_url == "https://sfedu.ru/s7/person/ru/volchik"


def test_ignores_phone_numbers_entirely():
    staff = _module().parse_staff_page(STAFF_HTML)

    assert all(not hasattr(person, "phone") for person in staff)


def test_empty_or_broken_page_is_not_mistaken_for_a_directory():
    assert _module().parse_staff_page("Fatal error: broken PHP") == []


def test_runner_falls_back_to_sfedu_and_keeps_deanery_first(db_session):
    sfedu_staff = _module()

    def fetch(url: str) -> str:
        if url in (econ_staff.DEANERY_URL, econ_staff.DEPARTMENTS_URL):
            return "Fatal error: Undefined constant DIR"
        if url == sfedu_staff.STAFF_URL:
            return STAFF_HTML
        raise AssertionError(f"unexpected URL: {url}")

    count = econ_staff_runner.sync(
        db_session,
        fetch=fetch,
        with_emails=False,
    )

    assert count == 3
    contacts = db_session.scalars(select(Contact).order_by(Contact.name)).all()
    by_name = {contact.name: contact for contact in contacts}
    assert by_name["Косолапова Наталья Алексеевна"].section == "Деканат"
    assert by_name["Вольчик Вячеслав Витальевич"].section == "Преподаватели"
    assert by_name["Вольчик Вячеслав Витальевич"].email == "volchik@sfedu.ru"
    assert all(contact.phone is None for contact in contacts)
