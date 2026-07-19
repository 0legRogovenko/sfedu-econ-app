"""Единый справочник людей: один список вместо двух поисков.

GET /api/persons                    — все люди (контакты + преподаватели)
GET /api/persons/{id}/schedule      — расписание человека (та же форма, что
                                      /api/schedule, чтобы клиент рендерил
                                      существующим виджетом)
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from src.api.etag import json_with_etag
from src.database import get_db
from src.models import Lesson, Module, WeekCalendar
from src.persons.directory import (
    build_directory,
    decode_id,
    lessons_for_person,
    person_display,
)
from src.schemas import LessonOut, ModuleOut, ScheduleOut, WeekCalendarOut

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
        key=lambda l: (
            l.weekday,
            l.pair_number,
            l.subgroup,
            l.week_type.value if l.week_type else "",
            l.id,
        )
    )
    # joinedload здесь не нужен: teacher в карточке человека не показываем.

    document_ids = sorted({l.document_id for l in lessons if l.document_id})
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
        lessons=[LessonOut.model_validate(l) for l in lessons],
        modules=[ModuleOut.model_validate(m) for m in modules],
        week_calendar=[WeekCalendarOut.model_validate(w) for w in calendar],
    ).model_dump(mode="json")
    return json_with_etag(request, response, payload)
