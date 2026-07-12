from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg2://sfedu:sfedu@localhost:5432/sfedu_econ"
    admin_username: str = "admin"
    admin_password: str = "change-me"
    secret_key: str = "dev-secret-change-me"


settings = Settings()
