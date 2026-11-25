import os
from secrets import token_urlsafe

from fastapi import APIRouter, FastAPI
from sqlalchemy.engine import make_url


def configure_runtime() -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("Configure the read-only DATABASE_URL in project secrets.")

    url = make_url(database_url)
    if url.username != "sfedu_netrun_reader" or url.get_backend_name() not in {
        "postgres",
        "postgresql",
    }:
        raise SystemExit("The Neon read-only role sfedu_netrun_reader is required.")
    if not url.host or not url.host.endswith(".neon.tech"):
        raise SystemExit("The database host must be a Neon Postgres endpoint.")

    url = url.set(drivername="postgresql+psycopg2").update_query_dict(
        {
            "sslmode": "verify-full",
            "sslrootcert": "/etc/ssl/certs/ca-certificates.crt",
            "connect_timeout": "8",
        }
    )
    os.environ.update(
        DATABASE_URL=url.render_as_string(hide_password=False),
        ADMIN_ENABLED="0",
        ENABLE_SCHEDULER="0",
        ADMIN_PASSWORD=token_urlsafe(32),
        SECRET_KEY=token_urlsafe(32),
        ANTHROPIC_API_KEY="",
    )


def create_app() -> FastAPI:
    # These modules load settings at import time.
    configure_runtime()
    from src.api import (
        assistant_upstream,
        contacts,
        exams,
        groups,
        news,
        persons,
        schedule,
        version,
    )
    from src.main import health

    app = FastAPI(title="Эконом ЮФУ", docs_url=None, redoc_url=None, openapi_url=None)
    app.add_api_route("/health", health, methods=["GET"])
    api = APIRouter(prefix="/api")
    for module in (
        contacts,
        exams,
        groups,
        news,
        persons,
        schedule,
        version,
        assistant_upstream,
    ):
        api.include_router(module.router)
    app.include_router(api)
    return app


app = create_app()
