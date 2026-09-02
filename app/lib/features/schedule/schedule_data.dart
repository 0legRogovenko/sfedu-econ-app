import 'lesson.dart';

/// Учебный модуль — основное измерение семестра. Ключ — диапазон дат, а не
/// имя: «2 модуль» встречается дважды в одном файле с разными датами, поэтому
/// имя ключом быть не может (см. контракт).
class Module {
  const Module({
    required this.id,
    required this.name,
    required this.dateFrom,
    required this.dateTo,
  });

  final int id;
  final String? name; // имя ключом не является
  final DateTime dateFrom;
  final DateTime dateTo;

  factory Module.fromJson(Map<String, dynamic> json) => Module(
    id: json['id'] as int,
    name: json['name'] as String?,
    dateFrom: DateTime.parse(json['date_from'] as String),
    dateTo: DateTime.parse(json['date_to'] as String),
  );
}

/// Запись календаря недель: диапазон дат → тип недели. Тип недели импортируется
/// как данные ЮФУ, клиент его НЕ вычисляет формулой (прежняя формула была
/// перевёрнута относительно реальности).
class WeekCalendarEntry {
  const WeekCalendarEntry({
    required this.dateFrom,
    required this.dateTo,
    required this.weekType,
  });

  final DateTime dateFrom;
  final DateTime dateTo;
  final WeekType weekType; // всегда upper|lower

  factory WeekCalendarEntry.fromJson(Map<String, dynamic> json) =>
      WeekCalendarEntry(
        dateFrom: DateTime.parse(json['date_from'] as String),
        dateTo: DateTime.parse(json['date_to'] as String),
        weekType: WeekType.fromValue(json['week_type'] as String),
      );
}

/// Расписание группы целиком: пары + контекст для резолвинга «дата → модуль +
/// тип недели». Всё, что нужно клиенту, чтобы по дате понять, какая пара видна.
class ScheduleData {
  const ScheduleData({
    required this.lessons,
    required this.modules,
    required this.weekCalendar,
  });

  const ScheduleData.empty()
    : lessons = const [],
      modules = const [],
      weekCalendar = const [];

  final List<Lesson> lessons;
  final List<Module> modules;
  final List<WeekCalendarEntry> weekCalendar;

  /// Разбор ответа /api/schedule (объект с тремя массивами).
  factory ScheduleData.fromJson(Map<String, dynamic> json) => ScheduleData(
    lessons: (json['lessons'] as List<dynamic>? ?? [])
        .map((e) => Lesson.fromJson(e as Map<String, dynamic>))
        .toList(),
    modules: (json['modules'] as List<dynamic>? ?? [])
        .map((e) => Module.fromJson(e as Map<String, dynamic>))
        .toList(),
    weekCalendar: (json['week_calendar'] as List<dynamic>? ?? [])
        .map((e) => WeekCalendarEntry.fromJson(e as Map<String, dynamic>))
        .toList(),
  );
}
