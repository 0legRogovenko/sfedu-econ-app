# Бесплатный HTTPS-бэкенд для закрытой Android-беты

Этот вариант предназначен только для личного некоммерческого фокус-теста:

```
Flutter APK -> https://econ-yufu-api.vercel.app -> Neon PostgreSQL
                                                   ^
                                                   |
                                    GitHub Actions: ежедневный импорт
```

Vercel выдаёт постоянный HTTPS-поддомен `*.vercel.app`; отдельный домен и VPS
не нужны. Web API работает как serverless FastAPI-функция, а долгие парсеры
PDF/DOCX/HTML запускаются отдельным workflow и пишут в ту же БД.

## 1. Neon Free

1. Войти в Neon через GitHub и создать проект `econ-yufu-beta` в европейском
   регионе (Frankfurt / AWS `eu-central-1`).
2. Сохранить два connection string только в менеджерах секретов:
   - **pooled** URL — для Vercel `DATABASE_URL`;
   - **direct** URL — для GitHub Environment `backend-beta`, secret
     `DATABASE_URL` (миграции и импорт).
3. Оба URL должны требовать TLS (`sslmode=require`). Не записывать их в `.env`,
   коммиты, issue, PR или логи.

## 2. Vercel Hobby

Импортировать публичный репозиторий `0legRogovenko/sfedu-econ-app` как новый
проект:

- Project Name: `econ-yufu-api` (если имя свободно, адрес будет
  `https://econ-yufu-api.vercel.app`);
- Root Directory: `backend`;
- Framework Preset: FastAPI или автоопределение;
- Production Branch: `main`.

Задать переменные Production:

| Переменная | Значение |
|---|---|
| `DATABASE_URL` | pooled URL Neon |
| `ADMIN_PASSWORD` | случайная строка; admin всё равно отключён |
| `SECRET_KEY` | отдельная случайная строка |
| `ADMIN_ENABLED` | `0` |
| `ENABLE_SCHEDULER` | `0` |
| `ANTHROPIC_API_KEY` | опционально; без ключа работает честный fallback |

`app.py` экспортирует существующее FastAPI-приложение, `vercel.json` закрепляет
регион `fra1`, 60-секундный предел запроса и исключает 18 МБ тестового корпуса
расписаний из serverless bundle. При `ADMIN_ENABLED=0` маршрут `/admin` вообще
не монтируется.

## 3. Автообновление данных

В GitHub создать Environment `backend-beta`, ограничить его deployment branches
веткой `main` и добавить только secret `DATABASE_URL` с **direct** URL Neon. Workflow
`.github/workflows/backend-beta-sync.yml`:

1. применяет `alembic upgrade head`;
2. обновляет новости и единый справочник людей;
3. забирает официальное расписание ЮФУ;
4. выполняется ежедневно в 03:17 МСК и вручную через Actions.

Источники выполняются независимо, но workflow завершается ошибкой, если хотя
бы один из них упал. Пустая официальная страница расписания не стирает старые
данные; выпуск APK всё равно запрещён gate-ом из `BETA_TESTING.md`.

Если индекс ЮФУ открывается, но сервер обрывает тела PDF, вручную запускается
`Import validated schedule snapshot`. Это отдельный аварийный workflow без
cron: он берёт последний просмотренный официальный набор из
`backend/data/schedule_snapshot/2026-08-28`, до обращения к БД проверяет размер
и SHA-256 каждого файла, импортирует семь документов одной транзакцией и
фиксирует её только при точных счётчиках 39 групп, 608 пар и 120 недель.
Ежедневный live-sync при этом не переводится в режим fallback: после
восстановления сайта он снова обязан скачать и проверить актуальные файлы.

## 4. Проверка стенда

После первого deploy и ручного запуска sync-workflow:

```bash
curl --fail-with-body https://econ-yufu-api.vercel.app/health
curl --fail-with-body https://econ-yufu-api.vercel.app/api/version
curl -i https://econ-yufu-api.vercel.app/admin/
```

Ожидания: `/health` возвращает `{"status":"ok"}`, `/api/version` — JSON, а
`/admin/` — `404`.

Затем в GitHub Environment `android-beta` задать variable:

```
BETA_API_BASE_URL=https://econ-yufu-api.vercel.app
```

и запускать **Android beta APK** только после прохождения всех пунктов
`BETA_TESTING.md` на актуальном расписании ЮФУ.

## Ограничения бесплатного стенда

- Vercel Hobby разрешён для личных некоммерческих проектов и не даёт SLA.
- Neon Free автоматически усыпляет compute при простое; первый запрос может
  быть медленнее последующих.
- Это стенд фокус-группы, не инфраструктура публичного релиза. Для открытого
  запуска остаётся VPS-вариант из `DEPLOY.md` с бэкапами и закрытой админкой.
