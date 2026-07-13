# Эконом ЮФУ — мобильное приложение

Flutter-клиент. Бэкенд: `../backend` (должен работать на localhost:8000).

## Запуск

    flutter pub get
    flutter run    # симулятор/эмулятор; для устройства см. ниже

Для реального устройства бэкенд доступен по IP машины:

    flutter run --dart-define=API_BASE_URL=http://<IP-машины>:8000

Android-эмулятор не видит localhost хоста — использовать:

    flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000

## Тесты и анализ

    flutter test
    flutter analyze

## Структура

    lib/core/       тема ЮФУ, API-клиент, prefs
    lib/router.dart go_router: онбординг + 4 вкладки
    lib/features/   onboarding, schedule, news, assistant, contacts
    lib/features/schedule/  экран расписания: drift-кэш, ETag-синк, недели числитель/знаменатель (нечётная ISO-неделя — числитель, допущение MVP)

## Кодогенерация (drift)

После изменения таблиц в lib/core/db.dart:

    dart run build_runner build --delete-conflicting-outputs
