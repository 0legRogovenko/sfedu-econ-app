from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy import select
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
    limit: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    query = (
        select(News)
        .order_by(News.published_at.desc(), News.id.desc())
        .limit(limit)
    )
    if before is not None:
        query = query.where(News.published_at < before)

    items = db.scalars(query).all()
    payload = [NewsOut.model_validate(n).model_dump(mode="json") for n in items]
    return json_with_etag(request, response, payload)
