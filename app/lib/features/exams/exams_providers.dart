import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api_client.dart';
import '../onboarding/selected_group.dart';
import '../schedule/schedule_providers.dart' show databaseProvider;
import 'exams_api.dart';
import 'exams_repository.dart';

final examsApiProvider =
    Provider<ExamsApi>((ref) => DioExamsApi(ref.watch(dioProvider)));

final examsRepositoryProvider = Provider<ExamsRepository>(
  (ref) => ExamsRepository(
    ref.watch(examsApiProvider),
    ref.watch(databaseProvider),
  ),
);

/// Экзамены выбранной группы: мгновенно из кэша, затем фоновый refresh.
class ExamsFeedNotifier extends AsyncNotifier<ExamsFeed> {
  ExamsRepository get _repo => ref.read(examsRepositoryProvider);

  @override
  Future<ExamsFeed> build() async {
    // Смена группы пересобирает провайдер — экзамены подтянутся для новой.
    final groupId = ref.watch(selectedGroupIdProvider);
    if (groupId == null) {
      return const ExamsFeed(items: [], offline: false);
    }
    final cached = await _repo.loadCached(groupId);
    Future.microtask(refresh);
    return cached;
  }

  Future<void> refresh() async {
    final groupId = ref.read(selectedGroupIdProvider);
    if (groupId == null) return;
    // try/catch по той же причине, что в новостях и контактах: refresh идёт
    // из Future.microtask в build(), и необработанное исключение оставило бы
    // экран на устаревшем кэше молча.
    try {
      state = AsyncData(await _repo.refresh(groupId));
    } catch (error, stack) {
      state = AsyncError(error, stack);
    }
  }
}

final examsFeedProvider =
    AsyncNotifierProvider<ExamsFeedNotifier, ExamsFeed>(ExamsFeedNotifier.new);
