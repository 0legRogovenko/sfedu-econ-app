# Эконом ЮФУ — мобильное приложение

Flutter-клиент. Бэкенд: `../backend` (должен работать на localhost:8000).

## Запуск

    flutter pub get
    flutter run    # симулятор/эмулятор; для устройства см. ниже

Android-эмулятор не видит localhost хоста — использовать:

    flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000

### Реальное устройство

Двух шагов мало: одного `--dart-define` с IP машины НЕ хватит.

1. Бэкенд по умолчанию слушает только 127.0.0.1 — поднимать с
   `uvicorn src.main:app --host 0.0.0.0` (в Docker уже так).
2. На Android cleartext-HTTP разрешён только для `10.0.2.2` и `localhost`
   (`android/app/src/main/res/xml/network_security_config.xml`). IP машины
   надо добавить туда отдельным `<domain>`, иначе запрос молча блокируется
   системой — приложение покажет «нет сети» при живом бэкенде.

    flutter run --dart-define=API_BASE_URL=http://<IP-машины>:8000

### Запуск вне семестра

Летом расписание честно пустое, и проверить экран на живых данных иначе
нельзя. Демо-дата подменяет «сегодня», сохраняя текущее время суток:

    flutter run --dart-define=DEMO_TODAY=2025-09-16

## Тесты и анализ

    flutter test
    flutter analyze

## Подписанная Android-бета

Release-сборка принципиально не использует debug-ключ и не запускается без
явного HTTPS `API_BASE_URL`. Нужны Flutter 3.44.6, JDK 17 и Android SDK с
platform/build-tools 36.

### Локальная подпись

Один раз создайте постоянный upload-ключ. Пароли вводятся интерактивно и не
должны попадать в shell history, Git или переписку:

```bash
keytool -genkeypair -v \
  -keystore upload-keystore.jks \
  -keyalg RSA -keysize 2048 -validity 10000 \
  -alias upload
```

Создайте локальный `android/key.properties` (файл и `*.jks` уже в
`.gitignore`):

```properties
storeFile=/absolute/path/to/upload-keystore.jks
storePassword=<ввести локально>
keyAlias=upload
keyPassword=<ввести локально>
```

Проверьте origin тем же валидатором, который использует CI, затем соберите APK:

```bash
dart tool/validate_beta_url.dart https://beta.example.ru
flutter analyze --no-pub
flutter test --no-pub
flutter build apk --release --no-pub \
  --dart-define=API_BASE_URL=https://beta.example.ru
shasum -a 256 build/app/outputs/flutter-apk/app-release.apk
```

Сборка останавливается, если endpoint пустой, не HTTPS, локальный либо содержит
путь, query, fragment или credentials.

### GitHub Actions

Workflow `.github/workflows/android-beta.yml` запускается вручную или тегом
`beta-v*`. Для GitHub Environment `android-beta` задаются:

- variable `BETA_API_BASE_URL` — только HTTPS-origin;
- secrets `ANDROID_KEYSTORE_BASE64`, `ANDROID_KEYSTORE_PASSWORD`,
  `ANDROID_KEY_ALIAS`, `ANDROID_KEY_PASSWORD`.

`ANDROID_KEYSTORE_BASE64` — base64-содержимое постоянного upload-keystore, а не
новый ключ для каждого билда. Workflow выполняет analyze/test, собирает
подписанный universal APK, добавляет SHA-256 и manifest, затем хранит artifact
7 дней. Он намеренно не создаёт публичный GitHub Release: владелец скачивает
artifact и передаёт APK фокус-группе по отдельной приватной ссылке.

Полный gate актуальности данных, инструкция установки и чек-лист проверки — в
[`../BETA_TESTING.md`](../BETA_TESTING.md).

## Структура

    lib/core/       тема ЮФУ, API-клиент, prefs
    lib/router.dart go_router: онбординг + 4 вкладки
    lib/features/   onboarding, schedule, exams, people, news, assistant, contacts
    lib/features/schedule/  расписание: drift-кэш со скоупом (группа|преподаватель),
                            ETag-синк, тип недели и активный модуль из календаря
                            сервера, фильтр подгруппы, выбор семестра
    lib/features/exams/     ближайшая сессия: консультация, экзамен, аудитория
    lib/features/people/    единый справочник людей: карточка, поиск и
                            расписание преподавателя (следует выбору семестра)
    lib/features/news/      лента новостей: drift-кэш, keyset-пагинация, детальный экран, офлайн-плашка
    lib/features/contacts/  справочник (деканат + кафедры): drift-кэш, поиск, mailto

Тип недели НЕ вычисляется формулой чётности. Прежняя формула («нечётная
ISO-неделя — числитель») давала результат, обратный реальному календарю ЮФУ,
и удалена: тип недели и активный модуль берутся из данных сервера. Термины —
«верхняя»/«нижняя», как в документах университета; слов «числитель» и
«знаменатель» в корпусе ЮФУ нет ни разу.

## Кодогенерация (drift)

После изменения таблиц в lib/core/db.dart:

    dart run build_runner build --delete-conflicting-outputs
