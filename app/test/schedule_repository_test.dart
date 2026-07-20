import 'package:drift/native.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sfedu_econ/core/db.dart';
import 'package:sfedu_econ/features/schedule/schedule_api.dart';
import 'package:sfedu_econ/features/schedule/schedule_repository.dart';
import 'package:sfedu_econ/features/schedule/schedule_scope.dart';

Map<String, dynamic> _lessonJson(int id) => {
      'id': id,
      'group_id': 3,
      'weekday': 0,
      'pair_number': id,
      'starts_at': '09:00:00',
      'ends_at': '10:35:00',
      'subject': 'Предмет $id',
      'room': null,
      'week_type': null,
      'subgroup': 0,
      'teacher': null,
      'module_id': 2,
      'valid_from': '2025-09-01',
      'valid_to': '2025-10-26',
    };

Map<String, dynamic> _schedule(List<Map<String, dynamic>> lessons) => {
      'lessons': lessons,
      'modules': [
        {
          'id': 2,
          'name': '1 модуль',
          'date_from': '2025-09-01',
          'date_to': '2025-10-26',
        }
      ],
      'week_calendar': [
        {
          'date_from': '2025-09-01',
          'date_to': '2025-09-07',
          'week_type': 'upper',
        }
      ],
    };

class FakeApi implements ScheduleApi {
  FakeApi(this.responses);

  final List<ScheduleApiResponse> responses;
  final List<String?> sentEtags = [];
  int calls = 0;

  final List<ScheduleScope> sentScopes = [];

  @override
  Future<ScheduleApiResponse> fetchSchedule(
      ScheduleScope scope, String? etag) async {
    sentScopes.add(scope);
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
      ScheduleApiResponse.ok(
          _schedule([_lessonJson(1), _lessonJson(2)]), '"e1"'),
    ]);
    final repo = ScheduleRepository(api, db);

    final result = await repo.sync(const ScheduleScope.group(3));

    expect(result, SyncResult.updated);
    expect(api.sentEtags, [null]);
    expect((await db.lessonsForScope('group:3')).length, 2);
    // модули и календарь тоже осели в кэше
    expect((await db.modulesForScope('group:3')).single.moduleId, 2);
    expect((await db.weekCalendarForScope('group:3')).single.weekType, 'upper');
    expect((await db.metaForScope('group:3'))!.etag, '"e1"');
  });

  test('повторный синк: отправляет etag, 304 → кэш не тронут', () async {
    final api = FakeApi([
      ScheduleApiResponse.ok(_schedule([_lessonJson(1)]), '"e1"'),
      ScheduleApiResponse.notModified(),
    ]);
    final repo = ScheduleRepository(api, db);

    await repo.sync(const ScheduleScope.group(3));
    final result = await repo.sync(const ScheduleScope.group(3));

    expect(result, SyncResult.notModified);
    expect(api.sentEtags, [null, '"e1"']);
    expect((await db.lessonsForScope('group:3')).length, 1);
  });

  test('ошибка сети: кэш не тронут, результат failed', () async {
    final api = FakeApi([
      ScheduleApiResponse.ok(_schedule([_lessonJson(1)]), '"e1"'),
      ScheduleApiResponse.failure(),
    ]);
    final repo = ScheduleRepository(api, db);

    await repo.sync(const ScheduleScope.group(3));
    final result = await repo.sync(const ScheduleScope.group(3));

    expect(result, SyncResult.failed);
    expect((await db.lessonsForScope('group:3')).length, 1);
  });

  test('битый 200 (неизвестный тип недели) → failed, прежний кэш цел', () async {
    // Регрессия #5: разбор тела 200 может бросить (WeekType.fromValue на
    // неизвестном значении). Раньше исключение уходило необработанным, синк
    // «падал в тишину», а экран показывал «Пар нет» вместо честного сбоя.
    final bad = _lessonJson(2)..['week_type'] = 'диагональ';
    final api = FakeApi([
      ScheduleApiResponse.ok(_schedule([_lessonJson(1)]), '"e1"'),
      ScheduleApiResponse.ok(_schedule([bad]), '"e2"'),
    ]);
    final repo = ScheduleRepository(api, db);

    await repo.sync(const ScheduleScope.group(3)); // кэш = 1 пара
    final result = await repo.sync(const ScheduleScope.group(3)); // битый

    expect(result, SyncResult.failed);
    // прежний (успешный) кэш не затёрт битым ответом
    expect((await db.lessonsForScope('group:3')).length, 1);
    expect((await db.metaForScope('group:3'))!.etag, '"e1"');
  });

  test('скоуп преподавателя кэшируется отдельно от скоупа группы', () async {
    // Пара с одним id приходит в обоих расписаниях; без скоупа вторая
    // синхронизация затирала бы первую.
    final api = FakeApi([
      ScheduleApiResponse.ok(_schedule([_lessonJson(1)]), '"g"'),
      ScheduleApiResponse.ok(_schedule([_lessonJson(1)]), '"t"'),
    ]);
    final repo = ScheduleRepository(api, db);

    await repo.sync(const ScheduleScope.group(3));
    await repo.sync(const ScheduleScope.teacher(7));

    expect(api.sentScopes,
        [const ScheduleScope.group(3), const ScheduleScope.teacher(7)]);
    expect((await db.lessonsForScope('group:3')).length, 1);
    expect((await db.lessonsForScope('teacher:7')).length, 1);
    expect((await db.metaForScope('group:3'))!.etag, '"g"');
    expect((await db.metaForScope('teacher:7'))!.etag, '"t"');
  });

  test('etag берётся из меты своего скоупа', () async {
    // Регрессия: с общей метой синк преподавателя отправил бы etag группы,
    // получил 304 — и расписание преподавателя осталось бы пустым навсегда.
    final api = FakeApi([
      ScheduleApiResponse.ok(_schedule([_lessonJson(1)]), '"g"'),
      ScheduleApiResponse.ok(_schedule([_lessonJson(1)]), '"t"'),
    ]);
    final repo = ScheduleRepository(api, db);

    await repo.sync(const ScheduleScope.group(3));
    await repo.sync(const ScheduleScope.teacher(7));

    expect(api.sentEtags, [null, null]);
  });

  test('watch отдаёт ScheduleData с парами, модулями и календарём', () async {
    final api = FakeApi([
      ScheduleApiResponse.ok(_schedule([_lessonJson(1)]), '"e1"'),
    ]);
    final repo = ScheduleRepository(api, db);
    await repo.sync(const ScheduleScope.group(3));

    final data = await repo.watch(const ScheduleScope.group(3)).first;
    expect(data.lessons.single.subject, 'Предмет 1');
    expect(data.lessons.single.moduleId, 2);
    expect(data.lessons.single.validFrom, DateTime(2025, 9, 1));
    expect(data.modules.single.name, '1 модуль');
    expect(data.weekCalendar.single.dateFrom, DateTime(2025, 9, 1));
  });
}
