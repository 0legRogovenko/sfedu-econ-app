from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy import select, tuple_
from sqlalchemy.orm import Session

from src.api.etag import json_with_etag
from src.database import get_db
from src.models import News
from src.schemas import NewsOut

router = APIRouter()


@router.get("/news")
def list_news(
    request: Request,
    response: Response,
    before: datetime | None = None,
    before_id: int | None = None,
    limit: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    # Keyset-курсор по паре (published_at, id): курсор только по дате терял бы
    # записи с одинаковым published_at (частый случай у парсеров новостей)
    if (before is None) != (before_id is None):
        raise HTTPException(
            status_code=422,
            detail="Курсор задаётся парой параметров: before и before_id",
        )

    query = (
        select(News)
        .order_by(News.published_at.desc(), News.id.desc())
        .limit(limit)
    )
    if before is not None:
        query = query.where(
            tuple_(News.published_at, News.id) < tuple_(before, before_id)
        )

    items = db.scalars(query).all()
    payload = [NewsOut.model_validate(n).model_dump(mode="json") for n in items]
    return json_with_etag(request, response, payload)
