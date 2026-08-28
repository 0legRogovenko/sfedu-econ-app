/// Тип недели. Термины ЮФУ — «верхняя»/«нижняя» (слов «числитель/знаменатель»
/// в корпусе университета нет ни разу). Значения совпадают с бэкендом.
enum WeekType {
  upper('upper'),
  lower('lower');

  const WeekType(this.value);
  final String value;

  /// Подпись для UI.
  String get label => this == WeekType.upper ? 'верхняя' : 'нижняя';

  static WeekType fromValue(String value) =>
      WeekType.values.firstWhere((t) => t.value == value);
}

/// Дата вида 'yyyy-MM-dd' или null → DateTime (полночь) или null.
DateTime? _parseDate(Object? raw) =>
    raw == null ? null : DateTime.parse(raw as String);

List<DateTime> _parseDates(Object? raw) => (raw as List<dynamic>? ?? const [])
    .map((value) => DateTime.parse(value as String))
    .toList(growable: false);

final _muamSubjectPattern = RegExp(r'^МУАМ\s*[—-]\s*(.+)$');

/// До выбора варианты МУАМ сворачиваются в один общий блок. После выбора
/// карточка показывает конкретную дисциплину без служебного префикса «МУАМ —»,
/// чтобы изменение было видно прямо в расписании.
String scheduleSubjectLabel(String subject, {String? selectedMuamSubject}) {
  final match = _muamSubjectPattern.firstMatch(subject.trimLeft());
  if (match == null) return subject;
  if (selectedMuamSubject == subject) return match.group(1)!.trim();
  return 'МУАМ';
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
    this.moduleId,
    this.validFrom,
    this.validTo,
    this.specificDates = const [],
  });

  final int id;
  final int groupId;
  final int weekday; // 0 = понедельник … 5 = суббота
  final int pairNumber;
  final String startsAt; // "09:00:00"
  final String endsAt;
  final String subject;
  final String? room;

  /// null = пара идёт КАЖДУЮ неделю (основной случай). upper/lower — чередование.
  final WeekType? weekType;
  final int subgroup; // 0 = вся группа
  final String? teacherName;

  /// Ключ группировки в modules, не FK для клиента (может быть null).
  final int? moduleId;

  /// Окно действия пары включительно. Оба null = весь семестр. Клиенту
  /// достаточно проверить validFrom <= дата <= validTo.
  final DateTime? validFrom;
  final DateTime? validTo;

  /// Exact dates for one-off or sparse lessons. Empty means the window is enough.
  final List<DateTime> specificDates;

  factory Lesson.fromJson(Map<String, dynamic> json) => Lesson(
    id: json['id'] as int,
    groupId: json['group_id'] as int,
    weekday: json['weekday'] as int,
    pairNumber: json['pair_number'] as int,
    startsAt: json['starts_at'] as String,
    endsAt: json['ends_at'] as String,
    subject: json['subject'] as String,
    room: json['room'] as String?,
    weekType: json['week_type'] == null
        ? null
        : WeekType.fromValue(json['week_type'] as String),
    subgroup: json['subgroup'] as int,
    teacherName:
        (json['teacher'] as Map<String, dynamic>?)?['full_name'] as String?,
    moduleId: json['module_id'] as int?,
    validFrom: _parseDate(json['valid_from']),
    validTo: _parseDate(json['valid_to']),
    specificDates: _parseDates(json['specific_dates']),
  );
}
