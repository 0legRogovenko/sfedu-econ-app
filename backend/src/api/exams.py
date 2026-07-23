from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import nulls_last, select
from sqlalchemy.orm import Session

from src.api.etag import json_with_etag
from src.database import get_db
from src.models import ExamEvent, Group
from src.renames import apply_renames
from src.schemas import ExamEventOut

router = APIRouter()


@router.get("/exams", response_model=list[ExamEventOut])
def list_exams(
    request: Request,
    response: Response,
    group_id: int,
    db: Session = Depends(get_db),
):
    if db.get(Group, group_id) is None:
        raise HTTPException(status_code=404, detail="Группа не найдена")

    exams = db.scalars(
        select(ExamEvent)
        .where(ExamEvent.group_id == group_id)
        # exam_at=None — неразобранная дата (дыра источника): в конец списка,
        # а не в начало (дефолт SQLite/Postgres для NULL расходится — фиксируем).
        # id — стабильный тайбрейкер: детерминированный порядок => стабильный ETag
        .order_by(nulls_last(ExamEvent.exam_at.asc()), ExamEvent.id)
    ).all()
    payload = [ExamEventOut.model_validate(e).model_dump(mode="json") for e in exams]
    apply_renames(db, payload)
    return json_with_etag(request, response, payload)
