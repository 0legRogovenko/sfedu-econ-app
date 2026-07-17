import 'package:drift/drift.dart';

import '../../core/db.dart';
import 'exam_event.dart';
import 'exams_api.dart';

/// Состояние экрана экзаменов.
class ExamsFeed {
  const ExamsFeed({
    required this.items,
    required this.offline,
    this.syncedAt,
  });

  final List<ExamEvent> items;
  final bool offline; // последний refresh не удался — показан кэш
  final DateTime? syncedAt;
}

/// ISO-8601 (naive) из DateTime или null — храним как приходит с сервера.
String? _iso(DateTime? d) => d?.toIso8601String();

class ExamsRepository {
  ExamsRepository(this._api, this._db);

  final ExamsApi _api;
  final AppDatabase _db;

  ExamEvent _fromRow(CachedExam r) => ExamEvent(
        id: r.id,
        groupId: r.groupId,
        subject: r.subject,
        teacher: r.teacher,
        consultationAt:
            r.consultationAt == null ? null : DateTime.parse(r.consultationAt!),
        examAt: r.examAt == null ? null : DateTime.parse(r.examAt!),
        room: r.room,
        kind: r.kind,
      );

  CachedExamsCompanion _toRow(ExamEvent e) => CachedExamsCompanion.insert(
        id: Value(e.id),
        groupId: e.groupId,
        subject: e.subject,
        teacher: Value(e.teacher),
        consultationAt: Value(_iso(e.consultationAt)),
        examAt: Value(_iso(e.examAt)),
        room: Value(e.room),
        kind: Value(e.kind),
      );

  /// Начальное состояние из кэша (мгновенно, до первого refresh).
  Future<ExamsFeed> loadCached(int groupId) async {
    final rows = await _db.examsForGroup(groupId);
    final meta = await _db.examMetaForGroup(groupId);
    return ExamsFeed(
      items: rows.map(_fromRow).toList(),
      offline: false,
      syncedAt: meta?.syncedAt,
    );
  }

  /// Загружает экзамены группы, заменяет кэш. Ошибка сети -> offline, кэш цел.
  /// 304 -> кэш не тронут, offline:false (данные актуальны).
  Future<ExamsFeed> refresh(int groupId) async {
    final meta = await _db.examMetaForGroup(groupId);
    final response = await _api.fetchExams(groupId, meta?.etag);
    switch (response.status) {
      case ExamsApiStatus.failure:
        final rows = await _db.examsForGroup(groupId);
        return ExamsFeed(
          items: rows.map(_fromRow).toList(),
          offline: true,
          syncedAt: meta?.syncedAt,
        );
      case ExamsApiStatus.notModified:
        await _db.touchExamSyncedAt(groupId, DateTime.now());
        final rows = await _db.examsForGroup(groupId);
        return ExamsFeed(
          items: rows.map(_fromRow).toList(),
          offline: false,
          syncedAt: DateTime.now(),
        );
      case ExamsApiStatus.ok:
        final items = response.examsJson!.map(ExamEvent.fromJson).toList();
        await _db.replaceGroupExams(
            groupId, items.map(_toRow).toList(), response.etag);
        return ExamsFeed(
          items: items,
          offline: false,
          syncedAt: DateTime.now(),
        );
    }
  }
}
