import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sfedu_econ/features/exams/exams_providers.dart';
import 'package:sfedu_econ/features/exams/exams_repository.dart';
import 'package:sfedu_econ/features/news/news_providers.dart';
import 'package:sfedu_econ/features/news/news_repository.dart';
import 'package:sfedu_econ/features/onboarding/selected_group.dart';

/// Репозитории, у которых refresh бросает НЕ DioException: так ведёт себя
/// битый JSON (TypeError внутри fromJson). Такое исключение репозиторий не
/// ловит, и оно доходит до нотифаера.
class _ThrowingNewsRepo implements NewsRepository {
  @override
  Future<NewsFeed> loadCached() async =>
      const NewsFeed(items: [], offline: false, hasMore: false);

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
  test('битый ответ новостей переводит ленту в ошибку, а не в тишину', () async {
    // Регрессия: refresh дёргается из Future.microtask в build(), и без
    // try/catch исключение улетало необработанным — экран оставался на
    // устаревшем кэше без единого признака сбоя.
    final c = ProviderContainer(overrides: [
      newsRepositoryProvider.overrideWithValue(_ThrowingNewsRepo()),
    ]);
    addTearDown(c.dispose);

    await c.read(newsFeedProvider.future);
    await c.read(newsFeedProvider.notifier).refresh();

    expect(c.read(newsFeedProvider), isA<AsyncError<NewsFeed>>());
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
