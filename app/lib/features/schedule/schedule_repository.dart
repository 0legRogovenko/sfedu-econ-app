import 'package:drift/drift.dart';

import '../../core/db.dart';
import 'lesson.dart';
import 'schedule_api.dart';

enum SyncResult { updated, notModified, failed }

class ScheduleRepository {
  ScheduleRepository(this._api, this._db);

  final ScheduleApi _api;
  final AppDatabase _db;

  Future<SyncResult> sync(int groupId) async {
    final meta = await _db.metaForGroup(groupId);
    final response = await _api.fetchSchedule(groupId, meta?.etag);
    switch (response.status) {
      case ScheduleApiStatus.failure:
        return SyncResult.failed;
      case ScheduleApiStatus.notModified:
        await _db.touchSyncedAt(groupId, DateTime.now());
        return SyncResult.notModified;
      case ScheduleApiStatus.ok:
        final rows = response.lessonsJson!
            .map(Lesson.fromJson)
            .map((l) => CachedLessonsCompanion.insert(
                  id: Value(l.id),
                  groupId: l.groupId,
                  weekday: l.weekday,
                  pairNumber: l.pairNumber,
                  startsAt: l.startsAt,
                  endsAt: l.endsAt,
                  subject: l.subject,
                  room: Value(l.room),
                  weekType: l.weekType.value,
                  subgroup: l.subgroup,
                  teacherName: Value(l.teacherName),
                ))
            .toList();
        await _db.replaceGroupLessons(groupId, rows, response.etag);
        return SyncResult.updated;
    }
  }

  Stream<List<Lesson>> watch(int groupId) =>
      _db.watchLessons(groupId).map((rows) => rows
          .map((r) => Lesson(
                id: r.id,
                groupId: r.groupId,
                weekday: r.weekday,
                pairNumber: r.pairNumber,
                startsAt: r.startsAt,
                endsAt: r.endsAt,
                subject: r.subject,
                room: r.room,
                weekType: WeekType.fromValue(r.weekType),
                subgroup: r.subgroup,
                teacherName: r.teacherName,
              ))
          .toList());

  Future<DateTime?> syncedAt(int groupId) async =>
      (await _db.metaForGroup(groupId))?.syncedAt;
}
