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
    # Импорт расписания: раз в сутки. Чаще незачем — один цикл это 29 файлов
    # по Crawl-delay: 30, то есть ~15 минут вежливого чтения чужого сайта.
    schedule_import_hours: int = 24
    # Справочник сотрудников меняется редко (состав кафедр — раз в семестр),
    # поэтому раз в сутки достаточно с большим запасом.
    staff_import_hours: int = 24

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
