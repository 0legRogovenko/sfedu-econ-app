"""Единый справочник людей: один список вместо двух поисков.

GET /api/persons                    — все люди (контакты + преподаватели)
GET /api/persons/{id}/schedule      — расписание человека (та же форма, что
                                      /api/schedule, чтобы клиент рендерил
                                      существующим виджетом)
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select

from src.api.etag import json_with_etag
from src.database import get_db
from src.models import Module, WeekCalendar
from src.persons.directory import (
    build_directory,
    decode_id,
    exams_for_person,
    lessons_for_person,
    person_display,
)
from src.renames import apply_renames
from src.schemas import ExamEventOut, LessonOut, ModuleOut, ScheduleOut, WeekCalendarOut

router = APIRouter()


@router.get("/persons")
def list_persons(request: Request, response: Response, db=Depends(get_db)):
    payload = person_display(build_directory(db))
    return json_with_etag(request, response, payload)


@router.get("/persons/{person_id}/schedule", response_model=ScheduleOut)
def person_schedule(
    person_id: str,
    request: Request,
    response: Response,
    db=Depends(get_db),
):
    key = decode_id(person_id)
    if key is None:
        raise HTTPException(status_code=404, detail="Человек не найден")

    lessons = lessons_for_person(db, key)
    # Детерминированный порядок => стабильный ETag (как в /api/schedule).
    lessons.sort(
        key=lambda lesson: (
            lesson.weekday,
            lesson.pair_number,
            lesson.subgroup,
            lesson.week_type.value if lesson.week_type else "",
            lesson.id,
        )
    )
    # teacher у пар подгружен заранее (joinedload в lessons_for_person):
    # LessonOut его сериализует, иначе был бы N+1 по SELECT на каждую пару.

    document_ids = sorted(
        {lesson.document_id for lesson in lessons if lesson.document_id}
    )
    modules: list[Module] = []
    calendar: list[WeekCalendar] = []
    if document_ids:
        modules = db.scalars(
            select(Module)
            .where(Module.document_id.in_(document_ids))
            .order_by(Module.date_from, Module.date_to, Module.id)
        ).all()
        calendar = db.scalars(
            select(WeekCalendar)
            .where(WeekCalendar.document_id.in_(document_ids))
            .order_by(WeekCalendar.date_from, WeekCalendar.date_to, WeekCalendar.id)
        ).all()

    payload = ScheduleOut(
        lessons=[LessonOut.model_validate(lesson) for lesson in lessons],
        modules=[ModuleOut.model_validate(m) for m in modules],
        week_calendar=[WeekCalendarOut.model_validate(w) for w in calendar],
    ).model_dump(mode="json")
    apply_renames(db, payload["lessons"])
    return json_with_etag(request, response, payload)


@router.get("/persons/{person_id}/exams", response_model=list[ExamEventOut])
def person_exams(
    person_id: str,
    request: Request,
    response: Response,
    db=Depends(get_db),
):
    """Экзамены человека — для карточки в справочнике (у пар есть аналог
    /persons/{id}/schedule; связывание то же — по тексту ячейки)."""
    key = decode_id(person_id)
    if key is None:
        raise HTTPException(status_code=404, detail="Человек не найден")

    exams = exams_for_person(db, key)
    # exam_at=None — в конец; id — стабильный тайбрейкер (стабильный ETag).
    exams.sort(key=lambda e: (e.exam_at is None, e.exam_at or datetime.min, e.id))
    payload = [ExamEventOut.model_validate(e).model_dump(mode="json") for e in exams]
    apply_renames(db, payload)
    return json_with_etag(request, response, payload)
