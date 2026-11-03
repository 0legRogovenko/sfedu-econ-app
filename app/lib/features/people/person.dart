/// Человек единого справочника: контакт, преподаватель расписания — или оба.
///
/// Заменяет два прежних поиска (по контактам и по преподавателям) одним.
/// В списке показываем короткое имя «Фамилия И.О.», на карточке — полное.
class Person {
  const Person({
    required this.id,
    required this.shortName,
    required this.fullName,
    required this.sections,
    required this.roles,
    required this.email,
    required this.hasSchedule,
    required this.lessonCount,
    required this.examCount,
  });

  final String id;
  final String shortName; // «Вольчик В.В.» — для списка и поиска
  final String fullName; // «Вольчик Вячеслав Витальевич» — для карточки
  final List<String>
  sections; // деканат / кафедры; пусто у внешних преподавателей
  final List<String> roles;
  final String? email;
  final bool hasSchedule;
  final int lessonCount;
  final int examCount;

  factory Person.fromJson(Map<String, dynamic> json) => Person(
    id: json['id'] as String,
    shortName: json['short_name'] as String,
    fullName: json['full_name'] as String,
    sections: ((json['sections'] as List?) ?? const [])
        .map((e) => e as String)
        .toList(),
    roles: ((json['roles'] as List?) ?? const [])
        .map((e) => e as String)
        .toList(),
    email: json['email'] as String?,
    hasSchedule: json['has_schedule'] as bool? ?? false,
    lessonCount: json['lesson_count'] as int? ?? 0,
    examCount: json['exam_count'] as int? ?? 0,
  );
}

/// Локальный поиск по короткому и полному имени (регистронезависимо).
/// 128 записей — фильтруем на клиенте, как контакты и преподаватели раньше.
List<Person> filterPeople(List<Person> all, String query) {
  final q = query.trim().toLowerCase();
  if (q.isEmpty) return all;
  return all
      .where(
        (p) =>
            p.shortName.toLowerCase().contains(q) ||
            p.fullName.toLowerCase().contains(q),
      )
      .toList();
}
