import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sfedu_econ/features/news/news_providers.dart';
import 'package:sfedu_econ/features/news/news_repository.dart';
import 'package:sfedu_econ/features/onboarding/selected_group.dart';
import 'package:sfedu_econ/features/schedule/lesson.dart';
import 'package:sfedu_econ/features/schedule/schedule_providers.dart';
import 'package:sfedu_econ/main.dart';

/// Экраны расписания и новостей в фоне ходят в реальную drift-БД/dio — здесь
/// это не по теме теста, поэтому подменяем на пустые мгновенные состояния.
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

Widget _appWithGroup() => ProviderScope(
      overrides: [
        // группа уже выбрана — онбординг не показывается
        selectedGroupIdProvider.overrideWith(() => FakeSelectedGroupId(3)),
        lessonsProvider.overrideWith((ref) => Stream.value(const <Lesson>[])),
        syncStatusProvider.overrideWith(_FakeSync.new),
        newsFeedProvider.overrideWith(_FakeFeed.new),
      ],
      child: const SfeduEconApp(),
    );

void main() {
  testWidgets('четыре вкладки в нижней панели', (tester) async {
    await tester.pumpWidget(_appWithGroup());
    await tester.pumpAndSettle();

    expect(find.text('Расписание'), findsWidgets);
    expect(find.text('Новости'), findsOneWidget);
    expect(find.text('Помощник'), findsOneWidget);
    expect(find.text('Контакты'), findsOneWidget);
  });

  testWidgets('переключение вкладок работает', (tester) async {
    await tester.pumpWidget(_appWithGroup());
    await tester.pumpAndSettle();

    await tester.tap(find.text('Новости'));
    await tester.pumpAndSettle();
    expect(find.text('Новостей пока нет'), findsOneWidget);

    await tester.tap(find.text('Контакты'));
    await tester.pumpAndSettle();
    expect(find.text('Здесь будет справочник'), findsOneWidget);
  });
}
