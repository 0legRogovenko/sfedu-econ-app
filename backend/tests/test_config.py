import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url


@pytest.mark.parametrize(
    "scheme",
    ["postgres", "postgresql", "postgresql+psycopg", "postgresql+psycopg2"],
)
def test_postgres_connection_urls_use_the_installed_driver(scheme):
    from src.config import Settings

    configured = Settings(
        database_url=(
            f"{scheme}://user:p%40ss%25word@database.example:5432/app"
            "?sslmode=require&channel_binding=require"
        ),
        _env_file=None,
    )

    url = make_url(configured.database_url)
    assert url.drivername == "postgresql+psycopg2"
    assert (url.username, url.password, url.host, url.port, url.database) == (
        "user",
        "p@ss%word",
        "database.example",
        5432,
        "app",
    )
    assert dict(url.query) == {"sslmode": "require", "channel_binding": "require"}

    # Building an engine imports its DBAPI but does not connect to the server.
    engine = create_engine(configured.database_url)
    assert engine.dialect.driver == "psycopg2"
    engine.dispose()


def test_sqlite_connection_url_is_unchanged():
    from src.config import Settings

    configured = Settings(database_url="sqlite://", _env_file=None)

    assert configured.database_url == "sqlite://"


def test_settings_read_from_env():
    from src.config import settings

    assert settings.database_url == "sqlite://"
    assert settings.admin_username == "admin"
    assert settings.admin_password == "test-password"
    assert settings.secret_key == "test-secret"


def test_admin_can_be_disabled_from_environment(monkeypatch):
    from src.config import Settings

    monkeypatch.setenv("ADMIN_ENABLED", "0")

    configured = Settings(_env_file=None)

    assert configured.admin_enabled is False


def test_admin_is_disabled_by_default(monkeypatch):
    from src.config import Settings

    monkeypatch.delenv("ADMIN_ENABLED", raising=False)

    configured = Settings(_env_file=None)

    assert configured.admin_enabled is False


def test_compose_deployments_explicitly_enable_admin():
    from pathlib import Path

    backend = Path(__file__).resolve().parents[1]

    for filename in ("docker-compose.yml", "docker-compose.prod.yml"):
        compose = (backend / filename).read_text()
        assert "ADMIN_ENABLED: ${ADMIN_ENABLED:-1}" in compose
