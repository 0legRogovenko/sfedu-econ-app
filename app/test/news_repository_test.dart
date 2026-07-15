import 'package:drift/drift.dart' show Value;
import 'package:drift/native.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sfedu_econ/core/db.dart';
import 'package:sfedu_econ/features/news/news_api.dart';
import 'package:sfedu_econ/features/news/news_repository.dart';

Map<String, dynamic> _json(int id, {String source = 'sfedu'}) => {
      'id': id,
      'title': 'Заголовок $id',
      'body': 'Текст $id',
      'source': source,
      'url': 'https://sfedu.ru/news/$id',
      'image_url': null,
      'is_important': false,
      // публикации по убыванию id
      'published_at': DateTime(2026, 7, 15, 12).subtract(Duration(hours: id))
          .toIso8601String(),
    };

class FakeNewsApi implements NewsApi {
  FakeNewsApi(this.pages);

  /// Список ответов; null-элемент имитирует сетевую ошибку.
  final List<List<Map<String, dynamic>>?> pages;
  final List<Map<String, dynamic>> calls = [];
  int _index = 0;

  @override
  Future<List<Map<String, dynamic>>?> fetchPage({
    DateTime? before,
    int? beforeId,
    int limit = 20,
  }) async {
    calls.add({'before': before, 'before_id': beforeId, 'limit': limit});
    return pages[_index++];
  }
}

void main() {
  late AppDatabase db;
  setUp(() => db = AppDatabase.forTesting(NativeDatabase.memory()));
  tearDown(() => db.close());

  test('refresh: страница заменяет кэш', () async {
    final api = FakeNewsApi([
      [_json(1), _json(2)],
    ]);
    final repo = NewsRepository(api, db);

    final feed = await repo.refresh();

    expect(feed.offline, isFalse);
    expect(feed.items.map((n) => n.id), [1, 2]);
    expect((await db.allNews()).length, 2);
  });

  test('refresh при ошибке сети: кэш не тронут, offline=true', () async {
    final seedApi = FakeNewsApi([
      [_json(1)],
    ]);
    final repo = NewsRepository(seedApi, db);
    await repo.refresh();

    final failing = NewsRepository(FakeNewsApi([null]), db);
    final feed = await failing.refresh();

    expect(feed.offline, isTrue);
    expect(feed.items.map((n) => n.id), [1]); // прежний кэш
    expect((await db.allNews()).length, 1);
  });

  test('loadMore: докидывает следующую страницу курсором', () async {
    final page1 = List.generate(20, (i) => _json(i + 1)); // ids 1..20, полная
    final api = FakeNewsApi([
      page1,
      [_json(21), _json(22)],
    ]);
    final repo = NewsRepository(api, db);
    final first = await repo.refresh();
    expect(first.hasMore, isTrue);

    final more = await repo.loadMore(first);

    expect(more.items.length, 22);
    expect(more.items.last.id, 22);
    // курсор второй страницы = (publishedAt, id) последнего элемента первой
    expect(api.calls.last['before_id'], 20);
    expect(api.calls.last['before'], isNotNull);
  });

  test('loadMore при короткой странице снимает hasMore', () async {
    final api = FakeNewsApi([
      List.generate(20, (i) => _json(i + 1)), // ровно limit -> hasMore
      [_json(21)], // меньше limit -> конец
    ]);
    final repo = NewsRepository(api, db);
    final first = await repo.refresh();
    expect(first.hasMore, isTrue);

    final more = await repo.loadMore(first);
    expect(more.hasMore, isFalse);
    expect(more.items.length, 21);
  });

  test('cachedNews отсортирован по дате убыв.', () async {
    await db.replaceNewsCache([
      CachedNewsCompanion.insert(
        id: const Value(5),
        title: 'a',
        body: 'a',
        source: 'sfedu',
        url: 'u5',
        isImportant: false,
        publishedAt: DateTime(2026, 1, 1),
      ),
      CachedNewsCompanion.insert(
        id: const Value(9),
        title: 'b',
        body: 'b',
        source: 'sfedu',
        url: 'u9',
        isImportant: false,
        publishedAt: DateTime(2026, 6, 1),
      ),
    ]);

    final rows = await db.allNews();
    expect(rows.map((r) => r.id), [9, 5]);
  });
}
