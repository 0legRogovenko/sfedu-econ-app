from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg2://sfedu:sfedu@localhost:5433/sfedu_econ"
    admin_username: str = "admin"
    admin_password: str
    secret_key: str

    # Планировщик парсеров. Выключен по умолчанию — не стартует в тестах
    # и при alembic; включается в контейнере api (ENABLE_SCHEDULER=1).
    enable_scheduler: bool = False
    news_poll_minutes: int = 30

    # Telegram-алерты о падении парсеров (опционально). Если не заданы —
    # уведомления идут только в лог.
    telegram_alert_bot_token: str | None = None
    telegram_alert_chat_id: str | None = None

    # AI-помощник. Ключ опционален: без него ручка отвечает заглушкой
    # с контактами деканата, а не падает.
    anthropic_api_key: str | None = None
    assistant_model: str = "claude-haiku-4-5"
    assistant_daily_limit: int = 20


settings = Settings()
