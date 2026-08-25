import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from src.admin import setup_admin
from src.api import router as api_router
from src.config import settings
from src.database import engine

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = None
    if settings.enable_scheduler:
        # Serverless beta runs imports in GitHub Actions.  Keep the heavy
        # PDF/DOCX parser stack out of API cold starts when scheduling is off.
        from src.scheduler import create_scheduler

        scheduler = create_scheduler()
        scheduler.start()
        logger.info("Планировщик парсеров запущен")
    try:
        yield
    finally:
        if scheduler is not None:
            scheduler.shutdown(wait=False)


app = FastAPI(title="Эконом ЮФУ API", lifespan=lifespan)
setup_admin(app)
app.include_router(api_router)


@app.get("/health")
def health():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"status": "ok"}
