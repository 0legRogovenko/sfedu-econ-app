from fastapi import APIRouter

from src.api import contacts, groups, news, schedule

router = APIRouter(prefix="/api")
router.include_router(groups.router)
router.include_router(schedule.router)
router.include_router(news.router)
router.include_router(contacts.router)
