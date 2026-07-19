/// Чьё это расписание: группы или преподавателя.
///
/// Одна и та же пара приходит и в расписании группы, и в расписании её
/// преподавателя, поэтому id пары не уникален сам по себе — ключом кэша
/// служит пара (scope, id). Раньше кэш ключевался только groupId, и добавление
/// режима преподавателя без скоупа перезаписывало бы расписание группы.
class ScheduleScope {
  const ScheduleScope.group(this.id) : kind = groupKind;
  const ScheduleScope.teacher(this.id) : kind = teacherKind;

  static const groupKind = 'group';
  static const teacherKind = 'teacher';

  final String kind;
  final int id;

  bool get isTeacher => kind == teacherKind;

  /// Ключ строки в кэше: 'group:3', 'teacher:7'.
  String get key => '$kind:$id';

  /// Имя query-параметра /api/schedule для этого скоупа.
  String get queryParam => isTeacher ? 'teacher_id' : 'group_id';

  @override
  bool operator ==(Object other) =>
      other is ScheduleScope && other.kind == kind && other.id == id;

  @override
  int get hashCode => Object.hash(kind, id);

  @override
  String toString() => key;
}
