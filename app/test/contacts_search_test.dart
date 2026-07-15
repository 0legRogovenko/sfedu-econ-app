import 'package:flutter_test/flutter_test.dart';
import 'package:sfedu_econ/features/contacts/contact.dart';
import 'package:sfedu_econ/features/contacts/contacts_search.dart';

Contact _c({
  int id = 1,
  String section = 'Деканат',
  String name = 'Иванова Елена Игоревна',
  String? role = 'Декан',
}) =>
    Contact(
      id: id,
      section: section,
      name: name,
      role: role,
      office: '203',
      email: 'dekan@sfedu.ru',
      phone: null,
      officeHours: 'Пн–Пт 10:00–12:00',
    );

void main() {
  group('filterContacts', () {
    final list = [
      _c(id: 1, name: 'Иванова Елена Игоревна', role: 'Декан'),
      _c(id: 2, name: 'Петров Андрей Сергеевич', section: 'Кафедра', role: 'Завкафедрой'),
      _c(id: 3, name: 'Сидорова Ольга', section: 'Деканат', role: 'Методист'),
    ];

    test('пустой запрос — все', () {
      expect(filterContacts(list, '').length, 3);
      expect(filterContacts(list, '   ').length, 3);
    });

    test('поиск по имени без учёта регистра', () {
      expect(filterContacts(list, 'иванова').map((c) => c.id), [1]);
      expect(filterContacts(list, 'ПЕТРОВ').map((c) => c.id), [2]);
    });

    test('поиск по роли', () {
      expect(filterContacts(list, 'методист').map((c) => c.id), [3]);
    });

    test('поиск по секции', () {
      expect(filterContacts(list, 'кафедра').map((c) => c.id), [2]);
    });

    test('ничего не найдено — пустой список', () {
      expect(filterContacts(list, 'зззз'), isEmpty);
    });
  });

  group('groupBySection', () {
    test('группирует, сохраняя порядок первого появления секции', () {
      final grouped = groupBySection([
        _c(id: 1, section: 'Деканат'),
        _c(id: 2, section: 'Кафедра экономики'),
        _c(id: 3, section: 'Деканат'),
      ]);
      expect(grouped.keys.toList(), ['Деканат', 'Кафедра экономики']);
      expect(grouped['Деканат']!.map((c) => c.id), [1, 3]);
    });

    test('пустой список — пустая карта', () {
      expect(groupBySection(const []), isEmpty);
    });
  });

  group('Contact.fromJson', () {
    test('парсит ответ API с null-полями', () {
      final c = Contact.fromJson({
        'id': 5,
        'section': 'Деканат',
        'name': 'Иванова Елена Петровна',
        'role': 'Декан',
        'office': '203',
        'email': 'dekan.econ@sfedu.ru',
        'phone': null,
        'office_hours': 'Пн–Пт 10:00–12:00',
      });
      expect(c.name, 'Иванова Елена Петровна');
      expect(c.phone, isNull);
      expect(c.officeHours, 'Пн–Пт 10:00–12:00');
    });
  });
}
