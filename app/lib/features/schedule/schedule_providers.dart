import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api_client.dart';
import '../../core/db.dart';
import '../onboarding/selected_group.dart';
import 'schedule_api.dart';
import 'schedule_data.dart';
import 'schedule_repository.dart';
import 'schedule_scope.dart';

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

/// Семестр, выбранный СТУДЕНТОМ на своём расписании: Semester.seasonKey (год +
/// сезон) или null — следовать текущему по дате. Пишет его только экран группы;
/// экран преподавателя лишь читает это как стартовое значение (дальше у него
/// свой локальный выбор), поэтому его расписание открывается на том же семестре,
/// что у студента, но переключение у преподавателя не трогает домашний экран.
/// Ключ, а не объект/дата: у группы и преподавателя точные границы семестра чуть
/// расходятся, а год+сезон общий; строка-значение вдобавок не страдает от
/// пересоздания объектов Semester на каждый build.
class ViewedSemesterNotifier extends Notifier<String?> {
  @override
  String? build() => null;

  void select(String? label) => state = label;
}

final viewedSemesterProvider =
    NotifierProvider<ViewedSemesterNotifier, String?>(
        ViewedSemesterNotifier.new);

/// Расписание выбранной группы из кэша (пары + модули + календарь, реактивно).
final scheduleDataProvider = StreamProvider<ScheduleData>((ref) {
  final groupId = ref.watch(selectedGroupIdProvider);
  if (groupId == null) return const Stream.empty();
  return ref
      .watch(scheduleRepositoryProvider)
      .watch(ScheduleScope.group(groupId));
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
    final scope = ScheduleScope.group(groupId);
    final repo = ref.read(scheduleRepositoryProvider);
    final result = await repo.sync(scope);
    state = SyncStatus(
      lastResult: result,
      syncedAt: await repo.syncedAt(scope),
    );
  }
}

final syncStatusProvider =
    NotifierProvider<SyncStatusNotifier, SyncStatus>(SyncStatusNotifier.new);
