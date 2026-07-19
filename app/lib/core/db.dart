import 'package:drift/drift.dart';
import 'package:drift_flutter/drift_flutter.dart';

part 'db.g.dart';

class CachedLessons extends Table {
  IntColumn get id => integer()();

  /// Чей это кэш: 'group:3' или 'teacher:7' (см. ScheduleScope). Отдельно от
  /// [groupId], который остаётся СВОЙСТВОМ ПАРЫ: в расписании преподавателя
  /// именно он подписывает карточку.
  TextColumn get scope => text()();
  IntColumn get groupId => integer()();
  IntColumn get weekday => integer()();
  IntColumn get pairNumber => integer()();
  TextColumn get startsAt => text()();
  TextColumn get endsAt => text()();
  TextColumn get subject => text()();
  TextColumn get room => text().nullable()();
  // null = каждую неделю (основной случай); 'upper'|'lower' — чередование
  TextColumn get weekType => text().nullable()();
  IntColumn get subgroup => integer()();
  TextColumn get teacherName => text().nullable()();
  // Модуль (ключ группировки) и окно действия пары — даты 'yyyy-MM-dd'.
  IntColumn get moduleId => integer().nullable()();
  TextColumn get validFrom => text().nullable()();
  TextColumn get validTo => text().nullable()();

  // Пара с одним id лежит и в кэше группы, и в кэше её преподавателя —
  // одного id мало, ключ составной.
  @override
  Set<Column> get primaryKey => {scope, id};
}

/// Учебные модули расписания. Суррогатный rowid: один module_id приходит в
/// расписании нескольких групп, а кэш живёт по скоупам.
class CachedModules extends Table {
  TextColumn get scope => text()();
  IntColumn get moduleId => integer()();
  TextColumn get name => text().nullable()();
  TextColumn get dateFrom => text()(); // 'yyyy-MM-dd'
  TextColumn get dateTo => text()();
}

/// Календарь недель расписания (диапазон дат → тип недели).
class CachedWeekCalendar extends Table {
  TextColumn get scope => text()();
  TextColumn get dateFrom => text()();
  TextColumn get dateTo => text()();
  TextColumn get weekType => text()(); // всегда 'upper'|'lower'
}

class ScheduleCacheMeta extends Table {
  TextColumn get scope => text()();
  TextColumn get etag => text().nullable()();
  DateTimeColumn get syncedAt => dateTime()();

  @override
  Set<Column> get primaryKey => {scope};
}

/// Экзамены группы (ближайшая сессия).
class CachedExams extends Table {
  IntColumn get id => integer()();
  IntColumn get groupId => integer()();
  TextColumn get subject => text()();
  TextColumn get teacher => text().nullable()();
  TextColumn get consultationAt => text().nullable()(); // ISO-8601 naive
  TextColumn get examAt => text().nullable()();
  TextColumn get room => text().nullable()();
  TextColumn get kind => text().nullable()();

  @override
  Set<Column> get primaryKey => {id};
}

class ExamCacheMeta extends Table {
  IntColumn get groupId => integer()();
  TextColumn get etag => text().nullable()();
  DateTimeColumn get syncedAt => dateTime()();

  @override
  Set<Column> get primaryKey => {groupId};
}

class CachedNews extends Table {
  IntColumn get id => integer()();
  TextColumn get title => text()();
  TextColumn get body => text()();
  TextColumn get source => text()();
  TextColumn get url => text()();
  TextColumn get imageUrl => text().nullable()();
  BoolColumn get isImportant => boolean()();
  DateTimeColumn get publishedAt => dateTime()();

  @override
  Set<Column> get primaryKey => {id};
}

class CachedContacts extends Table {
  IntColumn get id => integer()();
  TextColumn get section => text()();
  TextColumn get name => text()();
  TextColumn get role => text().nullable()();
  TextColumn get office => text().nullable()();
  TextColumn get email => text().nullable()();
  TextColumn get phone => text().nullable()();
  TextColumn get officeHours => text().nullable()();

  @override
  Set<Column> get primaryKey => {id};
}

@DriftDatabase(tables: [
  CachedLessons,
  CachedModules,
  CachedWeekCalendar,
  ScheduleCacheMeta,
  CachedExams,
  ExamCacheMeta,
  CachedNews,
  CachedContacts,
])
class AppDatabase extends _$AppDatabase {
  AppDatabase() : super(driftDatabase(name: 'sfedu_econ'));

  AppDatabase.forTesting(super.e);

  @override
  int get schemaVersion => 5;

  @override
  MigrationStrategy get migration => MigrationStrategy(
        onCreate: (m) => m.createAll(),
        onUpgrade: (m, from, to) async {
          // Это локальный кэш, а не источник истины — при апгрейде схемы
          // проще пересоздать все таблицы, чем писать пошаговые миграции.
          for (final table in allTables) {
            await m.deleteTable(table.actualTableName);
          }
          await m.createAll();
        },
      );

  // --- Расписание ---
  // Скоуп ('group:3' / 'teacher:7') строит ScheduleScope.key; БД принимает его
  // строкой, чтобы core/db не зависел от features.

  Future<List<CachedLesson>> lessonsForScope(String scope) =>
      (select(cachedLessons)..where((t) => t.scope.equals(scope))).get();

  Stream<List<CachedLesson>> watchLessons(String scope) =>
      (select(cachedLessons)..where((t) => t.scope.equals(scope))).watch();

  Future<List<CachedModule>> modulesForScope(String scope) =>
      (select(cachedModules)
            ..where((t) => t.scope.equals(scope))
            ..orderBy([(t) => OrderingTerm(expression: t.dateFrom)]))
          .get();

  Future<List<CachedWeekCalendarData>> weekCalendarForScope(String scope) =>
      (select(cachedWeekCalendar)
            ..where((t) => t.scope.equals(scope))
            ..orderBy([(t) => OrderingTerm(expression: t.dateFrom)]))
          .get();

  Future<ScheduleCacheMetaData?> metaForScope(String scope) =>
      (select(scheduleCacheMeta)..where((t) => t.scope.equals(scope)))
          .getSingleOrNull();

  /// Атомарная замена кэша расписания скоупа (пары + модули + календарь) и меты.
  Future<void> replaceScheduleCache(
    String scope,
    List<CachedLessonsCompanion> lessons,
    List<CachedModulesCompanion> modules,
    List<CachedWeekCalendarCompanion> calendar,
    String? etag,
  ) =>
      transaction(() async {
        await (delete(cachedLessons)..where((t) => t.scope.equals(scope))).go();
        await (delete(cachedModules)..where((t) => t.scope.equals(scope))).go();
        await (delete(cachedWeekCalendar)..where((t) => t.scope.equals(scope)))
            .go();
        await batch((b) {
          b.insertAll(cachedLessons, lessons);
          b.insertAll(cachedModules, modules);
          b.insertAll(cachedWeekCalendar, calendar);
        });
        await into(scheduleCacheMeta).insertOnConflictUpdate(
          ScheduleCacheMetaCompanion.insert(
            scope: scope,
            etag: Value(etag),
            syncedAt: DateTime.now(),
          ),
        );
      });

  Future<void> touchSyncedAt(String scope, DateTime at) =>
      (update(scheduleCacheMeta)..where((t) => t.scope.equals(scope)))
          .write(ScheduleCacheMetaCompanion(syncedAt: Value(at)));

  // --- Экзамены ---

  Future<List<CachedExam>> examsForGroup(int groupId) =>
      (select(cachedExams)..where((t) => t.groupId.equals(groupId))).get();

  Future<ExamCacheMetaData?> examMetaForGroup(int groupId) =>
      (select(examCacheMeta)..where((t) => t.groupId.equals(groupId)))
          .getSingleOrNull();

  /// Атомарная замена кэша экзаменов группы и меты.
  Future<void> replaceGroupExams(
    int groupId,
    List<CachedExamsCompanion> rows,
    String? etag,
  ) =>
      transaction(() async {
        await (delete(cachedExams)..where((t) => t.groupId.equals(groupId)))
            .go();
        await batch((b) => b.insertAll(cachedExams, rows));
        await into(examCacheMeta).insertOnConflictUpdate(
          ExamCacheMetaCompanion.insert(
            groupId: Value(groupId),
            etag: Value(etag),
            syncedAt: DateTime.now(),
          ),
        );
      });

  Future<void> touchExamSyncedAt(int groupId, DateTime at) =>
      (update(examCacheMeta)..where((t) => t.groupId.equals(groupId)))
          .write(ExamCacheMetaCompanion(syncedAt: Value(at)));

  // --- Новости ---

  Future<List<CachedNew>> allNews() => (select(cachedNews)
        ..orderBy([
          (t) => OrderingTerm(expression: t.publishedAt, mode: OrderingMode.desc),
          (t) => OrderingTerm(expression: t.id, mode: OrderingMode.desc),
        ]))
      .get();

  /// Атомарная замена всего кэша новостей (первая страница ленты).
  Future<void> replaceNewsCache(List<CachedNewsCompanion> rows) =>
      transaction(() async {
        await delete(cachedNews).go();
        await batch((b) => b.insertAll(cachedNews, rows));
      });

  // --- Контакты ---

  Future<List<CachedContact>> allContacts() =>
      (select(cachedContacts)..orderBy([(t) => OrderingTerm(expression: t.id)]))
          .get();

  /// Атомарная замена всего кэша контактов (справочник маленький).
  Future<void> replaceContactsCache(List<CachedContactsCompanion> rows) =>
      transaction(() async {
        await delete(cachedContacts).go();
        await batch((b) => b.insertAll(cachedContacts, rows));
      });
}
