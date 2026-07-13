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

## API

Read-only ручки для приложения (все отдают ETag, поддерживают If-None-Match):

    GET /api/groups                      — группы по курсам
    GET /api/schedule?group_id=<id>      — расписание группы (вся неделя)
    GET /api/schedule?teacher_id=<id>    — расписание преподавателя
    GET /api/news?before=<iso>&before_id=<id>&limit=20 — новости, keyset-пагинация
    GET /api/contacts                    — справочник контактов

Демо-данные: `python -m src.seed` (идемпотентно; в Docker —
`docker compose exec api python -m src.seed`).

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
