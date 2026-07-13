import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sfedu_econ/core/prefs.dart';
import 'package:sfedu_econ/features/onboarding/group_repository.dart';
import 'package:sfedu_econ/features/onboarding/selected_group.dart';
import 'package:sfedu_econ/features/schedule/lesson.dart';
import 'package:sfedu_econ/features/schedule/schedule_providers.dart';
import 'package:sfedu_econ/main.dart';
import 'package:sfedu_econ/router.dart';

const _groups = [
  Group(id: 1, course: 1, number: '01.1', subgroupCount: 2),
  Group(id: 3, course: 2, number: '02.1', subgroupCount: 2),
  Group(id: 4, course: 2, number: '02.2', subgroupCount: 2),
];

/// Экран расписания в фоне ходит в реальную drift-БД/dio — здесь это
/// не по теме теста, поэтому подменяем на пустой мгновенный поток.
class _FakeSync extends SyncStatusNotifier {
  @override
  Future<void> sync() async {}
}

Future<Widget> _app() async {
  SharedPreferences.setMockInitialValues({});
  final prefs = await SharedPreferences.getInstance();
  return ProviderScope(
    overrides: [
      sharedPreferencesProvider.overrideWithValue(prefs),
      groupsProvider.overrideWith((ref) async => _groups),
      lessonsProvider.overrideWith((ref) => Stream.value(const <Lesson>[])),
      syncStatusProvider.overrideWith(_FakeSync.new),
    ],
    child: const SfeduEconApp(),
  );
}

void main() {
  testWidgets('онбординг: выбор курса и группы ведёт на расписание',
      (tester) async {
    await tester.pumpWidget(await _app());
    await tester.pumpAndSettle();

    // без выбранной группы показывается онбординг
    expect(find.text('Привет! 👋'), findsOneWidget);

    // выбираем курс 2 — остаются группы второго курса
    await tester.tap(find.text('2 курс'));
    await tester.pumpAndSettle();
    expect(find.text('01.1'), findsNothing);

    // выбираем группу и жмём «Начать»
    await tester.tap(find.text('02.1'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Начать'));
    await tester.pumpAndSettle();

    // попали на вкладки
    expect(find.text('Расписание'), findsWidgets);
  });

  testWidgets('кнопка «Начать» неактивна без выбранной группы',
      (tester) async {
    await tester.pumpWidget(await _app());
    await tester.pumpAndSettle();

    final button = tester.widget<FilledButton>(
      find.widgetWithText(FilledButton, 'Начать'),
    );
    expect(button.onPressed, isNull);
  });

  test('выбор группы сохраняется в SharedPreferences', () async {
    SharedPreferences.setMockInitialValues({});
    final prefs = await SharedPreferences.getInstance();
    final container = ProviderContainer(
      overrides: [sharedPreferencesProvider.overrideWithValue(prefs)],
    );
    addTearDown(container.dispose);

    await container.read(selectedGroupIdProvider.notifier).select(3);

    expect(prefs.getInt('selected_group_id'), 3);
  });

  testWidgets('переход на вкладку без выбранной группы ведёт на онбординг',
      (tester) async {
    SharedPreferences.setMockInitialValues({});
    final prefs = await SharedPreferences.getInstance();
    final container = ProviderContainer(
      overrides: [
        sharedPreferencesProvider.overrideWithValue(prefs),
        groupsProvider.overrideWith((ref) async => _groups),
      ],
    );
    addTearDown(container.dispose);
    await tester.pumpWidget(UncontrolledProviderScope(
      container: container,
      child: const SfeduEconApp(),
    ));
    await tester.pumpAndSettle();

    container.read(routerProvider).go('/news');
    await tester.pumpAndSettle();

    expect(find.text('Привет! 👋'), findsOneWidget);
  });
}
