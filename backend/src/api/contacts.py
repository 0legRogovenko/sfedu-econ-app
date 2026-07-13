from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.api.etag import json_with_etag
from src.database import get_db
from src.models import Contact
from src.schemas import ContactOut

router = APIRouter()


@router.get("/contacts", response_model=list[ContactOut])
def list_contacts(
    request: Request, response: Response, db: Session = Depends(get_db)
):
    contacts = db.scalars(
        select(Contact).order_by(Contact.section, Contact.sort_order, Contact.name)
    ).all()
    payload = [ContactOut.model_validate(c).model_dump(mode="json") for c in contacts]
    return json_with_etag(request, response, payload)
