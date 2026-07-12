def test_settings_read_from_env():
    from src.config import settings

    assert settings.database_url == "sqlite://"
    assert settings.admin_username == "admin"
    assert settings.admin_password == "test-password"
    assert settings.secret_key == "test-secret"
