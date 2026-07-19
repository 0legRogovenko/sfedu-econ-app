import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api_client.dart';

/// Уровень обучения. Он же говорит, чем подписана группа: у бакалавра — номер,
/// у магистра — программа.
enum EducationLevel {
  bachelor,
  master;

  /// Незнакомое значение (бэкенд завёл новый уровень) не должно ронять декод
  /// всего списка: одна такая группа оставила бы без онбординга всех.
  static EducationLevel parse(Object? raw) => EducationLevel.values.firstWhere(
        (level) => level.name == raw,
        orElse: () => EducationLevel.bachelor,
      );
}

class Group {
  const Group({
    required this.id,
    required this.course,
    required this.number,
    required this.program,
    required this.level,
    required this.subgroupCount,
  });

  final int id;
  final int course;

  /// У магистров номера группы НЕТ — тогда заполнена [program]. Отсюда String?:
  /// приведение null к String бросало TypeError внутри декода списка, и одна
  /// магистерская группа отравляла весь ответ /api/groups — включая бакалавров.
  final String? number;

  /// Программа магистратуры. У бакалавров null.
  final String? program;

  final EducationLevel level;
  final int subgroupCount;

  /// Подпись группы в списке. Магистру показывать нечего кроме программы —
  /// пустой чип, по которому не понять, что выбираешь, хуже.
  String get displayName => number ?? program ?? 'Группа $id';

  factory Group.fromJson(Map<String, dynamic> json) => Group(
        id: json['id'] as int,
        course: json['course'] as int,
        number: json['number'] as String?,
        program: json['program'] as String?,
        level: EducationLevel.parse(json['level']),
        subgroupCount: json['subgroup_count'] as int,
      );
}

/// Имя группы по id для подписей (заголовок расписания, избранные, карточка
/// пары в режиме преподавателя). Фолбэк — если справочник групп ещё не
/// загрузился или id из кэша в нём не нашёлся.
String groupNameOf(List<Group> groups, int id) {
  for (final g in groups) {
    if (g.id == id) return g.displayName;
  }
  return 'Группа $id';
}

/// Список групп с бэкенда. В тестах переопределяется оверрайдом.
final groupsProvider = FutureProvider<List<Group>>((ref) async {
  final dio = ref.watch(dioProvider);
  final response = await dio.get<List<dynamic>>('/api/groups');
  return (response.data ?? [])
      .map((item) => Group.fromJson(item as Map<String, dynamic>))
      .toList();
});
