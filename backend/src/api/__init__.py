from fastapi import APIRouter

from src.api import assistant, contacts, exams, groups, news, persons, schedule, version

router = APIRouter(prefix="/api")
router.include_router(groups.router)
router.include_router(persons.router)
router.include_router(schedule.router)
router.include_router(exams.router)
router.include_router(news.router)
router.include_router(contacts.router)
router.include_router(assistant.router)
router.include_router(version.router)
