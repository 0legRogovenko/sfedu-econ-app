import 'package:flutter_test/flutter_test.dart';
import 'package:sfedu_econ/features/onboarding/group_repository.dart';

/// Декод групп с бэкенда. Тесты онбординга конструируют Group напрямую и
/// fromJson против настоящего ответа не гоняют — поэтому магистры с
/// number:null роняли декод, а через него и весь список: одна испорченная
/// группа отравляла ответ ВСЕМ, включая бакалавров.
void main() {
  test('магистр без номера декодируется, а не бросает TypeError', () {
    final group = Group.fromJson(const {
      'id': 7,
      'course': 1,
      'number': null,
      'program': 'Финансы и кредит',
      'level': 'master',
      'subgroup_count': 1,
    });

    expect(group.id, 7);
    expect(group.number, isNull);
    expect(group.program, 'Финансы и кредит');
    expect(group.level, EducationLevel.master);
  });

  test('у бакалавра номер есть, а программы нет', () {
    final group = Group.fromJson(const {
      'id': 1,
      'course': 1,
      'number': '1.1',
      'program': null,
      'level': 'bachelor',
      'subgroup_count': 2,
    });

    expect(group.number, '1.1');
    expect(group.program, isNull);
    expect(group.level, EducationLevel.bachelor);
  });

  test('одна магистерская группа не роняет декод всего списка', () {
    final groups = [
      const {
        'id': 1,
        'course': 1,
        'number': '1.1',
        'program': null,
        'level': 'bachelor',
        'subgroup_count': 2,
      },
      const {
        'id': 7,
        'course': 1,
        'number': null,
        'program': 'Финансы и кредит',
        'level': 'master',
        'subgroup_count': 1,
      },
    ].map(Group.fromJson).toList();

    expect(groups, hasLength(2));
  });

  group('displayName — то, что видит студент в списке', () {
    test('бакалавру показываем номер', () {
      const group = Group(
        id: 1,
        course: 1,
        number: '1.1',
        program: null,
        level: EducationLevel.bachelor,
        subgroupCount: 2,
      );
      expect(group.displayName, '1.1');
    });

    test('магистру вместо номера — программа', () {
      const group = Group(
        id: 7,
        course: 1,
        number: null,
        program: 'Финансы и кредит',
        level: EducationLevel.master,
        subgroupCount: 1,
      );
      expect(group.displayName, 'Финансы и кредит');
    });

    test('нет ни номера, ни программы — пустой чип показывать нельзя', () {
      const group = Group(
        id: 9,
        course: 1,
        number: null,
        program: null,
        level: EducationLevel.master,
        subgroupCount: 1,
      );
      expect(group.displayName, isNotEmpty);
    });
  });

  test('незнакомый level с бэкенда не роняет декод', () {
    final group = Group.fromJson(const {
      'id': 9,
      'course': 1,
      'number': '1.1',
      'program': null,
      'level': 'specialist',
      'subgroup_count': 2,
    });
    expect(group.level, EducationLevel.bachelor);
  });
}
