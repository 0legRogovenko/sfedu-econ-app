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

  // Пока идёт refresh (в т.ч. стартовый фоновой), loadMore не запускаем:
  // иначе докидка со стартового курсора кэша могла бы затереть свежую
  // первую страницу устаревшими строками (итог ревью).
  bool _refreshing = false;

  @override
  Future<NewsFeed> build() async {
    final cached = await _repo.loadCached();
    // фоновое обновление первой страницы, не блокируя первый кадр
    Future.microtask(refresh);
    return cached;
  }

  Future<void> refresh() async {
    _refreshing = true;
    // catch, а не только finally: refresh дёргается из Future.microtask в
    // build(), где исключение (например, кривой JSON — это TypeError, а не
    // DioException, и репозиторий его не ловит) улетело бы необработанным,
    // оставив экран на устаревшем кэше без единого признака сбоя. Та же
    // починка, что уже сделана в контактах.
    try {
      final feed = await _repo.refresh();
      state = AsyncData(feed);
    } catch (error, stack) {
      state = AsyncError(error, stack);
    } finally {
      _refreshing = false;
    }
  }

  Future<void> loadMore() async {
    if (_refreshing) return;
    final current = state.asData?.value;
    if (current == null || !current.hasMore || current.loadingMore) return;
    state = AsyncData(current.copyWith(loadingMore: true));
    final more = await _repo.loadMore(current);
    state = AsyncData(more.copyWith(loadingMore: false));
  }
}

final newsFeedProvider =
    AsyncNotifierProvider<NewsFeedNotifier, NewsFeed>(NewsFeedNotifier.new);
