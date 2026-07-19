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

    GET /api/groups                      — группы по курсам и уровням
    GET /api/teachers                    — преподаватели ({id, full_name})
    GET /api/schedule?group_id=<id>      — расписание группы (вся неделя)
    GET /api/schedule?teacher_id=<id>    — расписание преподавателя
    GET /api/exams?group_id=<id>         — ближайшая сессия группы
    GET /api/news?before=<iso>&before_id=<id>&limit=20 — новости, keyset-пагинация
    GET /api/contacts                    — справочник контактов

Единственная не-GET ручка:

    POST /api/assistant/ask              — {question, device_id} → {answer, fallback}

Демо-данные: `python -m src.seed` (идемпотентно; в Docker —
`docker compose exec api python -m src.seed`).

## Справочник сотрудников

Деканат и составы кафедр забираются с сайта факультета:

    python -m src.parsers.econ_staff_runner

Источники — `econ-sfedu.ru/pages/about-us.html` (деканат) и
`.../kafedry.html` (каталог кафедр, оттуда ссылки на 8 страниц). На сайте
две разные вёрстки карточек сотрудника, поддержаны обе.

Автозабор владеет ТОЛЬКО строками с `contacts.source='econ_site'` и при
каждом запуске заменяет именно их. Всё, что админ завёл руками
(`source='manual'`), не трогается — на сайте факультета нет ни кабинетов,
ни часов приёма, ни личных почт, и заполнить их можно только через админку.

Если разбор дал ноль записей, замена ОТМЕНЯЕТСЯ и уходит алерт: пустой
ответ сайта не должен обнулять справочник.

## AI-помощник

Переменные окружения:

    ANTHROPIC_API_KEY=sk-ant-...   # опционально
    ASSISTANT_MODEL=claude-haiku-4-5
    ASSISTANT_DAILY_LIMIT=20

**Без ключа бэкенд полностью работоспособен**: `/api/assistant/ask` отвечает
200 с заглушкой «Сейчас не могу ответить» и контактами деканата из базы —
тем же текстом, что и при недоступности Claude API. Квоту тратит только
реальный ответ модели: сбой на нашей стороне не съедает лимит студента.

Лимит — 20 вопросов на `device_id` за скользящие 24 часа (не за календарный
день): границу окна считает та же СУБД, что пишет `assistant_logs.created_at`,
поэтому часы приложения и БД не могут разойтись.

База знаний (`kb_articles`) наполняется вручную в админке; `assistant_logs`
показывает, каких статей не хватает. Системный промпт = инструкция + все
статьи + контакты; на него ставится `cache_control: ephemeral`, но у
`claude-haiku-4-5` кэш включается только с 4096 токенов — пока база знаний
маленькая, он тихо не срабатывает (`usage.cache_creation_input_tokens` = 0,
платим полную цену input, при haiku это копейки). Заработает сам, когда база
дорастёт. Отсюда же требование к промпту: он должен быть байт-в-байт
стабильным, поэтому в нём нет дат и id, а статьи и контакты сортируются.

## Фоновые задачи

Планировщик (парсер новостей и импорт расписания) по умолчанию ВЫКЛЮЧЕН —
иначе он стартовал бы в тестах и при alembic. В контейнере `api` он включён
через `ENABLE_SCHEDULER=1` в docker-compose.yml.

    ENABLE_SCHEDULER=1          # без неё бэкенд не забирает ни новостей, ни расписания
    NEWS_POLL_MINUTES=30
    SCHEDULE_IMPORT_HOURS=24    # один цикл — 29 файлов при Crawl-delay: 30
    STAFF_IMPORT_HOURS=24       # справочник кафедр и деканата с econ-sfedu.ru

О падении парсеров можно получать уведомления в Telegram; если переменные не
заданы, сообщения идут только в лог:

    TELEGRAM_ALERT_BOT_TOKEN=
    TELEGRAM_ALERT_CHAT_ID=

## Разработка локально

    python3 -m venv venv && source venv/bin/activate
    pip install -r requirements.txt
    cp .env.example .env   # DATABASE_URL уже указывает на localhost:5433
    docker compose up -d db
    alembic upgrade head
    uvicorn src.main:app --reload

Так поднятый бэкенд слушает только 127.0.0.1 и НЕ выполняет фоновых задач.
Чтобы забирал новости и расписание — `ENABLE_SCHEDULER=1 uvicorn ...`; чтобы
был виден с телефона в той же сети — `--host 0.0.0.0` (см. app/README).

## Тесты

    pytest -v

## Миграции

    alembic revision --autogenerate -m "описание"
    alembic upgrade head
