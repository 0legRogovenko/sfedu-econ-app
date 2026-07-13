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

@DriftDatabase(tables: [CachedLessons, ScheduleCacheMeta])
class AppDatabase extends _$AppDatabase {
  AppDatabase() : super(driftDatabase(name: 'sfedu_econ'));

  AppDatabase.forTesting(super.e);

  @override
  int get schemaVersion => 1;

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
}
