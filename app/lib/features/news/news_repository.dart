import 'package:drift/drift.dart';

import '../../core/db.dart';
import 'news_api.dart';
import 'news_item.dart';

const _pageLimit = 20;

/// Состояние ленты новостей.
class NewsFeed {
  const NewsFeed({
    required this.items,
    required this.offline,
    required this.hasMore,
    this.loadingMore = false,
  });

  final List<NewsItem> items;
  final bool offline; // последний refresh не удался — показан кэш
  final bool hasMore;
  final bool loadingMore;

  NewsFeed copyWith({
    List<NewsItem>? items,
    bool? offline,
    bool? hasMore,
    bool? loadingMore,
  }) => NewsFeed(
    items: items ?? this.items,
    offline: offline ?? this.offline,
    hasMore: hasMore ?? this.hasMore,
    loadingMore: loadingMore ?? this.loadingMore,
  );
}

class NewsRepository {
  NewsRepository(this._api, this._db);

  final NewsApi _api;
  final AppDatabase _db;

  NewsItem _fromRow(CachedNew r) => NewsItem(
    id: r.id,
    title: r.title,
    body: r.body,
    source: r.source,
    url: r.url,
    imageUrl: r.imageUrl,
    isImportant: r.isImportant,
    publishedAt: r.publishedAt,
  );

  CachedNewsCompanion _toRow(NewsItem n) => CachedNewsCompanion.insert(
    id: Value(n.id),
    title: n.title,
    body: n.body,
    source: n.source,
    url: n.url,
    imageUrl: Value(n.imageUrl),
    isImportant: n.isImportant,
    publishedAt: n.publishedAt,
  );

  /// Начальное состояние из кэша (мгновенно, до первого refresh).
  Future<NewsFeed> loadCached() async {
    final rows = await _db.allNews();
    return NewsFeed(
      items: rows.map(_fromRow).toList(),
      offline: false,
      hasMore: rows.length >= _pageLimit,
    );
  }

  /// Загружает первую страницу, заменяет кэш. Ошибка сети -> offline, кэш цел.
  Future<NewsFeed> refresh() async {
    final page = await _api.fetchPage(limit: _pageLimit);
    if (page == null) {
      final rows = await _db.allNews();
      return NewsFeed(
        items: rows.map(_fromRow).toList(),
        offline: true,
        hasMore: rows.length >= _pageLimit,
      );
    }
    final items = page.map(NewsItem.fromJson).toList();
    await _db.replaceNewsCache(items.map(_toRow).toList());
    return NewsFeed(
      items: items,
      offline: false,
      hasMore: items.length >= _pageLimit,
    );
  }

  /// Докидывает следующую страницу по keyset-курсору (publishedAt, id).
  Future<NewsFeed> loadMore(NewsFeed current) async {
    if (!current.hasMore || current.items.isEmpty) return current;
    final last = current.items.last;
    final page = await _api.fetchPage(
      before: last.publishedAt,
      beforeId: last.id,
      limit: _pageLimit,
    );
    if (page == null) return current; // тихо оставляем как есть

    final more = page.map(NewsItem.fromJson).toList();
    return current.copyWith(
      items: [...current.items, ...more],
      hasMore: more.length >= _pageLimit,
    );
  }
}
