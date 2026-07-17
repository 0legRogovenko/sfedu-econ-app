import 'package:drift/drift.dart' show Value;
import 'package:drift/native.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sfedu_econ/core/db.dart';

void main() {
  late AppDatabase db;

  setUp(() => db = AppDatabase.forTesting(NativeDatabase.memory()));
  tearDown(() => db.close());

  CachedLessonsCompanion row(int id, int groupId) =>
      CachedLessonsCompanion.insert(
        id: Value(id),
        groupId: groupId,
        weekday: 0,
        pairNumber: 1,
        startsAt: '09:00:00',
        endsAt: '10:35:00',
        subject: 'Макроэкономика',
        // weekType null = каждую неделю (основной случай)
        subgroup: 0,
      );

  CachedModulesCompanion moduleRow(int groupId) =>
      CachedModulesCompanion.insert(
        groupId: groupId,
        moduleId: 1,
        dateFrom: '2025-09-01',
        dateTo: '2025-10-26',
      );

  CachedWeekCalendarCompanion calRow(int groupId) =>
      CachedWeekCalendarCompanion.insert(
        groupId: groupId,
        dateFrom: '2025-09-01',
        dateTo: '2025-09-07',
        weekType: 'upper',
      );

  test('replaceGroupSchedule заменяет кэш группы целиком', () async {
    await db.replaceGroupSchedule(
        3, [row(1, 3), row(2, 3)], [moduleRow(3)], [calRow(3)], 'etag-1');
    await db.replaceGroupSchedule(3, [row(5, 3)], [], [], 'etag-2');

    final rows = await db.lessonsForGroup(3);
    expect(rows.map((r) => r.id), [5]);
    // модули и календарь тоже заменяются (второй прогон — пустые)
    expect(await db.modulesForGroup(3), isEmpty);
    expect(await db.weekCalendarForGroup(3), isEmpty);

    final meta = await db.metaForGroup(3);
    expect(meta?.etag, 'etag-2');
  });

  test('модули и календарь переживают в кэше', () async {
    await db.replaceGroupSchedule(
        3, [row(1, 3)], [moduleRow(3)], [calRow(3)], 'a');

    expect((await db.modulesForGroup(3)).single.moduleId, 1);
    expect((await db.weekCalendarForGroup(3)).single.weekType, 'upper');
  });

  test('кэш другой группы не затрагивается', () async {
    await db.replaceGroupSchedule(3, [row(1, 3)], [], [], 'a');
    await db.replaceGroupSchedule(4, [row(2, 4)], [], [], 'b');

    expect((await db.lessonsForGroup(3)).length, 1);
    expect((await db.lessonsForGroup(4)).length, 1);
  });

  test('touchSyncedAt обновляет метку, не трогая etag', () async {
    await db.replaceGroupSchedule(3, [row(1, 3)], [], [], 'etag-1');
    final before = (await db.metaForGroup(3))!.syncedAt;

    await db.touchSyncedAt(3, before.add(const Duration(minutes: 5)));

    final meta = (await db.metaForGroup(3))!;
    expect(meta.etag, 'etag-1');
    expect(meta.syncedAt.isAfter(before), isTrue);
  });

  test('watchLessons реагирует на замену кэша', () async {
    await db.replaceGroupSchedule(3, [row(1, 3)], [], [], 'a');
    final stream = db.watchLessons(3);

    expect(
      stream.map((rows) => rows.length),
      emitsInOrder([1, 2]),
    );
    await db.replaceGroupSchedule(3, [row(1, 3), row(2, 3)], [], [], 'b');
  });

  group('экзамены', () {
    CachedExamsCompanion examRow(int id, int groupId) =>
        CachedExamsCompanion.insert(
          id: Value(id),
          groupId: groupId,
          subject: 'Экономика',
        );

    test('replaceGroupExams заменяет кэш и сохраняет etag', () async {
      await db.replaceGroupExams(3, [examRow(1, 3), examRow(2, 3)], 'e1');
      await db.replaceGroupExams(3, [examRow(5, 3)], 'e2');

      expect((await db.examsForGroup(3)).map((r) => r.id), [5]);
      expect((await db.examMetaForGroup(3))!.etag, 'e2');
    });

    test('экзамены другой группы не затрагиваются', () async {
      await db.replaceGroupExams(3, [examRow(1, 3)], 'a');
      await db.replaceGroupExams(4, [examRow(2, 4)], 'b');

      expect((await db.examsForGroup(3)).length, 1);
      expect((await db.examsForGroup(4)).length, 1);
    });
  });
}
