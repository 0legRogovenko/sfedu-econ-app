import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sfedu_econ/core/clock.dart';
import 'package:sfedu_econ/core/prefs.dart';
import 'package:sfedu_econ/features/onboarding/group_repository.dart';
import 'package:sfedu_econ/features/onboarding/selected_group.dart';
import 'package:sfedu_econ/features/schedule/lesson.dart';
import 'package:sfedu_econ/features/schedule/schedule_data.dart';
import 'package:sfedu_econ/features/schedule/schedule_providers.dart';
import 'package:sfedu_econ/features/schedule/schedule_repository.dart';
import 'package:sfedu_econ/features/schedule/schedule_screen.dart';

// 13.07.2026 — понедельник, 09:30 — идёт 1-я пара. Неделя 13–19.07 — верхняя.
final _now = DateTime(2026, 7, 13, 9, 30);

const _lessons = [
  Lesson(
    id: 1,
    groupId: 3,
    weekday: 0,
    pairNumber: 1,
    startsAt: '09:00:00',
    endsAt: '10:35:00',
    subject: 'Макроэкономика',
    room: '220',
    weekType: null, // каждую неделю
    subgroup: 0,
    teacherName: 'Иванова Е. П.',
  ),
  Lesson(
    id: 2,
    groupId: 3,
    weekday: 0,
    pairNumber: 2,
    startsAt: '10:50:00',
    endsAt: '12:25:00',
    subject: 'Эконометрика',
    room: '305',
    weekType: WeekType.upper,
    subgroup: 0,
    teacherName: 'Петров А. С.',
  ),
  Lesson(
    id: 3,
    groupId: 3,
    weekday: 1, // вторник
    pairNumber: 1,
    startsAt: '09:00:00',
    endsAt: '10:35:00',
    subject: 'Иностранный язык',
    room: '118',
    weekType: null,
    subgroup: 1,
    teacherName: null,
  ),
];

// Календарь: 13–19.07 верхняя, 20–26.07 нижняя.
final _calendar = [
  WeekCalendarEntry(
    dateFrom: DateTime(2026, 7, 13),
    dateTo: DateTime(2026, 7, 19),
    weekType: WeekType.upper,
  ),
  WeekCalendarEntry(
    dateFrom: DateTime(2026, 7, 20),
    dateTo: DateTime(2026, 7, 26),
    weekType: WeekType.lower,
  ),
];

final _data =
    ScheduleData(lessons: _lessons, modules: const [], weekCalendar: _calendar);

/// Фоновый sync в initState не должен трогать реальную drift-БД в тестах.
class _FakeSync extends SyncStatusNotifier {
  @override
  Future<void> sync() async {}
}

/// Записывает, сколько раз дёрнули sync — для регрессии на смену группы.
class _RecordingSync extends SyncStatusNotifier {
  static int calls = 0;

  @override
  Future<void> sync() async {
    calls++;
  }
}

/// Синк уже завершился неудачей — для теста офлайн-плашки.
class _FailedSync extends SyncStatusNotifier {
  @override
  SyncStatus build() => SyncStatus(
        lastResult: SyncResult.failed,
        syncedAt: DateTime(2026, 7, 12),
      );

  @override
  Future<void> sync() async {}
}

/// Первый запуск: сеть упала ДО первого успешного синка, кэша ещё нет
/// (syncedAt == null). Для теста честной плашки «нет данных».
class _FirstLaunchFailedSync extends SyncStatusNotifier {
  @override
  SyncStatus build() =>
      const SyncStatus(lastResult: SyncResult.failed, syncedAt: null);

  @override
  Future<void> sync() async {}
}

const _groups = [
  Group(
    id: 3,
    course: 2,
    number: '2.1',
    program: null,
    level: EducationLevel.bachelor,
    subgroupCount: 2,
  ),
  Group(
    id: 4,
    course: 2,
    number: '2.2',
    program: null,
    level: EducationLevel.bachelor,
    subgroupCount: 2,
  ),
];

/// Контейнер со всеми оверрайдами экрана: prefs нужны избранным и фильтру
/// подгруппы, groupsProvider — имени группы в заголовке.
///
/// Возвращаем контейнер, а не список оверрайдов: тип элемента (riverpod
/// `Override`) не реэкспортируется через flutter_riverpod, а линтер
/// `strict_top_level_inference` требует явную аннотацию.
Future<ProviderContainer> _container({
  DateTime? now,
  SyncStatusNotifier Function()? sync,
  ScheduleData? data,
  Map<String, Object> prefsValues = const {},
}) async {
  SharedPreferences.setMockInitialValues(prefsValues);
  final prefs = await SharedPreferences.getInstance();
  return ProviderContainer(
    overrides: [
      sharedPreferencesProvider.overrideWithValue(prefs),
      groupsProvider.overrideWith((ref) async => _groups),
      selectedGroupIdProvider.overrideWith(() => FakeSelectedGroupId(3)),
      scheduleDataProvider.overrideWith((ref) => Stream.value(data ?? _data)),
      clockProvider.overrideWithValue(() => now ?? _now),
      syncStatusProvider.overrideWith(sync ?? _FakeSync.new),
    ],
  );
}

Future<Widget> _screen({
  DateTime? now,
  SyncStatusNotifier Function()? sync,
  ScheduleData? data,
  Map<String, Object> prefsValues = const {},
}) async =>
    UncontrolledProviderScope(
      container: await _container(
          now: now, sync: sync, data: data, prefsValues: prefsValues),
      child: const MaterialApp(home: ScheduleScreen()),
    );

void main() {
  testWidgets('смена группы запускает синхронизацию', (tester) async {
    // Регрессия: экран синкался только в initState, поэтому после перехода
    // на push/pop-навигацию смена группы в настройках не подтягивала бы
    // расписание новой группы (итог ревью).
    _RecordingSync.calls = 0;
    final container = await _container(sync: _RecordingSync.new);
    addTearDown(container.dispose);

    await tester.pumpWidget(UncontrolledProviderScope(
      container: container,
      child: const MaterialApp(home: ScheduleScreen()),
    ));
    await tester.pumpAndSettle();

    final afterInit = _RecordingSync.calls; // стартовый синк из initState

    await container.read(selectedGroupIdProvider.notifier).select(1);
    await tester.pumpAndSettle();

    expect(_RecordingSync.calls, greaterThan(afterInit));
  });

  testWidgets('показывает пары сегодняшнего дня', (tester) async {
    await tester.pumpWidget(await _screen());
    await tester.pumpAndSettle();

    expect(find.text('Макроэкономика'), findsOneWidget);
    expect(find.text('Эконометрика'), findsOneWidget);
    expect(find.text('Иностранный язык'), findsNothing); // вторник
  });

  testWidgets('аудитория-номер: в карточке ровно одно «ауд.»', (tester) async {
    // Регрессия «ауд. ауд.118»: бэкенд теперь отдаёт голое «220», а префикс
    // дописывает карточка — и только один раз.
    await tester.pumpWidget(await _screen());
    await tester.pumpAndSettle();

    expect(find.text('ауд. 220 · Иванова Е. П.'), findsOneWidget);
    expect(find.textContaining('ауд. ауд.'), findsNothing);
  });

  testWidgets('«Онлайн» показывается без префикса «ауд.»', (tester) async {
    final data = ScheduleData(
      lessons: const [
        Lesson(
          id: 4,
          groupId: 3,
          weekday: 0,
          pairNumber: 3,
          startsAt: '13:00:00',
          endsAt: '14:35:00',
          subject: 'Физкультура',
          room: 'Онлайн',
          weekType: null,
          subgroup: 0,
          teacherName: 'Бондин В.И.',
        ),
      ],
      modules: const [],
      weekCalendar: _calendar,
    );
    await tester.pumpWidget(await _screen(data: data));
    await tester.pumpAndSettle();

    expect(find.text('Онлайн · Бондин В.И.'), findsOneWidget);
    expect(find.textContaining('ауд. Онлайн'), findsNothing);
  });

  testWidgets('текущая пара помечена «Сейчас»', (tester) async {
    await tester.pumpWidget(await _screen());
    await tester.pumpAndSettle();

    expect(find.text('Сейчас'), findsOneWidget);
  });

  testWidgets('свайп влево — следующий день', (tester) async {
    await tester.pumpWidget(await _screen());
    await tester.pumpAndSettle();

    await tester.fling(find.byType(PageView), const Offset(-400, 0), 1000);
    await tester.pumpAndSettle();

    expect(find.text('Иностранный язык'), findsOneWidget);
    expect(find.text('Макроэкономика'), findsNothing);
  });

  testWidgets('тап по дню в ленте переключает страницу', (tester) async {
    await tester.pumpWidget(await _screen());
    await tester.pumpAndSettle();

    await tester.tap(find.text('Вт'));
    await tester.pumpAndSettle();

    expect(find.text('Иностранный язык'), findsOneWidget);
  });

  testWidgets('пустой день — дружелюбная заглушка', (tester) async {
    await tester.pumpWidget(await _screen());
    await tester.pumpAndSettle();

    await tester.tap(find.text('Сб'));
    await tester.pumpAndSettle();

    expect(find.text('Пар нет — отдыхаем'), findsOneWidget);
  });

  testWidgets('бейдж «верхняя» на верхней неделе', (tester) async {
    await tester.pumpWidget(await _screen());
    await tester.pumpAndSettle();

    expect(find.text('верхняя'), findsOneWidget);
  });

  testWidgets('в воскресенье показывается понедельник следующей недели',
      (tester) async {
    // 19.07.2026 — воскресенье; след. понедельник 20.07 — нижняя неделя.
    await tester.pumpWidget(await _screen(now: DateTime(2026, 7, 19, 12, 0)));
    await tester.pumpAndSettle();

    expect(find.text('Макроэкономика'), findsOneWidget); // каждую неделю
    expect(find.text('Эконометрика'), findsNothing); // верхняя — исключена
    expect(find.text('нижняя'), findsOneWidget);
  });

  testWidgets('после неудачного синка показывается плашка с датой данных',
      (tester) async {
    await tester.pumpWidget(await _screen(sync: _FailedSync.new));
    await tester.pumpAndSettle();

    expect(find.textContaining('Данные от 12.07.2026'), findsOneWidget);
  });

  testWidgets('бейдж активного модуля виден для даты внутри модуля',
      (tester) async {
    // Выбранный день — 13.07.2026, модуль накрывает весь июль.
    final data = ScheduleData(
      lessons: _lessons,
      modules: [
        Module(
          id: 2,
          name: '2 модуль',
          dateFrom: DateTime(2026, 7, 1),
          dateTo: DateTime(2026, 7, 31),
        ),
      ],
      weekCalendar: _calendar,
    );
    await tester.pumpWidget(await _screen(data: data));
    await tester.pumpAndSettle();

    expect(find.text('2 модуль'), findsOneWidget);
  });

  testWidgets('бейдж активного модуля скрыт для даты вне диапазонов',
      (tester) async {
    // Выбранный день — 13.07.2026, модуль относится к сентябрю.
    final data = ScheduleData(
      lessons: _lessons,
      modules: [
        Module(
          id: 1,
          name: '1 модуль',
          dateFrom: DateTime(2026, 9, 1),
          dateTo: DateTime(2026, 9, 30),
        ),
      ],
      weekCalendar: _calendar,
    );
    await tester.pumpWidget(await _screen(data: data));
    await tester.pumpAndSettle();

    expect(find.text('1 модуль'), findsNothing);
  });

  testWidgets('первый офлайн-запуск: честная плашка вместо «Пар нет»',
      (tester) async {
    // Свежая установка: кэш пуст, первый синк упал (syncedAt == null).
    // Студент не должен видеть «Пар нет — отдыхаем» — данные просто не загружены.
    await tester.pumpWidget(await _screen(
      sync: _FirstLaunchFailedSync.new,
      data: const ScheduleData.empty(),
    ));
    await tester.pumpAndSettle();

    expect(find.text('Пар нет — отдыхаем'), findsNothing);
    expect(find.textContaining('Нет данных'), findsOneWidget);
  });

  testWidgets('заголовок показывает имя активной группы', (tester) async {
    await tester.pumpWidget(await _screen());
    await tester.pumpAndSettle();

    expect(find.text('2.1'), findsOneWidget);
  });

  testWidgets('тап по заголовку — меню избранных, выбор переключает активную',
      (tester) async {
    final container = await _container(prefsValues: {
      'favorite_group_ids': ['3', '4'],
    });
    addTearDown(container.dispose);

    await tester.pumpWidget(UncontrolledProviderScope(
      container: container,
      child: const MaterialApp(home: ScheduleScreen()),
    ));
    await tester.pumpAndSettle();

    await tester.tap(find.text('2.1'));
    await tester.pumpAndSettle();
    expect(find.text('2.2'), findsOneWidget); // меню избранных открылось

    await tester.tap(find.text('2.2'));
    await tester.pumpAndSettle();

    // Смена активной идёт через selectedGroupIdProvider.select() —
    // существующий ref.listen-синк подхватит сам.
    expect(container.read(selectedGroupIdProvider), 4);
  });
}
