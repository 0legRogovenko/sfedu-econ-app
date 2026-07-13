from fastapi import FastAPI
from sqlalchemy import text

from src.admin import setup_admin
from src.api import router as api_router
from src.database import engine

app = FastAPI(title="Эконом ЮФУ API")
setup_admin(app)
app.include_router(api_router)


@app.get("/health")
def health():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"status": "ok"}
