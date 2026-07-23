import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sfedu_econ/core/prefs.dart';
import 'package:sfedu_econ/core/theme_mode.dart';
import 'package:sfedu_econ/features/assistant/assistant_api.dart';
import 'package:sfedu_econ/features/assistant/assistant_providers.dart';
import 'package:sfedu_econ/features/contacts/contacts_providers.dart';
import 'package:sfedu_econ/features/contacts/contacts_repository.dart';
import 'package:sfedu_econ/features/news/news_providers.dart';
import 'package:sfedu_econ/features/news/news_repository.dart';
import 'package:sfedu_econ/features/onboarding/favorite_groups.dart';
import 'package:sfedu_econ/features/onboarding/group_repository.dart';
import 'package:sfedu_econ/features/onboarding/selected_group.dart';
import 'package:sfedu_econ/features/schedule/lesson.dart';
import 'package:sfedu_econ/features/schedule/schedule_data.dart';
import 'package:sfedu_econ/features/schedule/schedule_providers.dart';
import 'package:sfedu_econ/features/schedule/subgroup_filter.dart';
import 'package:sfedu_econ/main.dart';
import 'package:sfedu_econ/router.dart';

const _groups = [
  Group(
    id: 1,
    course: 1,
    number: '1.1',
    program: null,
    level: EducationLevel.bachelor,
    subgroupCount: 2,
  ),
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
  // Разбиение на три подгруппы — для проверки, что чипы не зашиты как 1/2.
  Group(
    id: 5,
    course: 3,
    number: '3.1',
    program: null,
    level: EducationLevel.bachelor,
    subgroupCount: 3,
  ),
];

/// Расписание, новости и контакты в фоне ходят в реальную drift-БД/dio —
/// здесь это не по теме теста, поэтому подменяем на пустые мгновенные
/// состояния. selectedGroupIdProvider и themeModeProvider НЕ подменяем —
/// именно их поведение (запись в SharedPreferences) здесь проверяется.
class _FakeSync extends SyncStatusNotifier {
  @override
  Future<void> sync() async {}
}

class _FakeNewsFeed extends NewsFeedNotifier {
  @override
  Future<NewsFeed> build() async =>
      const NewsFeed(items: [], offline: false, hasMore: false);
  @override
  Future<void> refresh() async {}
}

class _FakeContactsFeed extends ContactsFeedNotifier {
  @override
  Future<ContactsFeed> build() async =>
      const ContactsFeed(items: [], offline: false);
  @override
  Future<void> refresh() async {}
}

/// Пара нужной подгруппы: число чипов фильтра считается по самим парам,
/// потому что Group.subgroupCount импорт не заполняет.
Lesson _lesson(int subgroup) => Lesson(
      id: subgroup,
      groupId: 3,
      weekday: 0,
      pairNumber: 1,
      startsAt: '09:00:00',
      endsAt: '10:35:00',
      subject: 'Английский',
      room: '118',
      weekType: null,
      subgroup: subgroup,
      teacherName: null,
    );

class _RecordingApi implements AssistantApi {
  final List<String> forgotDevices = [];

  @override
  Future<AskResult> ask(String question, String deviceId) async =>
      const AskAnswer(text: 'x', fallback: false);

  @override
  Future<bool> forget(String deviceId) async {
    forgotDevices.add(deviceId);
    return true;
  }
}

Future<ProviderContainer> _container({
  Map<String, Object> prefsValues = const {'selected_group_id': 3},
  List<Lesson> lessons = const [],
  AssistantApi? assistantApi,
}) async {
  SharedPreferences.setMockInitialValues(prefsValues);
  final prefs = await SharedPreferences.getInstance();
  return ProviderContainer(
    overrides: [
      sharedPreferencesProvider.overrideWithValue(prefs),
      groupsProvider.overrideWith((ref) async => _groups),
      scheduleDataProvider.overrideWith((ref) => Stream.value(ScheduleData(
            lessons: lessons,
            modules: const [],
            weekCalendar: const [],
          ))),
      syncStatusProvider.overrideWith(_FakeSync.new),
      newsFeedProvider.overrideWith(_FakeNewsFeed.new),
      contactsFeedProvider.overrideWith(_FakeContactsFeed.new),
      if (assistantApi != null)
        assistantApiProvider.overrideWithValue(assistantApi),
    ],
  );
}

/// Прокрутка к элементу настроек. Экран растёт, и элемент оказывается в одном
/// из двух состояний: построен, но за краем вьюпорта (помогает только
/// ensureVisible — прокручивать нечего, виджет уже найден) либо ещё не построен
/// ленивым ListView (нужен scrollUntilVisible). Хелпер закрывает оба случая,
/// чтобы новая секция не роняла чужие тесты.
Future<void> _scrollTo(WidgetTester tester, Finder finder) async {
  if (finder.evaluate().isEmpty) {
    await tester.scrollUntilVisible(finder, 200,
        scrollable: find.byType(Scrollable).first);
  }
  await tester.ensureVisible(finder);
  await tester.pumpAndSettle();
}

Future<void> _pumpSettings(WidgetTester tester, ProviderContainer container) async {
  await tester.pumpWidget(
    UncontrolledProviderScope(container: container, child: const SfeduEconApp()),
  );
  await tester.pumpAndSettle();
  container.read(routerProvider).go('/settings');
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('экран показывает текущую группу', (tester) async {
    final container = await _container();
    addTearDown(container.dispose);
    await _pumpSettings(tester, container);

    expect(find.text('Текущая группа: 2.1'), findsOneWidget);
  });

  testWidgets('смена группы обновляет провайдер и сохраняется в prefs',
      (tester) async {
    final container = await _container();
    addTearDown(container.dispose);
    await _pumpSettings(tester, container);

    // Пикер открыт на текущей группе 2.1 (курс 2). Чтобы выбрать 1.1,
    // раскрываем первый курс, затем жмём группу.
    await tester.tap(find.text('1 курс'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('1.1'));
    await tester.pumpAndSettle();

    expect(container.read(selectedGroupIdProvider), 1);
    expect(container.read(sharedPreferencesProvider).getInt('selected_group_id'), 1);
  });

  testWidgets('переключение темы обновляет провайдер и сохраняется в prefs',
      (tester) async {
    final container = await _container();
    addTearDown(container.dispose);
    await _pumpSettings(tester, container);

    final dark = find.text('Тёмная');
    await _scrollTo(tester, dark);
    await tester.tap(dark);
    await tester.pumpAndSettle();

    expect(container.read(themeModeProvider), ThemeMode.dark);
    expect(container.read(sharedPreferencesProvider).getString('theme_mode'), 'dark');
  });

  testWidgets('есть кнопка «Сообщить об ошибке»', (tester) async {
    final container = await _container();
    addTearDown(container.dispose);
    await _pumpSettings(tester, container);

    final button = find.text('Сообщить об ошибке');
    await _scrollTo(tester, button);
    expect(button, findsOneWidget);
  });

  testWidgets('«Удалить мои данные» после подтверждения зовёт forget',
      (tester) async {
    final api = _RecordingApi();
    final container = await _container(assistantApi: api);
    addTearDown(container.dispose);
    await _pumpSettings(tester, container);

    final button = find.text('Удалить мои данные');
    await _scrollTo(tester, button);
    await tester.tap(button);
    await tester.pumpAndSettle();

    // Диалог подтверждения — без него ничего не удаляем.
    expect(api.forgotDevices, isEmpty);
    await tester.tap(find.widgetWithText(TextButton, 'Удалить'));
    await tester.pumpAndSettle();

    expect(api.forgotDevices, hasLength(1));
    expect(find.text('Данные удалены'), findsOneWidget);
  });

  group('избранные группы', () {
    testWidgets('секция показывает избранные с именами групп', (tester) async {
      final container = await _container(prefsValues: {
        'selected_group_id': 3,
        'favorite_group_ids': ['3', '4'],
      });
      addTearDown(container.dispose);
      await _pumpSettings(tester, container);

      expect(find.text('Избранные группы'), findsOneWidget);
      expect(find.widgetWithText(ListTile, '2.1'), findsOneWidget);
      expect(find.widgetWithText(ListTile, '2.2'), findsOneWidget);
    });

    testWidgets('кнопка добавляет текущую группу в избранные', (tester) async {
      // Текущая группа 3 избранная (миграция), меняем на 1 через пикер —
      // появляется кнопка добавления.
      final container = await _container();
      addTearDown(container.dispose);
      await _pumpSettings(tester, container);

      await tester.tap(find.text('1 курс'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('1.1'));
      await tester.pumpAndSettle();

      final addButton = find.text('Добавить текущую в избранные');
      await _scrollTo(tester, addButton);
      await tester.tap(addButton);
      await tester.pumpAndSettle();

      expect(container.read(favoriteGroupIdsProvider), [3, 1]);
      // кнопка исчезает: текущая уже в избранных
      expect(find.text('Добавить текущую в избранные'), findsNothing);
    });

    testWidgets('тап по избранной делает её активной', (tester) async {
      final container = await _container(prefsValues: {
        'selected_group_id': 3,
        'favorite_group_ids': ['3', '4'],
      });
      addTearDown(container.dispose);
      await _pumpSettings(tester, container);

      await tester.tap(find.widgetWithText(ListTile, '2.2'));
      await tester.pumpAndSettle();

      expect(container.read(selectedGroupIdProvider), 4);
    });

    testWidgets('удаление активной переключает активную на первую оставшуюся',
        (tester) async {
      // Семантика зафиксирована в favorite_groups_test: активную удалить
      // МОЖНО, активной становится первая из оставшихся.
      final container = await _container(prefsValues: {
        'selected_group_id': 3,
        'favorite_group_ids': ['3', '4'],
      });
      addTearDown(container.dispose);
      await _pumpSettings(tester, container);

      await tester.tap(find.descendant(
        of: find.widgetWithText(ListTile, '2.1'),
        matching: find.byIcon(Icons.delete_outline),
      ));
      await tester.pumpAndSettle();

      expect(container.read(favoriteGroupIdsProvider), [4]);
      expect(container.read(selectedGroupIdProvider), 4);
    });
  });

  group('моя подгруппа', () {
    testWidgets('без пар по подгруппам фильтра нет, а не пустые чипы',
        (tester) async {
      // В живом корпусе у большинства групп подгрупп нет вовсе. Показывать
      // им фильтр, который ничего не изменит, — обещать несуществующую
      // настройку.
      final container = await _container();
      addTearDown(container.dispose);
      await _pumpSettings(tester, container);
      await _scrollTo(tester, find.text('Моя подгруппа'));

      expect(find.textContaining('нет занятий по подгруппам'), findsOneWidget);
      expect(find.widgetWithText(ChoiceChip, 'Все'), findsNothing);
    });

    testWidgets('чипов столько, сколько подгрупп в парах группы',
        (tester) async {
      // Регрессия: считать по Group.subgroupCount нельзя — импорт его не
      // заполняет (в живой базе он равен 1 у всех групп, включая те, где
      // реально есть пары второй подгруппы).
      final container = await _container(lessons: [_lesson(1), _lesson(2)]);
      addTearDown(container.dispose);
      await _pumpSettings(tester, container);
      await _scrollTo(tester, find.text('Моя подгруппа'));

      expect(find.widgetWithText(ChoiceChip, '1-я'), findsOneWidget);
      expect(find.widgetWithText(ChoiceChip, '2-я'), findsOneWidget);
      expect(find.widgetWithText(ChoiceChip, '3-я'), findsNothing);
    });

    testWidgets('разбиение на три подгруппы даёт три чипа', (tester) async {
      final container =
          await _container(lessons: [_lesson(1), _lesson(2), _lesson(3)]);
      addTearDown(container.dispose);
      await _pumpSettings(tester, container);
      await _scrollTo(tester, find.text('Моя подгруппа'));

      expect(find.widgetWithText(ChoiceChip, '3-я'), findsOneWidget);
      expect(find.widgetWithText(ChoiceChip, '4-я'), findsNothing);
    });

    testWidgets('по умолчанию выбрано «Все»', (tester) async {
      final container = await _container(lessons: [_lesson(1), _lesson(2)]);
      addTearDown(container.dispose);
      await _pumpSettings(tester, container);
      await _scrollTo(tester, find.text('Моя подгруппа'));

      // Проверяем именно ВЫБРАННОСТЬ чипа: сам по себе он есть всегда, и
      // ассерт на его наличие прошёл бы даже при selected: false.
      expect(
        tester.widget<ChoiceChip>(find.widgetWithText(ChoiceChip, 'Все')).selected,
        isTrue,
      );
      expect(
        tester.widget<ChoiceChip>(find.widgetWithText(ChoiceChip, '1-я')).selected,
        isFalse,
      );
      expect(container.read(activeSubgroupProvider), isNull);
    });

    testWidgets('выбор подгруппы сохраняется для активной группы',
        (tester) async {
      final container = await _container(lessons: [_lesson(1), _lesson(2)]);
      addTearDown(container.dispose);
      await _pumpSettings(tester, container);

      final second = find.text('2-я');
      await _scrollTo(tester, second);
      await tester.tap(second);
      await tester.pumpAndSettle();

      // Активная группа — 3 (см. prefs по умолчанию).
      expect(container.read(activeSubgroupProvider), 2);
      expect(container.read(sharedPreferencesProvider).getInt('subgroup_of_3'),
          2);
    });

    testWidgets('«Все» снимает ранее выбранный фильтр', (tester) async {
      final container = await _container(
        prefsValues: {'selected_group_id': 3, 'subgroup_of_3': 1},
        lessons: [_lesson(1), _lesson(2)],
      );
      addTearDown(container.dispose);
      await _pumpSettings(tester, container);

      final all = find.text('Все');
      await _scrollTo(tester, all);
      await tester.tap(all);
      await tester.pumpAndSettle();

      expect(container.read(activeSubgroupProvider), isNull);
      expect(
          container.read(sharedPreferencesProvider).containsKey('subgroup_of_3'),
          isFalse);
    });
  });

  testWidgets('«О приложении» указывает неофициальный статус', (tester) async {
    final container = await _container();
    addTearDown(container.dispose);
    await _pumpSettings(tester, container);

    final about = find.text(
      'Неофициальное приложение, сделано студентом. '
      'Данные берутся с sfedu.ru.',
    );
    await _scrollTo(tester, about);

    expect(about, findsOneWidget);
  });
}
