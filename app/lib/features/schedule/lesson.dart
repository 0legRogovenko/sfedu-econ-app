enum WeekType {
  numerator('numerator'),
  denominator('denominator'),
  both('both');

  const WeekType(this.value);
  final String value;

  static WeekType fromValue(String value) =>
      WeekType.values.firstWhere((t) => t.value == value);
}

class Lesson {
  const Lesson({
    required this.id,
    required this.groupId,
    required this.weekday,
    required this.pairNumber,
    required this.startsAt,
    required this.endsAt,
    required this.subject,
    required this.room,
    required this.weekType,
    required this.subgroup,
    required this.teacherName,
  });

  final int id;
  final int groupId;
  final int weekday; // 0 = понедельник … 5 = суббота
  final int pairNumber;
  final String startsAt; // "09:00:00"
  final String endsAt;
  final String subject;
  final String? room;
  final WeekType weekType;
  final int subgroup; // 0 = вся группа
  final String? teacherName;

  factory Lesson.fromJson(Map<String, dynamic> json) => Lesson(
        id: json['id'] as int,
        groupId: json['group_id'] as int,
        weekday: json['weekday'] as int,
        pairNumber: json['pair_number'] as int,
        startsAt: json['starts_at'] as String,
        endsAt: json['ends_at'] as String,
        subject: json['subject'] as String,
        room: json['room'] as String?,
        weekType: WeekType.fromValue(json['week_type'] as String),
        subgroup: json['subgroup'] as int,
        teacherName:
            (json['teacher'] as Map<String, dynamic>?)?['full_name'] as String?,
      );
}
