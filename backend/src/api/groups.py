from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.api.etag import json_with_etag
from src.database import get_db
from src.models import Group
from src.schemas import GroupOut

router = APIRouter()


@router.get("/groups", response_model=list[GroupOut])
def list_groups(
    request: Request, response: Response, db: Session = Depends(get_db)
):
    groups = db.scalars(select(Group).order_by(Group.course, Group.number)).all()
    payload = [GroupOut.model_validate(g).model_dump(mode="json") for g in groups]
    return json_with_etag(request, response, payload)
