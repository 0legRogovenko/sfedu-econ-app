from fastapi import FastAPI
from sqlalchemy import text

from src.database import engine

app = FastAPI(title="Эконом ЮФУ API")


@app.get("/health")
def health():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"status": "ok"}
