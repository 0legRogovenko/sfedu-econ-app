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
