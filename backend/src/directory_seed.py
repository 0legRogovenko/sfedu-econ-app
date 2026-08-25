"""Идемпотентные правки справочника, подтверждённые владельцем приложения.

Автозабор может сколько угодно заменять `contacts`: этот слой живёт отдельно
и применяется при чтении единого справочника. Неизвестные админские правки не
удаляются.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models import DirectoryOverride


CURATED_DIRECTORY_OVERRIDES: tuple[tuple[str, str | None, bool], ...] = (
    ("Фролова И.В.", "ifrolova@sfedu.ru", False),
    ("Никитаева А.Ю.", "aunikitaeva@sfedu.ru", False),
    ("Елецкий А.Н.", "eletskii@sfedu.ru", False),
    ("Туманян Ю.Р.", "yrtumanyan@sfedu.ru", False),
    ("Скачкова Л.С.", "lsskachkova@sfedu.ru", False),
    ("Полховская Т.Ю.", "tpolhovskaya@sfedu.ru", False),
    ("Маслюкова Е.В.", "maslyukova@sfedu.ru", False),
    ("Барсукова А.В.", "ovbarsukova@sfedu.ru", False),
    ("Вольчик В.В.", "volchik@sfedu.ru", False),
    ("Максютова Л.В.", "maksiutova@sfedu.ru", False),
    ("Педченко Е.А.", "eafedortsova@sfedu.ru", False),
    ("Погорелова Т.Г.", None, True),
    # В доступных актуальных источниках этой строки уже нет. Скрытие по
    # фамилии оставлено, чтобы устаревший кэш/будущий импорт не вернул запись.
    ("Потракаева", None, True),
)


def seed_directory_overrides(session: Session) -> int:
    """Создаёт или обновляет только известные правки, прочие не трогает."""
    for match_name, email, hidden in CURATED_DIRECTORY_OVERRIDES:
        row = session.scalar(
            select(DirectoryOverride)
            .where(DirectoryOverride.match_name == match_name)
            .limit(1)
        )
        if row is None:
            row = DirectoryOverride(match_name=match_name)
            session.add(row)
        row.email = email
        row.hidden = hidden

    session.flush()
    return len(CURATED_DIRECTORY_OVERRIDES)
