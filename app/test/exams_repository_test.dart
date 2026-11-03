import 'package:drift/native.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sfedu_econ/core/db.dart';
import 'package:sfedu_econ/features/exams/exams_api.dart';
import 'package:sfedu_econ/features/exams/exams_repository.dart';

Map<String, dynamic> _examJson(int id) => {
  'id': id,
  'group_id': 3,
  'subject': 'Предмет $id',
  'teacher': 'Чернова О.А.',
  'consultation_at': '2026-04-08T11:00:00',
  'exam_at': '2026-04-09T09:00:00',
  'room': '214',
  'kind': 'устный',
};

class FakeExamsApi implements ExamsApi {
  FakeExamsApi(this.responses);

  final List<ExamsApiResponse> responses;
  final List<String?> sentEtags = [];
  int calls = 0;

  @override
  Future<ExamsApiResponse> fetchExams(int groupId, String? etag) async {
    sentEtags.add(etag);
    return responses[calls++];
  }
}

void main() {
  late AppDatabase db;

  setUp(() => db = AppDatabase.forTesting(NativeDatabase.memory()));
  tearDown(() => db.close());

  test('refresh: 200 → кэш заполнен, etag сохранён, offline=false', () async {
    final api = FakeExamsApi([
      ExamsApiResponse.ok([_examJson(1), _examJson(2)], '"e1"'),
    ]);
    final repo = ExamsRepository(api, db);

    final feed = await repo.refresh(3);

    expect(feed.offline, isFalse);
    expect(feed.items.length, 2);
    expect(feed.items.first.teacher, 'Чернова О.А.');
    expect((await db.examMetaForGroup(3))!.etag, '"e1"');
  });

  test('повторный refresh: шлёт etag, 304 → кэш цел, offline=false', () async {
    final api = FakeExamsApi([
      ExamsApiResponse.ok([_examJson(1)], '"e1"'),
      ExamsApiResponse.notModified(),
    ]);
    final repo = ExamsRepository(api, db);

    await repo.refresh(3);
    final feed = await repo.refresh(3);

    expect(api.sentEtags, [null, '"e1"']);
    expect(feed.offline, isFalse);
    expect(feed.items.length, 1);
  });

  test('ошибка сети: кэш показан, offline=true', () async {
    final api = FakeExamsApi([
      ExamsApiResponse.ok([_examJson(1)], '"e1"'),
      ExamsApiResponse.failure(),
    ]);
    final repo = ExamsRepository(api, db);

    await repo.refresh(3);
    final feed = await repo.refresh(3);

    expect(feed.offline, isTrue);
    expect(feed.items.length, 1); // кэш цел
  });

  test('loadCached отдаёт сохранённые экзамены без сети', () async {
    final api = FakeExamsApi([
      ExamsApiResponse.ok([_examJson(1)], '"e1"'),
    ]);
    final repo = ExamsRepository(api, db);
    await repo.refresh(3);

    final feed = await repo.loadCached(3);
    expect(feed.items.single.subject, 'Предмет 1');
    expect(feed.offline, isFalse);
  });
}
