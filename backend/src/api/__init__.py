from fastapi import APIRouter

from src.api import assistant, contacts, exams, groups, news, schedule, teachers

router = APIRouter(prefix="/api")
router.include_router(groups.router)
router.include_router(teachers.router)
router.include_router(schedule.router)
router.include_router(exams.router)
router.include_router(news.router)
router.include_router(contacts.router)
router.include_router(assistant.router)
