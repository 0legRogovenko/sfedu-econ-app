import 'schedule_data.dart';

/// Семестр — кластер дат расписания между каникулами. В данных ЮФУ у группы
/// два семестра, каждый своим документом: осенний (сентябрь–январь) и весенний
/// (февраль–июнь), разрыв на зимние каникулы ~4 недели. Границы определяем ПО
/// ДАННЫМ (диапазоны модулей и календаря недель), а не по календарным месяцам:
/// даты семестров год от года плавают.
class Semester {
  const Semester({required this.from, required this.to});

  final DateTime from;
  final DateTime to;

  /// Подпись переключателя. По месяцу начала: сентябрь–январь — осенний,
  /// февраль–август — весенний.
  String get label =>
      (from.month >= 8 || from.month == 1) ? 'Осенний' : 'Весенний';

  /// Устойчивый ключ семестра, общий для расписаний студента и преподавателя:
  /// год начала + сезон. Год отличает соседние одноимённые семестры (два осенних
  /// разных учебных лет, если в данных накопилось больше года), а сезон —
  /// осенний от весеннего. По одной лишь метке нельзя: два «Осенний» дали бы
  /// коллизию. Год начала общий у группы и преподавателя (оба стартуют в тот же
  /// сентябрь/февраль), поэтому ключ совпадает на обоих экранах.
  String get seasonKey => '${from.year}-$label';

  /// Понедельник первой недели семестра — куда прыгает расписание при выборе
  /// не текущего семестра.
  DateTime get firstMonday {
    final offset = (from.weekday - DateTime.monday) % 7;
    final monday = from.subtract(Duration(days: offset));
    return DateTime(monday.year, monday.month, monday.day);
  }

  bool contains(DateTime date) {
    final day = DateTime(date.year, date.month, date.day);
    return !day.isBefore(from) && !day.isAfter(to);
  }

  @override
  bool operator ==(Object other) =>
      other is Semester && other.from == from && other.to == to;

  @override
  int get hashCode => Object.hash(from, to);
}

// Разрыв больше трёх недель считаем каникулами (зимние — ~4 недели). Границы
// модулей внутри семестра идут стык в стык, поэтому не расщепляются.
const _gapDays = 21;

/// Семестры из расписания, по возрастанию даты. Пусто — если дат нет вовсе
/// (демо/ручные пары без модулей и календаря).
List<Semester> detectSemesters(ScheduleData data) {
  final ranges = <(DateTime, DateTime)>[
    for (final m in data.modules) (m.dateFrom, m.dateTo),
    for (final w in data.weekCalendar) (w.dateFrom, w.dateTo),
  ]..sort((a, b) => a.$1.compareTo(b.$1));

  if (ranges.isEmpty) return const [];

  final semesters = <Semester>[];
  var from = ranges.first.$1;
  var to = ranges.first.$2;
  for (final (start, end) in ranges.skip(1)) {
    if (start.isAfter(to.add(const Duration(days: _gapDays)))) {
      // разрыв больше каникул — закрываем семестр, начинаем новый
      semesters.add(Semester(from: from, to: to));
      from = start;
      to = end;
    } else if (end.isAfter(to)) {
      to = end; // диапазоны перекрываются/примыкают — расширяем
    }
  }
  semesters.add(Semester(from: from, to: to));
  return semesters;
}

/// Семестр по умолчанию для даты: тот, что её содержит; иначе ближайший
/// предстоящий, а если все позади — последний. null, если семестров нет.
Semester? currentSemester(List<Semester> semesters, DateTime now) {
  if (semesters.isEmpty) return null;
  for (final s in semesters) {
    if (s.contains(now)) return s;
  }
  // В каникулах или вне года: ближайший, что ещё впереди…
  for (final s in semesters) {
    if (s.from.isAfter(now)) return s;
  }
  // …а если весь год позади — последний.
  return semesters.last;
}

/// Выбранный семестр: по [seasonKey] (год + сезон), общему для расписаний
/// студента и преподавателя, — иначе текущий по дате. Ключ, а не голая метка:
/// два одноимённых семестра (осень двух лет) по метке дали бы коллизию —
/// выбрался бы первый, а второй стал бы недоступен.
Semester? resolveSemester(
  List<Semester> semesters,
  String? chosenKey,
  DateTime now,
) {
  if (chosenKey != null) {
    for (final s in semesters) {
      if (s.seasonKey == chosenKey) return s;
    }
  }
  return currentSemester(semesters, now);
}

/// Понедельник текущей недели. Воскресенье: показываем следующую неделю —
/// студент планирует предстоящие пары.
DateTime currentWeekMonday(DateTime now) {
  final isSunday = now.weekday == DateTime.sunday;
  final monday = now.subtract(Duration(days: now.weekday - 1));
  return DateTime(
    monday.year,
    monday.month,
    monday.day,
  ).add(Duration(days: isSunday ? 7 : 0));
}

/// Неделя, с которой открывается семестр: текущий — на сегодняшней неделе,
/// не текущий — на своей первой.
DateTime mondayForSemester(Semester? semester, DateTime now) {
  if (semester == null) return currentWeekMonday(now);
  return semester.contains(now) ? currentWeekMonday(now) : semester.firstMonday;
}
