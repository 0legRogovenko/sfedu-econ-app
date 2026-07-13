import 'package:drift/native.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sfedu_econ/core/db.dart';
import 'package:sfedu_econ/features/schedule/schedule_api.dart';
import 'package:sfedu_econ/features/schedule/schedule_repository.dart';

Map<String, dynamic> _lessonJson(int id) => {
      'id': id,
      'group_id': 3,
      'weekday': 0,
      'pair_number': id,
      'starts_at': '09:00:00',
      'ends_at': '10:35:00',
      'subject': 'Предмет $id',
      'room': null,
      'week_type': 'both',
      'subgroup': 0,
      'teacher': null,
    };

class FakeApi implements ScheduleApi {
  FakeApi(this.responses);

  final List<ScheduleApiResponse> responses;
  final List<String?> sentEtags = [];
  int calls = 0;

  @override
  Future<ScheduleApiResponse> fetchSchedule(int groupId, String? etag) async {
    sentEtags.add(etag);
    return responses[calls++];
  }
}

void main() {
  late AppDatabase db;

  setUp(() => db = AppDatabase.forTesting(NativeDatabase.memory()));
  tearDown(() => db.close());

  test('первый синк: 200 → кэш заполнен, etag сохранён', () async {
    final api = FakeApi([
      ScheduleApiResponse.ok([_lessonJson(1), _lessonJson(2)], '"e1"'),
    ]);
    final repo = ScheduleRepository(api, db);

    final result = await repo.sync(3);

    expect(result, SyncResult.updated);
    expect(api.sentEtags, [null]);
    expect((await db.lessonsForGroup(3)).length, 2);
    expect((await db.metaForGroup(3))!.etag, '"e1"');
  });

  test('повторный синк: отправляет etag, 304 → кэш не тронут', () async {
    final api = FakeApi([
      ScheduleApiResponse.ok([_lessonJson(1)], '"e1"'),
      ScheduleApiResponse.notModified(),
    ]);
    final repo = ScheduleRepository(api, db);

    await repo.sync(3);
    final result = await repo.sync(3);

    expect(result, SyncResult.notModified);
    expect(api.sentEtags, [null, '"e1"']);
    expect((await db.lessonsForGroup(3)).length, 1);
  });

  test('ошибка сети: кэш не тронут, результат failed', () async {
    final api = FakeApi([
      ScheduleApiResponse.ok([_lessonJson(1)], '"e1"'),
      ScheduleApiResponse.failure(),
    ]);
    final repo = ScheduleRepository(api, db);

    await repo.sync(3);
    final result = await repo.sync(3);

    expect(result, SyncResult.failed);
    expect((await db.lessonsForGroup(3)).length, 1);
  });

  test('watch отдаёт Lesson-модели из кэша', () async {
    final api = FakeApi([
      ScheduleApiResponse.ok([_lessonJson(1)], '"e1"'),
    ]);
    final repo = ScheduleRepository(api, db);
    await repo.sync(3);

    final lessons = await repo.watch(3).first;
    expect(lessons.single.subject, 'Предмет 1');
  });
}
