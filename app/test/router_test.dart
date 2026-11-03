import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sfedu_econ/core/prefs.dart';
import 'package:sfedu_econ/features/contacts/contacts_providers.dart';
import 'package:sfedu_econ/features/contacts/contacts_repository.dart';
import 'package:sfedu_econ/features/news/news_providers.dart';
import 'package:sfedu_econ/features/people/people_providers.dart';
import 'package:sfedu_econ/features/news/news_repository.dart';
import 'package:sfedu_econ/features/onboarding/selected_group.dart';
import 'package:sfedu_econ/features/schedule/schedule_data.dart';
import 'package:sfedu_econ/features/schedule/schedule_providers.dart';
import 'package:sfedu_econ/main.dart';

/// Экраны расписания, новостей и контактов в фоне ходят в реальную
/// drift-БД/dio — здесь это не по теме теста, поэтому подменяем на пустые
/// мгновенные состояния.
class _FakeSync extends SyncStatusNotifier {
  @override
  Future<void> sync() async {}
}

class _FakeFeed extends NewsFeedNotifier {
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

/// main.dart читает themeModeProvider, которому нужен sharedPreferencesProvider
/// — подменяем на мок, чтобы не падать с UnimplementedError.
Future<Widget> _appWithGroup() async {
  SharedPreferences.setMockInitialValues({});
  final prefs = await SharedPreferences.getInstance();
  return ProviderScope(
    overrides: [
      sharedPreferencesProvider.overrideWithValue(prefs),
      // группа уже выбрана — онбординг не показывается
      selectedGroupIdProvider.overrideWith(() => FakeSelectedGroupId(3)),
      scheduleDataProvider.overrideWith(
        (ref) => Stream.value(const ScheduleData.empty()),
      ),
      syncStatusProvider.overrideWith(_FakeSync.new),
      newsFeedProvider.overrideWith(_FakeFeed.new),
      contactsFeedProvider.overrideWith(_FakeContactsFeed.new),
      peopleProvider.overrideWith((ref) async => const []),
    ],
    child: const SfeduEconApp(),
  );
}

void main() {
  testWidgets('четыре вкладки в нижней панели', (tester) async {
    await tester.pumpWidget(await _appWithGroup());
    await tester.pumpAndSettle();

    expect(find.text('Расписание'), findsWidgets);
    expect(find.text('Новости'), findsOneWidget);
    expect(find.text('Помощник'), findsOneWidget);
    expect(find.text('Контакты'), findsOneWidget);
  });

  testWidgets('переключение вкладок работает', (tester) async {
    await tester.pumpWidget(await _appWithGroup());
    await tester.pumpAndSettle();

    await tester.tap(find.text('Новости'));
    await tester.pumpAndSettle();
    expect(find.text('Новостей пока нет'), findsOneWidget);

    await tester.tap(find.text('Контакты'));
    await tester.pumpAndSettle();
    expect(find.text('Справочник пуст'), findsOneWidget);
  });
}
