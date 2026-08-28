import 'dart:convert';

import 'package:drift/drift.dart';

import '../../core/db.dart';
import 'lesson.dart';
import 'schedule_api.dart';
import 'schedule_data.dart';
import 'schedule_scope.dart';

enum SyncResult { updated, notModified, failed }

/// 'yyyy-MM-dd' из DateTime (даты храним в кэше строкой, как приходят с сервера).
String? _dateStr(DateTime? d) => d == null
    ? null
    : '${d.year.toString().padLeft(4, '0')}-'
          '${d.month.toString().padLeft(2, '0')}-'
          '${d.day.toString().padLeft(2, '0')}';

DateTime? _dateOf(String? s) => s == null ? null : DateTime.parse(s);

String _datesStr(List<DateTime> dates) =>
    jsonEncode(dates.map(_dateStr).toList(growable: false));

List<DateTime> _datesOf(String raw) => (jsonDecode(raw) as List<dynamic>)
    .map((value) => DateTime.parse(value as String))
    .toList(growable: false);

class ScheduleRepository {
  ScheduleRepository(this._api, this._db);

  final ScheduleApi _api;
  final AppDatabase _db;

  Future<SyncResult> sync(ScheduleScope scope) async {
    final key = scope.key;
    final meta = await _db.metaForScope(key);
    final response = await _api.fetchSchedule(scope, meta?.etag);
    switch (response.status) {
      case ScheduleApiStatus.failure:
        return SyncResult.failed;
      case ScheduleApiStatus.notModified:
        await _db.touchSyncedAt(key, DateTime.now());
        return SyncResult.notModified;
      case ScheduleApiStatus.ok:
        // Разбор тела 200 может бросить (неизвестный week_type, кривая дата,
        // отсутствующее поле) — это НЕ DioException, и апи-слой его не ловит.
        // Без этого исключение уходило необработанным, а экран показывал
        // «Пар нет — отдыхаем» вместо честной плашки сбоя. Возвращаем failed,
        // syncedAt не трогаем — логика noData/баннера отрабатывает как надо.
        try {
          return await _persist(key, response);
        } catch (_) {
          return SyncResult.failed;
        }
    }
  }

  Future<SyncResult> _persist(String key, ScheduleApiResponse response) async {
    final data = ScheduleData.fromJson(response.scheduleJson!);
    final lessons = data.lessons
        .map(
          (l) => CachedLessonsCompanion.insert(
            id: l.id,
            scope: key,
            // Группа ПАРЫ, не скоупа: в расписании преподавателя
            // именно она подписывает карточку.
            groupId: l.groupId,
            weekday: l.weekday,
            pairNumber: l.pairNumber,
            startsAt: l.startsAt,
            endsAt: l.endsAt,
            subject: l.subject,
            room: Value(l.room),
            weekType: Value(l.weekType?.value),
            subgroup: l.subgroup,
            teacherName: Value(l.teacherName),
            moduleId: Value(l.moduleId),
            validFrom: Value(_dateStr(l.validFrom)),
            validTo: Value(_dateStr(l.validTo)),
            specificDates: Value(_datesStr(l.specificDates)),
          ),
        )
        .toList();
    final modules = data.modules
        .map(
          (m) => CachedModulesCompanion.insert(
            scope: key,
            moduleId: m.id,
            name: Value(m.name),
            dateFrom: _dateStr(m.dateFrom)!,
            dateTo: _dateStr(m.dateTo)!,
          ),
        )
        .toList();
    final calendar = data.weekCalendar
        .map(
          (w) => CachedWeekCalendarCompanion.insert(
            scope: key,
            dateFrom: _dateStr(w.dateFrom)!,
            dateTo: _dateStr(w.dateTo)!,
            weekType: w.weekType.value,
          ),
        )
        .toList();
    await _db.replaceScheduleCache(
      key,
      lessons,
      modules,
      calendar,
      response.etag,
    );
    return SyncResult.updated;
  }

  Lesson _lessonFromRow(CachedLesson r) => Lesson(
    id: r.id,
    groupId: r.groupId,
    weekday: r.weekday,
    pairNumber: r.pairNumber,
    startsAt: r.startsAt,
    endsAt: r.endsAt,
    subject: r.subject,
    room: r.room,
    weekType: r.weekType == null ? null : WeekType.fromValue(r.weekType!),
    subgroup: r.subgroup,
    teacherName: r.teacherName,
    moduleId: r.moduleId,
    validFrom: _dateOf(r.validFrom),
    validTo: _dateOf(r.validTo),
    specificDates: _datesOf(r.specificDates),
  );

  /// Расписание скоупа из кэша (реактивно). Модули и календарь читаются вместе
  /// с парами: они пишутся одной транзакцией, поэтому эмиссия потока пар уже
  /// видит свежие модули/календарь.
  Stream<ScheduleData> watch(ScheduleScope scope) =>
      _db.watchLessons(scope.key).asyncMap((lessonRows) async {
        final modules = (await _db.modulesForScope(scope.key))
            .map(
              (m) => Module(
                id: m.moduleId,
                name: m.name,
                dateFrom: DateTime.parse(m.dateFrom),
                dateTo: DateTime.parse(m.dateTo),
              ),
            )
            .toList();
        final calendar = (await _db.weekCalendarForScope(scope.key))
            .map(
              (w) => WeekCalendarEntry(
                dateFrom: DateTime.parse(w.dateFrom),
                dateTo: DateTime.parse(w.dateTo),
                weekType: WeekType.fromValue(w.weekType),
              ),
            )
            .toList();
        return ScheduleData(
          lessons: lessonRows.map(_lessonFromRow).toList(),
          modules: modules,
          weekCalendar: calendar,
        );
      });

  Future<DateTime?> syncedAt(ScheduleScope scope) async =>
      (await _db.metaForScope(scope.key))?.syncedAt;
}
