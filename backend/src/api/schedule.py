from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from src.api.etag import json_with_etag
from src.database import get_db
from src.models import Group, Lesson, Teacher
from src.schemas import LessonOut

router = APIRouter()


@router.get("/schedule")
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
        .order_by(Lesson.weekday, Lesson.pair_number, Lesson.subgroup)
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
    payload = [LessonOut.model_validate(l).model_dump(mode="json") for l in lessons]
    return json_with_etag(request, response, payload)
