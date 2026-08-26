# Развёртывание бэкенда в продакшене

Для закрытой Android-беты без домена и VPS есть отдельный бесплатный вариант:
[`DEPLOY_FREE_BETA.md`](DEPLOY_FREE_BETA.md). Этот документ ниже остаётся
рекомендуемым вариантом для постоянного публичного сервиса.

Стек: Caddy (авто-HTTPS) → FastAPI (api) → PostgreSQL (db), всё в Docker Compose.
Публично доступны только `https://ВАШ_ДОМЕН/api` и `/health`; БД и админка
наружу не выставлены.

## 1. Сервер

- Любой VPS с Docker и Docker Compose v2 (2 ГБ RAM достаточно).
- Домен, A-запись которого указывает на IP сервера (нужен для HTTPS от Let's
  Encrypt). Порты 80 и 443 открыты.

## 2. Настройка

```bash
git clone <репозиторий> && cd backend
cp .env.example .env
```

В `.env` задайте (обязательно — свои, не dev-значения):

```
DOMAIN=econ.example.ru
DB_PASSWORD=<длинный случайный пароль>
ADMIN_PASSWORD=<длинный случайный пароль админки>
SECRET_KEY=<длинная случайная строка>            # openssl rand -hex 32
ANTHROPIC_API_KEY=sk-ant-...                      # опционально (без него — заглушка)
TELEGRAM_ALERT_BOT_TOKEN=...                       # опционально: алерты о сбоях
TELEGRAM_ALERT_CHAT_ID=...
```

## 3. Запуск

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

Миграции применяются автоматически при старте `api`. Caddy сам получит
сертификат. Проверка: `curl https://ВАШ_ДОМЕН/health` → `{"status":"ok"}`.

Демо-данные не нужны — расписание/новости/контакты наполнит фоновый парсер
(`ENABLE_SCHEDULER=1` уже включён в prod-compose). Первый цикл импорта
расписания идёт ~15 минут (29 файлов при Crawl-delay 30).

## 4. Приложение → этот бэкенд

Сборка клиента с прод-URL:

```bash
flutter build apk    --dart-define=API_BASE_URL=https://ВАШ_ДОМЕН
flutter build ipa    --dart-define=API_BASE_URL=https://ВАШ_ДОМЕН
```

## 5. Админка (sqladmin)

В интернет не выставлена намеренно. Доступ — через SSH-туннель:

```bash
# временно добавьте к сервису api в compose: ports: ["127.0.0.1:8000:8000"]
ssh -L 8000:localhost:8000 user@server
# затем локально открыть http://localhost:8000/admin
```

либо ограничьте свой IP в `Caddyfile` (закомментированный блок `@admin`).

## 6. Бэкапы

```bash
crontab -e
# 0 3 * * * /path/to/backend/scripts/backup.sh >> /var/log/sfedu-backup.log 2>&1
```

Дампы кладутся в `/var/backups/sfedu-econ` (настраивается `BACKUP_DIR`), хранятся
`BACKUP_KEEP_DAYS` дней (по умолчанию 14). Восстановление — см. шапку
`scripts/backup.sh`.

## 7. Обновление

```bash
git pull
docker compose -f docker-compose.prod.yml up -d --build
```

## Хардининг, уже заложенный

- api-контейнер работает от непривилегированного пользователя, healthcheck на
  `/health`, `restart: always`, лимит памяти.
- БД без проброса порта на хост, пароль из env (не dev `sfedu:sfedu`).
- `pool_pre_ping` в SQLAlchemy — переживает перезапуск БД.
- Помощник: глобальный суточный потолок вызовов (защита бюджета ключа).
- Парсеры: Crawl-delay 30, изоляция ошибок, алерты в Telegram.
