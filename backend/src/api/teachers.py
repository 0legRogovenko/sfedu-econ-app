from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.api.etag import json_with_etag
from src.database import get_db
from src.models import Teacher
from src.schemas import TeacherBrief

router = APIRouter()


@router.get("/teachers", response_model=list[TeacherBrief])
def list_teachers(
    request: Request, response: Response, db: Session = Depends(get_db)
):
    # Просто по строке full_name, локале-независимо: 129 записей, поиск и
    # красивая сортировка — на клиенте. Сдвоенные ФИО («Бутова С.В. /
    # Писанка С.А.») — одна запись, как в ячейке расписания.
    teachers = db.scalars(select(Teacher).order_by(Teacher.full_name)).all()
    payload = [
        TeacherBrief.model_validate(t).model_dump(mode="json") for t in teachers
    ]
    return json_with_etag(request, response, payload)
