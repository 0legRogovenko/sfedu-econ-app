import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sfedu_econ/features/exams/exams_providers.dart';
import 'package:sfedu_econ/features/exams/exams_repository.dart';
import 'package:sfedu_econ/features/news/news_item.dart';
import 'package:sfedu_econ/features/news/news_providers.dart';
import 'package:sfedu_econ/features/news/news_repository.dart';
import 'package:sfedu_econ/features/onboarding/selected_group.dart';

final _cachedItem = NewsItem(
  id: 1,
  title: 'Из кэша',
  body: '',
  source: 'sfedu',
  url: 'https://sfedu.ru/1',
  imageUrl: null,
  isImportant: false,
  publishedAt: DateTime(2026, 1, 1),
);

/// Репозитории, у которых refresh бросает НЕ DioException: так ведёт себя
/// битый JSON (TypeError внутри fromJson). Такое исключение репозиторий не
/// ловит, и оно доходит до нотифаера. loadCached отдаёт непустой кэш —
/// проверяем, что битый refresh его НЕ стирает.
class _ThrowingNewsRepo implements NewsRepository {
  @override
  Future<NewsFeed> loadCached() async =>
      NewsFeed(items: [_cachedItem], offline: false, hasMore: false);

  @override
  Future<NewsFeed> refresh() async => throw TypeError();

  @override
  Future<NewsFeed> loadMore(NewsFeed current) async => current;
}

class _ThrowingExamsRepo implements ExamsRepository {
  @override
  Future<ExamsFeed> loadCached(int groupId) async =>
      const ExamsFeed(items: [], offline: false);

  @override
  Future<ExamsFeed> refresh(int groupId) async => throw TypeError();
}

void main() {
  test('битый ответ новостей не стирает кэш, а помечает offline (не тишина)',
      () async {
    // Регрессия #8: битый JSON при refresh НЕ должен ронять уже показанную
    // ленту в full-screen ошибку без retry. Кэш сохраняется, лента помечается
    // offline — сработает баннер/кнопка «Обновить». И это не «тишина»:
    // исключение из Future.microtask в build() обработано, а не улетело мимо.
    final c = ProviderContainer(overrides: [
      newsRepositoryProvider.overrideWithValue(_ThrowingNewsRepo()),
    ]);
    addTearDown(c.dispose);

    await c.read(newsFeedProvider.future);
    await c.read(newsFeedProvider.notifier).refresh();

    final state = c.read(newsFeedProvider);
    expect(state, isA<AsyncData<NewsFeed>>()); // не ошибка на весь экран
    expect(state.value!.offline, isTrue); // помечено offline → есть retry
    expect(state.value!.items, [_cachedItem]); // кэш НЕ стёрт
  });

  test('битый ответ экзаменов переводит экран в ошибку, а не в тишину',
      () async {
    final c = ProviderContainer(overrides: [
      selectedGroupIdProvider.overrideWith(() => FakeSelectedGroupId(3)),
      examsRepositoryProvider.overrideWithValue(_ThrowingExamsRepo()),
    ]);
    addTearDown(c.dispose);

    await c.read(examsFeedProvider.future);
    await c.read(examsFeedProvider.notifier).refresh();

    expect(c.read(examsFeedProvider), isA<AsyncError<ExamsFeed>>());
  });
}
