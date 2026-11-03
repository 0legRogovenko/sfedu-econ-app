"""Подтверждённые пользователем правки единого справочника."""

from __future__ import annotations

import importlib
import importlib.util

from sqlalchemy import select

from src.models import Contact, DirectoryOverride
from src.persons.directory import build_directory


def _module():
    spec = importlib.util.find_spec("src.directory_seed")
    assert spec is not None, "нет идемпотентного seed подтверждённых почт"
    return importlib.import_module("src.directory_seed")


def test_seed_is_idempotent_and_keeps_unrelated_admin_override(db_session):
    db_session.add(DirectoryOverride(match_name="Админов А.А.", hidden=True))
    db_session.flush()

    directory_seed = _module()
    first = directory_seed.seed_directory_overrides(db_session)
    second = directory_seed.seed_directory_overrides(db_session)

    rows = db_session.scalars(select(DirectoryOverride)).all()
    assert first == second == 13
    assert len(rows) == 14
    assert any(row.match_name == "Админов А.А." for row in rows)


def test_seed_contains_every_confirmed_email_and_two_hidden_names(db_session):
    directory_seed = _module()
    directory_seed.seed_directory_overrides(db_session)

    rows = {
        row.match_name: row
        for row in db_session.scalars(select(DirectoryOverride)).all()
    }
    assert {name: row.email for name, row in rows.items() if row.email} == {
        "Фролова И.В.": "ifrolova@sfedu.ru",
        "Никитаева А.Ю.": "aunikitaeva@sfedu.ru",
        "Елецкий А.Н.": "eletskii@sfedu.ru",
        "Туманян Ю.Р.": "yrtumanyan@sfedu.ru",
        "Скачкова Л.С.": "lsskachkova@sfedu.ru",
        "Полховская Т.Ю.": "tpolhovskaya@sfedu.ru",
        "Маслюкова Е.В.": "maslyukova@sfedu.ru",
        "Барсукова А.В.": "ovbarsukova@sfedu.ru",
        "Вольчик В.В.": "volchik@sfedu.ru",
        "Максютова Л.В.": "maksiutova@sfedu.ru",
        "Педченко Е.А.": "eafedortsova@sfedu.ru",
    }
    assert rows["Погорелова Т.Г."].hidden is True
    assert rows["Потракаева"].hidden is True


def test_surname_only_hidden_override_removes_person(db_session):
    db_session.add(
        Contact(
            section="Преподаватели",
            name="Потракаева Анна Ивановна",
            role="Доцент",
        )
    )
    db_session.flush()
    _module().seed_directory_overrides(db_session)

    assert all(
        person.short_name != "Потракаева А.И." for person in build_directory(db_session)
    )
