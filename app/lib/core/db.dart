import 'package:drift/drift.dart';
import 'package:drift_flutter/drift_flutter.dart';

part 'db.g.dart';

class CachedLessons extends Table {
  IntColumn get id => integer()();
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

  @override
  Set<Column> get primaryKey => {id};
}

/// Учебные модули группы. Суррогатный rowid: один module_id может прийти в
/// расписании нескольких групп, а кэш живёт по группам.
class CachedModules extends Table {
  IntColumn get groupId => integer()();
  IntColumn get moduleId => integer()();
  TextColumn get name => text().nullable()();
  TextColumn get dateFrom => text()(); // 'yyyy-MM-dd'
  TextColumn get dateTo => text()();
}

/// Календарь недель группы (диапазон дат → тип недели).
class CachedWeekCalendar extends Table {
  IntColumn get groupId => integer()();
  TextColumn get dateFrom => text()();
  TextColumn get dateTo => text()();
  TextColumn get weekType => text()(); // всегда 'upper'|'lower'
}

class ScheduleCacheMeta extends Table {
  IntColumn get groupId => integer()();
  TextColumn get etag => text().nullable()();
  DateTimeColumn get syncedAt => dateTime()();

  @override
  Set<Column> get primaryKey => {groupId};
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
  int get schemaVersion => 4;

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

  Future<List<CachedLesson>> lessonsForGroup(int groupId) =>
      (select(cachedLessons)..where((t) => t.groupId.equals(groupId))).get();

  Stream<List<CachedLesson>> watchLessons(int groupId) =>
      (select(cachedLessons)..where((t) => t.groupId.equals(groupId))).watch();

  Future<List<CachedModule>> modulesForGroup(int groupId) =>
      (select(cachedModules)
            ..where((t) => t.groupId.equals(groupId))
            ..orderBy([(t) => OrderingTerm(expression: t.dateFrom)]))
          .get();

  Future<List<CachedWeekCalendarData>> weekCalendarForGroup(int groupId) =>
      (select(cachedWeekCalendar)
            ..where((t) => t.groupId.equals(groupId))
            ..orderBy([(t) => OrderingTerm(expression: t.dateFrom)]))
          .get();

  Future<ScheduleCacheMetaData?> metaForGroup(int groupId) =>
      (select(scheduleCacheMeta)..where((t) => t.groupId.equals(groupId)))
          .getSingleOrNull();

  /// Атомарная замена кэша расписания группы (пары + модули + календарь) и меты.
  Future<void> replaceGroupSchedule(
    int groupId,
    List<CachedLessonsCompanion> lessons,
    List<CachedModulesCompanion> modules,
    List<CachedWeekCalendarCompanion> calendar,
    String? etag,
  ) =>
      transaction(() async {
        await (delete(cachedLessons)..where((t) => t.groupId.equals(groupId)))
            .go();
        await (delete(cachedModules)..where((t) => t.groupId.equals(groupId)))
            .go();
        await (delete(cachedWeekCalendar)
              ..where((t) => t.groupId.equals(groupId)))
            .go();
        await batch((b) {
          b.insertAll(cachedLessons, lessons);
          b.insertAll(cachedModules, modules);
          b.insertAll(cachedWeekCalendar, calendar);
        });
        await into(scheduleCacheMeta).insertOnConflictUpdate(
          ScheduleCacheMetaCompanion.insert(
            groupId: Value(groupId),
            etag: Value(etag),
            syncedAt: DateTime.now(),
          ),
        );
      });

  Future<void> touchSyncedAt(int groupId, DateTime at) =>
      (update(scheduleCacheMeta)..where((t) => t.groupId.equals(groupId)))
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
