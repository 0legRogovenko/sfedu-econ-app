from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from src.api.etag import json_with_etag
from src.database import get_db
from src.models import Group, Lesson, Module, Teacher, WeekCalendar
from src.schemas import LessonOut, ModuleOut, ScheduleOut, WeekCalendarOut

router = APIRouter()


@router.get("/schedule", response_model=ScheduleOut)
def get_schedule(
    request: Request,
    response: Response,
    group_id: int | None = None,
    teacher_id: int | None = None,
    db: Session = Depends(get_db),
):
    if (group_id is None) == (teacher_id is None):
        raise HTTPException(
            status_code=422,
            detail="Укажите ровно один параметр: group_id или teacher_id",
        )

    query = (
        select(Lesson)
        .options(joinedload(Lesson.teacher))
        # week_type и id — стабильные тайбрейкеры: детерминированный порядок => стабильный ETag
        .order_by(
            Lesson.weekday,
            Lesson.pair_number,
            Lesson.subgroup,
            Lesson.week_type,
            Lesson.id,
        )
    )
    if group_id is not None:
        if db.get(Group, group_id) is None:
            raise HTTPException(status_code=404, detail="Группа не найдена")
        query = query.where(Lesson.group_id == group_id)
    else:
        if db.get(Teacher, teacher_id) is None:
            raise HTTPException(status_code=404, detail="Преподаватель не найден")
        query = query.where(Lesson.teacher_id == teacher_id)

    lessons = db.scalars(query).all()

    # Контекст резолвинга «дата → модуль + тип недели» — данные, не формула.
    # Берём ВСЕ модули и календарь документов, откуда приехали пары: клиенту
    # нужны границы и тех модулей, где у группы занятий нет.
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
