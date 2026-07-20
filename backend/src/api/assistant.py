from datetime import timedelta
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from src.config import settings
from src.database import get_db
from src.models import AssistantLog, Contact, KbArticle
from src.schemas import AskRequest, AskResponse
from src.services.assistant import (
    AskResult,
    AssistantClient,
    build_client,
    build_fallback_answer,
    build_system_prompt,
)

router = APIRouter()


@lru_cache(maxsize=1)
def get_assistant_client() -> AssistantClient | None:
    # lru_cache: клиент создаётся один раз, и предупреждение об отсутствии
    # ключа тоже пишется в лог один раз, а не на каждый вопрос
    return build_client()


def _questions_last_24h(db: Session, device_id: str) -> int:
    # Границу окна считает та же СУБД, что пишет created_at (naive-колонка,
    # server_default=func.now()): рассинхрона часов приложения и БД быть не может
    cutoff = db.scalar(select(func.now())) - timedelta(hours=24)
    return db.scalar(
        select(func.count())
        .select_from(AssistantLog)
        .where(
            AssistantLog.device_id == device_id,
            AssistantLog.created_at >= cutoff,
        )
    )


def _billed_last_24h(db: Session) -> int:
    # Строки AssistantLog пишутся ТОЛЬКО на оплаченный вызов, поэтому их число
    # за 24 часа по всем устройствам = число биллинговых обращений. Служит
    # глобальным потолком бюджета, не завязанным на клиентский device_id.
    cutoff = db.scalar(select(func.now())) - timedelta(hours=24)
    return db.scalar(
        select(func.count())
        .select_from(AssistantLog)
        .where(AssistantLog.created_at >= cutoff)
    )


@router.post("/assistant/ask", response_model=AskResponse)
def ask(
    payload: AskRequest,
    db: Session = Depends(get_db),
    assistant: AssistantClient | None = Depends(get_assistant_client),
):
    if _questions_last_24h(db, payload.device_id) >= settings.assistant_daily_limit:
        raise HTTPException(
            status_code=429,
            detail=(
                f"Можно задать не больше {settings.assistant_daily_limit} вопросов "
                "за 24 часа. Попробуйте позже или обратитесь в деканат."
            ),
        )

    # Глобальный потолок ДО обращения к платной модели: per-device лимит выше
    # обходится сменой device_id на каждый запрос, поэтому нужен предел, не
    # завязанный на клиентский идентификатор, — иначе безлимитная генерация
    # новых device_id жгла бы бюджет ключа (финансовый DoS).
    if _billed_last_24h(db) >= settings.assistant_global_daily_limit:
        raise HTTPException(
            status_code=429,
            detail=(
                "Помощник сейчас перегружен. Попробуйте позже или обратитесь "
                "в деканат."
            ),
        )

    contacts = db.scalars(
        select(Contact).order_by(Contact.section, Contact.id)
    ).all()

    # Ключа нет — вызова не будет, значит и оплаты тоже
    result = AskResult(text=None, billed=False)
    if assistant is not None:
        articles = db.scalars(select(KbArticle).order_by(KbArticle.slug)).all()
        result = assistant.ask(
            build_system_prompt(articles, contacts), payload.question
        )

    # Квоту тратит любой оплаченный вызов, а не только удачный: отказ модели
    # и пустой ответ стоят денег ровно столько же, и без записи в лог ими
    # можно было бы жечь бюджет мимо rate-limit'а. Сбой на нашей стороне
    # (API лёг, ключа нет) вызова не стоил — лимит студента он не съедает.
    answer = result.text if result.text is not None else build_fallback_answer(contacts)

    if result.billed:
        # В лог кладём то, что реально ушло студенту: логи остаются честной
        # историей и сигналом «каких статей не хватает в базе знаний»
        db.add(
            AssistantLog(
                question=payload.question, answer=answer, device_id=payload.device_id
            )
        )
        db.commit()

    return AskResponse(answer=answer, fallback=result.text is None)


@router.delete("/assistant/data")
def forget_device(
    device_id: str = Query(min_length=1, max_length=64),
    db: Session = Depends(get_db),
):
    """Удаляет все логи помощника этого устройства (кнопка «Удалить мои данные»
    в приложении, требование приватности). Идемпотентно: нет строк — deleted 0.
    """
    result = db.execute(
        delete(AssistantLog).where(AssistantLog.device_id == device_id)
    )
    db.commit()
    return {"deleted": result.rowcount}
