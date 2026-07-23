import 'dart:io';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sfedu_econ/core/app_version.dart';
import 'package:sfedu_econ/core/prefs.dart';
import 'package:sfedu_econ/features/contacts/contacts_providers.dart';
import 'package:sfedu_econ/features/contacts/contacts_repository.dart';
import 'package:sfedu_econ/features/news/news_providers.dart';
import 'package:sfedu_econ/features/news/news_repository.dart';
import 'package:sfedu_econ/features/onboarding/group_repository.dart';
import 'package:sfedu_econ/features/schedule/schedule_data.dart';
import 'package:sfedu_econ/features/schedule/schedule_providers.dart';
import 'package:sfedu_econ/main.dart';

/// Как в settings_screen_test: фоновые фиды подменяем на мгновенные пустые,
/// чтобы полный запуск приложения не тянул сеть/БД и не оставлял таймеров.
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

void main() {
  test('appBuild синхронизирован с pubspec.yaml', () {
    // Версионный гейт сравнивает appBuild с серверным min_build; если забыть
    // поднять константу при релизе, гейт будет резать не те версии.
    final pubspec = File('pubspec.yaml').readAsStringSync();
    final match =
        RegExp(r'^version:\s*\S+\+(\d+)', multiLine: true).firstMatch(pubspec)!;
    expect(appBuild, int.parse(match.group(1)!),
        reason: 'поднимите appBuild в core/app_version.dart вместе с pubspec');
  });

  Future<ProviderContainer> container({required int? minBuild}) async {
    SharedPreferences.setMockInitialValues({'selected_group_id': 3});
    final prefs = await SharedPreferences.getInstance();
    return ProviderContainer(overrides: [
      sharedPreferencesProvider.overrideWithValue(prefs),
      minBuildProvider.overrideWith((ref) async => minBuild),
      groupsProvider.overrideWith((ref) async => const <Group>[]),
      scheduleDataProvider
          .overrideWith((ref) => Stream.value(const ScheduleData.empty())),
      syncStatusProvider.overrideWith(_FakeSync.new),
      newsFeedProvider.overrideWith(_FakeNewsFeed.new),
      contactsFeedProvider.overrideWith(_FakeContactsFeed.new),
    ]);
  }

  testWidgets('сервер требует новее — блокирующий экран', (tester) async {
    final c = await container(minBuild: appBuild + 1);
    addTearDown(c.dispose);
    await tester.pumpWidget(
      UncontrolledProviderScope(container: c, child: const SfeduEconApp()),
    );
    await tester.pumpAndSettle();

    expect(find.text('Нужно обновление'), findsOneWidget);
    expect(find.textContaining('устарела'), findsOneWidget);
  });

  testWidgets('минимум не превышен — приложение работает', (tester) async {
    final c = await container(minBuild: appBuild);
    addTearDown(c.dispose);
    await tester.pumpWidget(
      UncontrolledProviderScope(container: c, child: const SfeduEconApp()),
    );
    await tester.pumpAndSettle();

    expect(find.text('Нужно обновление'), findsNothing);
  });

  testWidgets('offline (min_build неизвестен) — НЕ блокируем', (tester) async {
    final c = await container(minBuild: null);
    addTearDown(c.dispose);
    await tester.pumpWidget(
      UncontrolledProviderScope(container: c, child: const SfeduEconApp()),
    );
    await tester.pumpAndSettle();

    expect(find.text('Нужно обновление'), findsNothing);
  });
}
