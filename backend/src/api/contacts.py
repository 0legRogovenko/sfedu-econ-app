from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import case, select
from sqlalchemy.orm import Session

from src.api.etag import json_with_etag
from src.database import get_db
from src.models import Contact
from src.schemas import ContactOut

router = APIRouter()

DEANERY_SECTION = "Деканат"


@router.get("/contacts", response_model=list[ContactOut])
def list_contacts(
    request: Request, response: Response, db: Session = Depends(get_db)
):
    # Деканат закреплён первым, остальные секции по алфавиту: студенту в первую
    # очередь нужен деканат, а не первая по алфавиту кафедра. Внутри секции
    # порядок задаёт sort_order — им импорт ставит заведующего первым.
    deanery_first = case((Contact.section == DEANERY_SECTION, 0), else_=1)
    contacts = db.scalars(
        select(Contact).order_by(
            deanery_first, Contact.section, Contact.sort_order, Contact.name
        )
    ).all()
    payload = [ContactOut.model_validate(c).model_dump(mode="json") for c in contacts]
    return json_with_etag(request, response, payload)
