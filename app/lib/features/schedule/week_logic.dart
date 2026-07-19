import 'lesson.dart';
import 'schedule_data.dart';

// Прежняя формула «чётность ISO-недели → тип недели» УДАЛЕНА: она давала
// результат, обратный реальному календарю ЮФУ (0 совпадений из 10). Тип недели
// и активный модуль теперь берутся из данных сервера (week_calendar, valid_from/
// valid_to) по правилу резолвинга из контракта — никаких формул чётности.

bool _inRange(DateTime date, DateTime from, DateTime to) =>
    !date.isBefore(from) && !date.isAfter(to);

/// Тип недели для даты по календарю. null — дата вне всех диапазонов
/// (тип недели неизвестен → показываем только пары без чередования).
WeekType? weekTypeForDate(List<WeekCalendarEntry> calendar, DateTime date) {
  for (final entry in calendar) {
    if (_inRange(date, entry.dateFrom, entry.dateTo)) return entry.weekType;
  }
  return null;
}

/// Активный модуль для даты, либо null (демо/ручные пары без модулей).
Module? activeModule(List<Module> modules, DateTime date) {
  for (final module in modules) {
    if (_inRange(date, module.dateFrom, module.dateTo)) return module;
  }
  return null;
}

/// Видна ли пара в дату по ПРАВИЛУ РЕЗОЛВИНГА:
/// weekday совпадает И (окно valid_from..valid_to охватывает дату)
/// И (тип недели пары null ИЛИ равен типу недели календаря на эту дату).
///
/// [subgroup] — пользовательский фильтр «моя подгруппа» (null = показывать
/// все). Он НЕ часть правила резолвинга, а настройка поверх него.
bool lessonVisibleOn(Lesson lesson, DateTime date, WeekType? weekType,
    {int? subgroup}) {
  if (lesson.weekday != date.weekday - 1) return false;
  if (lesson.validFrom != null && date.isBefore(lesson.validFrom!)) return false;
  if (lesson.validTo != null && date.isAfter(lesson.validTo!)) return false;
  // Пара с чередованием видна только на своей неделе. Если тип недели на дату
  // неизвестен (null), такая пара не показывается — только пары без чередования.
  if (lesson.weekType != null && lesson.weekType != weekType) return false;
  // subgroup == 0 — пара всей группы: видна при любом фильтре, иначе студент
  // с фильтром потерял бы все общие лекции.
  if (subgroup != null && lesson.subgroup != 0 && lesson.subgroup != subgroup) {
    return false;
  }
  return true;
}

/// Пары на конкретную дату: фильтр по правилу резолвинга,
/// сортировка по номеру пары и подгруппе.
List<Lesson> lessonsForDay(ScheduleData data, DateTime date, {int? subgroup}) {
  final weekType = weekTypeForDate(data.weekCalendar, date);
  final result = data.lessons
      .where((l) => lessonVisibleOn(l, date, weekType, subgroup: subgroup))
      .toList()
    ..sort((a, b) {
      final byPair = a.pairNumber.compareTo(b.pairNumber);
      return byPair != 0 ? byPair : a.subgroup.compareTo(b.subgroup);
    });
  return result;
}

int _minutes(String hhmmss) {
  final parts = hhmmss.split(':');
  return int.parse(parts[0]) * 60 + int.parse(parts[1]);
}

/// Идёт ли пара прямо сейчас (правило резолвинга на сегодня + интервал времени).
/// [weekType] — тип недели сегодняшней даты (резолвится вызывающим по календарю).
bool isLessonNow(Lesson lesson, WeekType? weekType, DateTime now) {
  final today = DateTime(now.year, now.month, now.day);
  if (!lessonVisibleOn(lesson, today, weekType)) return false;
  final nowMinutes = now.hour * 60 + now.minute;
  // Верхняя граница исключена: в минуту стыка смежных пар
  // «Сейчас» не должны быть обе.
  return nowMinutes >= _minutes(lesson.startsAt) &&
      nowMinutes < _minutes(lesson.endsAt);
}
