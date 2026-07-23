"""Версионный гейт приложения.

После публикации в магазинах это единственный способ вывести из оборота
сломанную/несовместимую версию клиента: приложение на старте спрашивает
min_build, и если его build ниже — показывает блокирующий экран «обновитесь».
По умолчанию min_build=1, то есть ничего не заблокировано.
"""

from fastapi import APIRouter

from src.config import settings

router = APIRouter()


@router.get("/version")
def version() -> dict:
    return {"min_build": settings.min_app_build}
