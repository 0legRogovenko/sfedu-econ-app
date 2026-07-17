import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sfedu_econ/core/prefs.dart';
import 'package:sfedu_econ/core/theme_mode.dart';
import 'package:sfedu_econ/features/contacts/contacts_providers.dart';
import 'package:sfedu_econ/features/contacts/contacts_repository.dart';
import 'package:sfedu_econ/features/news/news_providers.dart';
import 'package:sfedu_econ/features/news/news_repository.dart';
import 'package:sfedu_econ/features/onboarding/group_repository.dart';
import 'package:sfedu_econ/features/onboarding/selected_group.dart';
import 'package:sfedu_econ/features/schedule/schedule_data.dart';
import 'package:sfedu_econ/features/schedule/schedule_providers.dart';
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

Future<ProviderContainer> _container() async {
  SharedPreferences.setMockInitialValues({'selected_group_id': 3});
  final prefs = await SharedPreferences.getInstance();
  return ProviderContainer(
    overrides: [
      sharedPreferencesProvider.overrideWithValue(prefs),
      groupsProvider.overrideWith((ref) async => _groups),
      scheduleDataProvider
          .overrideWith((ref) => Stream.value(const ScheduleData.empty())),
      syncStatusProvider.overrideWith(_FakeSync.new),
      newsFeedProvider.overrideWith(_FakeNewsFeed.new),
      contactsFeedProvider.overrideWith(_FakeContactsFeed.new),
    ],
  );
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

    await tester.tap(find.text('Тёмная'));
    await tester.pumpAndSettle();

    expect(container.read(themeModeProvider), ThemeMode.dark);
    expect(container.read(sharedPreferencesProvider).getString('theme_mode'), 'dark');
  });

  testWidgets('«О приложении» указывает неофициальный статус', (tester) async {
    final container = await _container();
    addTearDown(container.dispose);
    await _pumpSettings(tester, container);

    // Пикер стал выше — блок «О приложении» уходит за нижнюю границу ленивого
    // ListView, поэтому прокручиваем до него.
    final about = find.text(
      'Неофициальное приложение, сделано студентом. '
      'Данные берутся с sfedu.ru.',
    );
    await tester.scrollUntilVisible(about, 200,
        scrollable: find.byType(Scrollable).first);

    expect(about, findsOneWidget);
  });
}
