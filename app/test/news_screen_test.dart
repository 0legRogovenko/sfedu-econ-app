import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sfedu_econ/core/prefs.dart';
import 'package:sfedu_econ/features/news/news_date.dart';
import 'package:sfedu_econ/features/news/news_item.dart';
import 'package:sfedu_econ/features/news/news_providers.dart';
import 'package:sfedu_econ/features/news/news_repository.dart';
import 'package:sfedu_econ/features/onboarding/selected_group.dart';
import 'package:sfedu_econ/features/schedule/schedule_data.dart';
import 'package:sfedu_econ/features/schedule/schedule_providers.dart';
import 'package:sfedu_econ/main.dart';

/// Экран расписания (стартовая вкладка) в фоне ходит в реальную drift-БД —
/// здесь это не по теме, подменяем на пустой поток и no-op sync.
class _FakeSync extends SyncStatusNotifier {
  @override
  Future<void> sync() async {}
}

NewsItem _item({
  int id = 1,
  String title = 'Заголовок',
  String source = 'econ',
  bool important = false,
}) => NewsItem(
  id: id,
  title: title,
  body: 'Полный текст новости $id',
  source: source,
  url: 'https://sfedu.ru/news/$id',
  imageUrl: null,
  isImportant: important,
  publishedAt: DateTime(2026, 7, 10, 12),
);

/// Фейковый нотифаер: сразу отдаёт готовую ленту, refresh/loadMore — no-op.
class _FakeFeed extends NewsFeedNotifier {
  _FakeFeed(this._feed);
  final NewsFeed _feed;

  @override
  Future<NewsFeed> build() async => _feed;

  @override
  Future<void> refresh() async {}

  @override
  Future<void> loadMore() async {}
}

/// main.dart читает themeModeProvider, которому нужен sharedPreferencesProvider
/// — подменяем на мок, чтобы не падать с UnimplementedError.
Future<Widget> _app(List<NewsItem> items, {bool offline = false}) async {
  SharedPreferences.setMockInitialValues({});
  final prefs = await SharedPreferences.getInstance();
  return ProviderScope(
    overrides: [
      sharedPreferencesProvider.overrideWithValue(prefs),
      selectedGroupIdProvider.overrideWith(() => FakeSelectedGroupId(3)),
      scheduleDataProvider.overrideWith(
        (ref) => Stream.value(const ScheduleData.empty()),
      ),
      syncStatusProvider.overrideWith(_FakeSync.new),
      newsFeedProvider.overrideWith(
        () =>
            _FakeFeed(NewsFeed(items: items, offline: offline, hasMore: false)),
      ),
    ],
    child: const SfeduEconApp(),
  );
}

void main() {
  test('источник econ подписан полным названием факультета', () {
    expect(_item(source: 'econ').sourceLabel, 'Экономический факультет');
  });

  testWidgets('лента рендерит заголовки и чипы источников', (tester) async {
    await tester.pumpWidget(
      await _app([
        _item(id: 1, title: 'Эконфак новость', source: 'econ'),
        _item(id: 2, title: 'Универ новость', source: 'sfedu'),
      ]),
    );
    await tester.pumpAndSettle();

    // переходим на вкладку новостей
    await tester.tap(find.text('Новости'));
    await tester.pumpAndSettle();

    expect(find.text('Эконфак новость'), findsOneWidget);
    expect(find.text('Универ новость'), findsOneWidget);
    expect(find.text('Экономический факультет'), findsOneWidget);
    expect(find.text('ЮФУ'), findsOneWidget);
  });

  testWidgets('«Важное» показывается только у важных новостей', (tester) async {
    await tester.pumpWidget(
      await _app([
        _item(id: 1, important: true),
        _item(id: 2, important: false),
      ]),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.text('Новости'));
    await tester.pumpAndSettle();

    expect(find.text('Важное'), findsOneWidget);
  });

  testWidgets('тап по карточке открывает полный текст', (tester) async {
    await tester.pumpWidget(await _app([_item(id: 7, title: 'Про стипендию')]));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Новости'));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Про стипендию'));
    await tester.pumpAndSettle();

    expect(find.text('Полный текст новости 7'), findsOneWidget);
    expect(find.text('Открыть на сайте'), findsOneWidget);
  });

  testWidgets('офлайн без кэша — «нужна сеть», а не «новостей нет»', (
    tester,
  ) async {
    await tester.pumpWidget(await _app([], offline: true));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Новости'));
    await tester.pumpAndSettle();

    expect(
      find.text('Нет данных. Для первой загрузки нужна сеть'),
      findsOneWidget,
    );
    expect(find.textContaining('Показаны сохранённые'), findsNothing);
  });

  testWidgets('офлайн-плашка при недоступной сети', (tester) async {
    await tester.pumpWidget(await _app([_item()], offline: true));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Новости'));
    await tester.pumpAndSettle();

    expect(find.text('Нет сети. Показаны сохранённые новости'), findsOneWidget);
  });

  group('formatNewsDate', () {
    final now = DateTime(2026, 7, 15, 10);
    test('сегодня', () {
      expect(formatNewsDate(DateTime(2026, 7, 15, 8), now: now), 'сегодня');
    });
    test('вчера', () {
      expect(formatNewsDate(DateTime(2026, 7, 14, 23), now: now), 'вчера');
    });
    test('старше — dd.MM.yyyy', () {
      expect(formatNewsDate(DateTime(2026, 3, 5), now: now), '05.03.2026');
    });
  });
}
