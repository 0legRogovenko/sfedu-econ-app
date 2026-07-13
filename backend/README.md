# Эконом ЮФУ — бэкенд

FastAPI + PostgreSQL. См. спеку в `../docs/superpowers/specs/`.

## Запуск (Docker)

    cp .env.example .env   # и поменять пароли
    docker compose up -d --build
    # API:     http://localhost:8000/health
    # Админка: http://localhost:8000/admin

Миграции применяются автоматически при старте контейнера api.

БД проброшена на хост как localhost:5433 (5432 часто занят локальным
PostgreSQL). Внутри compose-сети api ходит в db:5432.

## Разработка локально

    python3 -m venv venv && source venv/bin/activate
    pip install -r requirements.txt
    cp .env.example .env   # DATABASE_URL уже указывает на localhost:5433
    docker compose up -d db
    alembic upgrade head
    uvicorn src.main:app --reload

## Тесты

    pytest -v

## Миграции

    alembic revision --autogenerate -m "описание"
    alembic upgrade head
