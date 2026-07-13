import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api_client.dart';
import '../../core/db.dart';
import '../onboarding/selected_group.dart';
import 'lesson.dart';
import 'schedule_api.dart';
import 'schedule_repository.dart';

final databaseProvider = Provider<AppDatabase>((ref) {
  final db = AppDatabase();
  ref.onDispose(db.close);
  return db;
});

final scheduleApiProvider =
    Provider<ScheduleApi>((ref) => DioScheduleApi(ref.watch(dioProvider)));

final scheduleRepositoryProvider = Provider<ScheduleRepository>((ref) =>
    ScheduleRepository(
        ref.watch(scheduleApiProvider), ref.watch(databaseProvider)));

/// Пары выбранной группы из кэша (реактивно).
final lessonsProvider = StreamProvider<List<Lesson>>((ref) {
  final groupId = ref.watch(selectedGroupIdProvider);
  if (groupId == null) return const Stream.empty();
  return ref.watch(scheduleRepositoryProvider).watch(groupId);
});

/// Статус последней синхронизации (для плашки «Данные от…»).
class SyncStatus {
  const SyncStatus({required this.lastResult, required this.syncedAt});
  final SyncResult? lastResult;
  final DateTime? syncedAt;
}

class SyncStatusNotifier extends Notifier<SyncStatus> {
  @override
  SyncStatus build() => const SyncStatus(lastResult: null, syncedAt: null);

  Future<void> sync() async {
    final groupId = ref.read(selectedGroupIdProvider);
    if (groupId == null) return;
    final repo = ref.read(scheduleRepositoryProvider);
    final result = await repo.sync(groupId);
    state = SyncStatus(
      lastResult: result,
      syncedAt: await repo.syncedAt(groupId),
    );
  }
}

final syncStatusProvider =
    NotifierProvider<SyncStatusNotifier, SyncStatus>(SyncStatusNotifier.new);
