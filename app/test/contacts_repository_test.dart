import 'package:drift/native.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sfedu_econ/core/db.dart';
import 'package:sfedu_econ/features/contacts/contacts_api.dart';
import 'package:sfedu_econ/features/contacts/contacts_repository.dart';

Map<String, dynamic> _json(int id, {String section = 'Деканат'}) => {
      'id': id,
      'section': section,
      'name': 'Контакт $id',
      'role': 'Роль $id',
      'office': '20$id',
      'email': 'c$id@sfedu.ru',
      'phone': null,
      'office_hours': null,
    };

class FakeContactsApi implements ContactsApi {
  FakeContactsApi(this.responses);
  final List<List<Map<String, dynamic>>?> responses;
  int _i = 0;

  @override
  Future<List<Map<String, dynamic>>?> fetchContacts() async =>
      responses[_i++];
}

void main() {
  late AppDatabase db;
  setUp(() => db = AppDatabase.forTesting(NativeDatabase.memory()));
  tearDown(() => db.close());

  test('refresh заполняет кэш', () async {
    final repo = ContactsRepository(
      FakeContactsApi([[_json(1), _json(2)]]),
      db,
    );

    final feed = await repo.refresh();

    expect(feed.offline, isFalse);
    expect(feed.items.map((c) => c.id), [1, 2]);
    expect((await db.allContacts()).length, 2);
  });

  test('refresh при ошибке сети: кэш цел, offline=true', () async {
    await ContactsRepository(FakeContactsApi([[_json(1)]]), db).refresh();

    final feed =
        await ContactsRepository(FakeContactsApi([null]), db).refresh();

    expect(feed.offline, isTrue);
    expect(feed.items.map((c) => c.id), [1]);
  });

  test('refresh заменяет кэш целиком (удалённые контакты исчезают)', () async {
    final repo1 = ContactsRepository(FakeContactsApi([[_json(1), _json(2)]]), db);
    await repo1.refresh();

    final repo2 = ContactsRepository(FakeContactsApi([[_json(2)]]), db);
    final feed = await repo2.refresh();

    expect(feed.items.map((c) => c.id), [2]);
    expect((await db.allContacts()).length, 1);
  });

  test('loadCached отдаёт сохранённое', () async {
    await ContactsRepository(FakeContactsApi([[_json(7)]]), db).refresh();

    final cached =
        await ContactsRepository(FakeContactsApi([null]), db).loadCached();

    expect(cached.items.single.id, 7);
    expect(cached.offline, isFalse);
  });
}
