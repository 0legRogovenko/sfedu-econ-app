import 'lesson.dart';

/// Номер недели по ISO 8601 (неделя четверга).
int isoWeekNumber(DateTime date) {
  final day = DateTime(date.year, date.month, date.day);
  final thursday = day.add(Duration(days: 4 - day.weekday));
  final firstDayOfYear = DateTime(thursday.year, 1, 1);
  return thursday.difference(firstDayOfYear).inDays ~/ 7 + 1;
}

/// Допущение MVP: числитель — нечётная ISO-неделя.
/// Единственная точка правки, когда сверимся с реальным расписанием.
WeekType weekTypeForDate(DateTime date) =>
    isoWeekNumber(date).isOdd ? WeekType.numerator : WeekType.denominator;

/// Пары на конкретную дату: фильтр по дню недели и типу недели,
/// сортировка по номеру пары и подгруппе.
List<Lesson> lessonsForDay(List<Lesson> lessons, DateTime date) {
  final weekday = date.weekday - 1; // DateTime: 1=пн … модель: 0=пн
  final weekType = weekTypeForDate(date);
  final result = lessons
      .where((l) =>
          l.weekday == weekday &&
          (l.weekType == WeekType.both || l.weekType == weekType))
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

/// Идёт ли пара прямо сейчас (день, тип недели и интервал времени).
bool isLessonNow(Lesson lesson, DateTime now) {
  if (lesson.weekday != now.weekday - 1) return false;
  final weekType = weekTypeForDate(now);
  if (lesson.weekType != WeekType.both && lesson.weekType != weekType) {
    return false;
  }
  final nowMinutes = now.hour * 60 + now.minute;
  return nowMinutes >= _minutes(lesson.startsAt) &&
      nowMinutes <= _minutes(lesson.endsAt);
}
