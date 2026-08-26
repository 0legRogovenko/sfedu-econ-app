from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import exists, or_, select
from sqlalchemy.orm import Session

from src.api.etag import json_with_etag
from src.database import get_db
from src.models import ExamEvent, Group, Lesson, ScheduleDocument
from src.schemas import GroupOut

router = APIRouter()


@router.get("/groups", response_model=list[GroupOut])
def list_groups(
    request: Request, response: Response, db: Session = Depends(get_db)
):
    # Порядок детерминированный: уровень → курс → номер (бакалавры) / программа
    # (магистры). level пишется значением ('bachelor' < 'master'), так что
    # бакалавры идут раньше магистров; внутри курса номер разводит бакалаврские
    # группы, а программа — магистерские (у них number NULL и тождествен).
    statement = select(Group)
    if db.scalar(select(ScheduleDocument.id).limit(1)) is not None:
        # После смены учебного года старые строки groups могут остаться без
        # единой пары/экзамена. Не показываем технические сироты в онбординге,
        # но в пустой dev-БД по-прежнему разрешаем ручные группы.
        statement = statement.where(
            or_(
                exists(select(Lesson.id).where(Lesson.group_id == Group.id)),
                exists(
                    select(ExamEvent.id).where(ExamEvent.group_id == Group.id)
                ),
            )
        )
    groups = db.scalars(
        statement.order_by(
            Group.level, Group.course, Group.number, Group.program
        )
    ).all()
    payload = [GroupOut.model_validate(g).model_dump(mode="json") for g in groups]
    return json_with_etag(request, response, payload)
