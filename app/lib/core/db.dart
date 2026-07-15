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
  TextColumn get weekType => text()();
  IntColumn get subgroup => integer()();
  TextColumn get teacherName => text().nullable()();

  @override
  Set<Column> get primaryKey => {id};
}

class ScheduleCacheMeta extends Table {
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

@DriftDatabase(
    tables: [CachedLessons, ScheduleCacheMeta, CachedNews, CachedContacts])
class AppDatabase extends _$AppDatabase {
  AppDatabase() : super(driftDatabase(name: 'sfedu_econ'));

  AppDatabase.forTesting(super.e);

  @override
  int get schemaVersion => 3;

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

  Future<List<CachedLesson>> lessonsForGroup(int groupId) =>
      (select(cachedLessons)..where((t) => t.groupId.equals(groupId))).get();

  Stream<List<CachedLesson>> watchLessons(int groupId) =>
      (select(cachedLessons)..where((t) => t.groupId.equals(groupId))).watch();

  Future<ScheduleCacheMetaData?> metaForGroup(int groupId) =>
      (select(scheduleCacheMeta)..where((t) => t.groupId.equals(groupId)))
          .getSingleOrNull();

  /// Атомарная замена кэша группы + обновление меты.
  Future<void> replaceGroupLessons(
    int groupId,
    List<CachedLessonsCompanion> rows,
    String? etag,
  ) =>
      transaction(() async {
        await (delete(cachedLessons)..where((t) => t.groupId.equals(groupId)))
            .go();
        await batch((b) => b.insertAll(cachedLessons, rows));
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
