import 'lesson.dart';
import 'schedule_data.dart';

// Прежняя формула «чётность ISO-недели → тип недели» УДАЛЕНА: она давала
// результат, обратный реальному календарю ЮФУ (0 совпадений из 10). Тип недели
// и активный модуль теперь берутся из данных сервера (week_calendar, valid_from/
// valid_to) по правилу резолвинга из контракта — никаких формул чётности.

bool _inRange(DateTime date, DateTime from, DateTime to) =>
    !date.isBefore(from) && !date.isAfter(to);

bool _sameDay(DateTime one, DateTime other) =>
    one.year == other.year && one.month == other.month && one.day == other.day;

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
bool lessonVisibleOn(
  Lesson lesson,
  DateTime date,
  WeekType? weekType, {
  int? subgroup,
}) {
  if (lesson.weekday != date.weekday - 1) return false;
  if (lesson.validFrom != null && date.isBefore(lesson.validFrom!)) {
    return false;
  }
  if (lesson.validTo != null && date.isAfter(lesson.validTo!)) return false;
  if (lesson.specificDates.isNotEmpty &&
      !lesson.specificDates.any((value) => _sameDay(value, date))) {
    return false;
  }
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

/// Известный данным учебный период: объединённый охват календаря недель и
/// модулей — (первый день, последний день). null, если ни того ни другого нет
/// (демо/ручные данные).
(DateTime, DateTime)? _dataCoverage(ScheduleData data) {
  final ranges = <(DateTime, DateTime)>[
    for (final w in data.weekCalendar) (w.dateFrom, w.dateTo),
    for (final m in data.modules) (m.dateFrom, m.dateTo),
  ];
  if (ranges.isEmpty) return null;
  var (from, to) = ranges.first;
  for (final (f, t) in ranges.skip(1)) {
    if (f.isBefore(from)) from = f;
    if (t.isAfter(to)) to = t;
  }
  return (from, to);
}

/// Пары на конкретную дату: фильтр по правилу резолвинга,
/// сортировка по номеру пары и подгруппе.
List<Lesson> lessonsForDay(
  ScheduleData data,
  DateTime date, {
  int? subgroup,
  String? muamSubject,
}) {
  final weekType = weekTypeForDate(data.weekCalendar, date);
  // Пара без окна действия (validFrom и validTo == null — файл без модулей)
  // подходит под любой matching-день, в том числе летом и в каникулы. Бьём по
  // известному данным учебному периоду (календарь ∪ модули): вне его такие
  // пары не показываем. Ни календаря, ни модулей нет — фильтр не применяем
  // (демо/ручные пары).
  final coverage = _dataCoverage(data);
  final visible = data.lessons.where((l) {
    if (!lessonVisibleOn(l, date, weekType, subgroup: subgroup)) return false;
    if (coverage != null && l.validFrom == null && l.validTo == null) {
      final day = DateTime(date.year, date.month, date.day);
      if (day.isBefore(coverage.$1) || day.isAfter(coverage.$2)) return false;
    }
    return true;
  }).toList();

  // ЮФУ перечисляет в одной ячейке все варианты курса по выбору МУАМ.
  // Это один временной слот, а не несколько обязательных пар: до выбора
  // показываем один общий блок, после выбора — выбранный вариант.
  final result = <Lesson>[];
  final muamSlots = <String, List<Lesson>>{};
  for (final lesson in visible) {
    if (scheduleSubjectLabel(lesson.subject) != 'МУАМ') {
      result.add(lesson);
      continue;
    }
    final key =
        '${lesson.weekday}|${lesson.pairNumber}|${lesson.startsAt}|'
        '${lesson.endsAt}|${lesson.subgroup}';
    muamSlots.putIfAbsent(key, () => []).add(lesson);
  }
  for (final candidates in muamSlots.values) {
    result.add(
      candidates.firstWhere(
        (lesson) => lesson.subject == muamSubject,
        orElse: () => candidates.first,
      ),
    );
  }

  result.sort((a, b) {
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
