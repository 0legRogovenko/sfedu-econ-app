"""Золотой эталон корпуса: сигнатуры импортированных пар СНАРУЖИ парсера.

prove() перепарсивает ячейку тем же parse_cell — он ловит любое расхождение
импортёра с парсером, но слеп к мутации самого парсера: соврут оба одинаково —
инвариант сойдётся. Эталон закрывает эту дыру с другой стороны: фикстурный
JSON хранит для каждого извлекаемого документа число пар/экзаменов/unparsed и
полные отсортированные сигнатуры пар (плюс их хэш). Данные в нём — внешний
факт, зафиксированный человеком, и никакая правка кода его не сдвинет.

Сигнатура нарочно без БД-шных id: группа — это (курс, номер, программа),
преподаватель — ФИО, модуль — даты. Прогон на чистой in-memory базе даёт
байт-в-байт тот же список.

Регенерация — ТОЛЬКО scripts/regen_golden.py, и только осознанно.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from sqlalchemy import func, select

from src.models import ExamEvent, Lesson, UnparsedCell

GOLDEN_PATH = Path(__file__).parent / "fixtures" / "schedule" / "golden.json"


def document_golden(session, document) -> dict:
    """Снимок документа для сверки с эталоном: счётчики + сигнатуры пар."""
    lessons = session.scalars(
        select(Lesson).where(Lesson.document_id == document.id)
    ).all()
    signatures = sorted(lesson_signature(lesson) for lesson in lessons)
    return {
        "lessons": len(lessons),
        "exams": _count(session, ExamEvent, document),
        "unparsed": _count(session, UnparsedCell, document),
        "hash": signatures_hash(signatures),
        "signatures": signatures,
    }


def lesson_signature(lesson) -> str:
    """Одна пара одной строкой, стабильной между прогонами и без id."""
    group = lesson.group
    module = lesson.module
    teacher = lesson.teacher
    return "|".join(
        (
            f"группа={group.course}/{group.number or ''}/{group.program or ''}",
            f"день={lesson.weekday}",
            f"пара={lesson.pair_number}",
            f"предмет={lesson.subject}",
            f"препод={teacher.full_name if teacher else ''}",
            f"ауд={lesson.room or ''}",
            f"неделя={lesson.week_type.value if lesson.week_type else ''}",
            f"п/г={lesson.subgroup}",
            f"модуль={module.date_from}..{module.date_to}" if module else "модуль=",
            f"даты={lesson.date_constraint_raw or ''}",
        )
    )


def signatures_hash(signatures: list[str]) -> str:
    return hashlib.sha256("\n".join(signatures).encode("utf-8")).hexdigest()


def _count(session, model, document) -> int:
    return session.scalar(
        select(func.count()).select_from(model).where(model.document_id == document.id)
    )
