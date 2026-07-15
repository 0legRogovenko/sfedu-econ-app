import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api_client.dart';
// databaseProvider переиспользуем из schedule_providers — вся drift-БД живёт
// в одном инстансе (одна и та же локальная база).
import '../schedule/schedule_providers.dart' show databaseProvider;
import 'news_api.dart';
import 'news_repository.dart';

final newsApiProvider =
    Provider<NewsApi>((ref) => DioNewsApi(ref.watch(dioProvider)));

final newsRepositoryProvider = Provider<NewsRepository>(
  (ref) => NewsRepository(
    ref.watch(newsApiProvider),
    ref.watch(databaseProvider),
  ),
);

/// Лента новостей: мгновенно из кэша, затем фоновый refresh; пагинация.
class NewsFeedNotifier extends AsyncNotifier<NewsFeed> {
  NewsRepository get _repo => ref.read(newsRepositoryProvider);

  @override
  Future<NewsFeed> build() async {
    final cached = await _repo.loadCached();
    // фоновое обновление первой страницы, не блокируя первый кадр
    Future.microtask(refresh);
    return cached;
  }

  Future<void> refresh() async {
    final feed = await _repo.refresh();
    state = AsyncData(feed);
  }

  Future<void> loadMore() async {
    final current = state.asData?.value;
    if (current == null || !current.hasMore || current.loadingMore) return;
    state = AsyncData(current.copyWith(loadingMore: true));
    final more = await _repo.loadMore(current);
    state = AsyncData(more.copyWith(loadingMore: false));
  }
}

final newsFeedProvider =
    AsyncNotifierProvider<NewsFeedNotifier, NewsFeed>(NewsFeedNotifier.new);
