from fastapi import APIRouter

from src.api import groups

router = APIRouter(prefix="/api")
router.include_router(groups.router)
