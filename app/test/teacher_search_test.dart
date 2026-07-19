import 'package:flutter_test/flutter_test.dart';
import 'package:sfedu_econ/features/teachers/teacher.dart';

const _teachers = [
  Teacher(id: 1, fullName: 'Ласкова Т.С.'),
  Teacher(id: 2, fullName: 'Галич Ж.В.'),
  Teacher(id: 3, fullName: 'Бутова С.В. / Писанка С.А.'),
];

void main() {
  test('пустой запрос — весь список', () {
    expect(filterTeachers(_teachers, ''), _teachers);
    expect(filterTeachers(_teachers, '   '), _teachers);
  });

  test('поиск по подстроке фамилии', () {
    expect(filterTeachers(_teachers, 'Ласк').single.id, 1);
  });

  test('регистр не важен', () {
    expect(filterTeachers(_teachers, 'галич').single.id, 2);
  });

  test('находит второго преподавателя сдвоенной ячейки', () {
    // «Бутова С.В. / Писанка С.А.» — одна запись (так стоит в ячейке
    // расписания), но искать по любой из фамилий должно получаться.
    expect(filterTeachers(_teachers, 'Писанка').single.id, 3);
  });

  test('ничего не найдено — пустой список', () {
    expect(filterTeachers(_teachers, 'Иванов'), isEmpty);
  });

  test('Teacher.fromJson разбирает контракт /api/teachers', () {
    final teacher = Teacher.fromJson({'id': 5, 'full_name': 'Петров А.С.'});
    expect(teacher.id, 5);
    expect(teacher.fullName, 'Петров А.С.');
  });
}
