/// Экзамен/зачёт группы (ответ /api/exams и строка кэша).
///
/// Любое из полей дат/преподавателя/аудитории/формы может быть null — это
/// дыры источника (ЮФУ не заполнил), а не дефект. Такие поля в UI показываем
/// как «уточняется», запись НЕ прячем.
class ExamEvent {
  const ExamEvent({
    required this.id,
    required this.groupId,
    required this.subject,
    required this.teacher,
    required this.consultationAt,
    required this.examAt,
    required this.room,
    required this.kind,
  });

  final int id;
  final int groupId;
  final String subject;
  final String? teacher; // может быть несколько ФИО через запятую
  final DateTime? consultationAt;
  final DateTime? examAt;
  final String? room;
  final String? kind; // форма свободным текстом: «устный», «письменный»…

  static DateTime? _parseDt(Object? raw) =>
      raw == null ? null : DateTime.parse(raw as String);

  factory ExamEvent.fromJson(Map<String, dynamic> json) => ExamEvent(
        id: json['id'] as int,
        groupId: json['group_id'] as int,
        subject: json['subject'] as String,
        teacher: json['teacher'] as String?,
        consultationAt: _parseDt(json['consultation_at']),
        examAt: _parseDt(json['exam_at']),
        room: json['room'] as String?,
        kind: json['kind'] as String?,
      );
}
