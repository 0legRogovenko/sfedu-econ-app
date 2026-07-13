from fastapi import APIRouter

from src.api import groups, schedule

router = APIRouter(prefix="/api")
router.include_router(groups.router)
router.include_router(schedule.router)
