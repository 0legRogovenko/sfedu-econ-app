"""Применение кураторских переименований предметов (SubjectRename) к ответам API.

Слой чтения: БД хранит предметы дословно как в исходном файле ЮФУ (это держит
инвариант доказуемости импорта), а наружу уходит выправленное название.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models import SubjectRename


def rename_map(db: Session) -> dict[str, str]:
    rows = db.scalars(select(SubjectRename)).all()
    return {r.match_subject: r.display_subject for r in rows}


def apply_renames(db: Session, items: list[dict]) -> None:
    """Правит поле subject у уже сериализованных словарей (in place)."""
    renames = rename_map(db)
    if not renames:
        return
    for item in items:
        subject = item.get("subject")
        if subject in renames:
            item["subject"] = renames[subject]
