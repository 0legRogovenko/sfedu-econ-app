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
        weekType: 'both',
        subgroup: 0,
      );

  test('replaceGroupLessons заменяет кэш группы целиком', () async {
    await db.replaceGroupLessons(3, [row(1, 3), row(2, 3)], 'etag-1');
    await db.replaceGroupLessons(3, [row(5, 3)], 'etag-2');

    final rows = await db.lessonsForGroup(3);
    expect(rows.map((r) => r.id), [5]);

    final meta = await db.metaForGroup(3);
    expect(meta?.etag, 'etag-2');
  });

  test('кэш другой группы не затрагивается', () async {
    await db.replaceGroupLessons(3, [row(1, 3)], 'a');
    await db.replaceGroupLessons(4, [row(2, 4)], 'b');

    expect((await db.lessonsForGroup(3)).length, 1);
    expect((await db.lessonsForGroup(4)).length, 1);
  });

  test('touchSyncedAt обновляет метку, не трогая etag', () async {
    await db.replaceGroupLessons(3, [row(1, 3)], 'etag-1');
    final before = (await db.metaForGroup(3))!.syncedAt;

    await db.touchSyncedAt(3, before.add(const Duration(minutes: 5)));

    final meta = (await db.metaForGroup(3))!;
    expect(meta.etag, 'etag-1');
    expect(meta.syncedAt.isAfter(before), isTrue);
  });

  test('watchLessons реагирует на замену кэша', () async {
    await db.replaceGroupLessons(3, [row(1, 3)], 'a');
    final stream = db.watchLessons(3);

    expect(
      stream.map((rows) => rows.length),
      emitsInOrder([1, 2]),
    );
    await db.replaceGroupLessons(3, [row(1, 3), row(2, 3)], 'b');
  });
}
