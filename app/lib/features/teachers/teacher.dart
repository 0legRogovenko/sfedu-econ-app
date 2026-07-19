/// Преподаватель из расписания. ФИО короткие («Ласкова Т.С.»), как в ячейке
/// файла ЮФУ; встречаются сдвоенные («Бутова С.В. / Писанка С.А.») — это одна
/// запись, потому что в расписании это одна ячейка.
class Teacher {
  const Teacher({required this.id, required this.fullName});

  final int id;
  final String fullName;

  factory Teacher.fromJson(Map<String, dynamic> json) => Teacher(
        id: json['id'] as int,
        fullName: json['full_name'] as String,
      );
}

/// Поиск по подстроке ФИО (регистронезависимо). Список маленький (129 записей),
/// поэтому фильтруем на клиенте — как в контактах.
List<Teacher> filterTeachers(List<Teacher> all, String query) {
  final q = query.trim().toLowerCase();
  if (q.isEmpty) return all;
  return all.where((t) => t.fullName.toLowerCase().contains(q)).toList();
}
