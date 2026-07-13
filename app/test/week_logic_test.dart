import 'package:flutter_test/flutter_test.dart';
import 'package:sfedu_econ/features/schedule/lesson.dart';
import 'package:sfedu_econ/features/schedule/week_logic.dart';

Lesson _lesson({
  int id = 1,
  int weekday = 0,
  int pairNumber = 1,
  String startsAt = '09:00:00',
  String endsAt = '10:35:00',
  WeekType weekType = WeekType.both,
  int subgroup = 0,
}) =>
    Lesson(
      id: id,
      groupId: 3,
      weekday: weekday,
      pairNumber: pairNumber,
      startsAt: startsAt,
      endsAt: endsAt,
      subject: 'Макроэкономика',
      room: '220',
      weekType: weekType,
      subgroup: subgroup,
      teacherName: 'Иванова Е. П.',
    );

void main() {
  group('isoWeekNumber', () {
    test('1 января 2026 (четверг) — неделя 1', () {
      expect(isoWeekNumber(DateTime(2026, 1, 1)), 1);
    });
    test('13 июля 2026 (понедельник) — неделя 29', () {
      expect(isoWeekNumber(DateTime(2026, 7, 13)), 29);
    });
    test('28 декабря 2026 — неделя 53', () {
      expect(isoWeekNumber(DateTime(2026, 12, 28)), 53);
    });
  });

  group('weekTypeForDate', () {
    test('нечётная ISO-неделя — числитель', () {
      expect(weekTypeForDate(DateTime(2026, 7, 13)), WeekType.numerator); // 29
    });
    test('чётная ISO-неделя — знаменатель', () {
      expect(weekTypeForDate(DateTime(2026, 7, 20)), WeekType.denominator); // 30
    });
  });

  group('lessonsForDay', () {
    final lessons = [
      _lesson(id: 1, weekday: 0, pairNumber: 2),
      _lesson(id: 2, weekday: 0, pairNumber: 1, weekType: WeekType.numerator),
      _lesson(id: 3, weekday: 0, pairNumber: 1, weekType: WeekType.denominator),
      _lesson(id: 4, weekday: 1, pairNumber: 1),
    ];

    test('фильтрует по дню и типу недели, сортирует по номеру пары', () {
      // 13.07.2026 — понедельник (weekday 0), неделя 29 — числитель
      final day = lessonsForDay(lessons, DateTime(2026, 7, 13));
      expect(day.map((l) => l.id), [2, 1]); // знаменательная (id 3) исключена
    });

    test('на знаменательной неделе — другая пара в том же слоте', () {
      final day = lessonsForDay(lessons, DateTime(2026, 7, 20));
      expect(day.map((l) => l.id), [3, 1]);
    });
  });

  group('isLessonNow', () {
    final lesson = _lesson(); // пн, 09:00–10:35, обе недели

    test('во время пары — true', () {
      expect(isLessonNow(lesson, DateTime(2026, 7, 13, 9, 30)), isTrue);
    });
    test('до начала — false', () {
      expect(isLessonNow(lesson, DateTime(2026, 7, 13, 8, 59)), isFalse);
    });
    test('после конца — false', () {
      expect(isLessonNow(lesson, DateTime(2026, 7, 13, 10, 36)), isFalse);
    });
    test('в другой день — false', () {
      expect(isLessonNow(lesson, DateTime(2026, 7, 14, 9, 30)), isFalse);
    });
    test('пара числителя на знаменательной неделе — false', () {
      final numeratorLesson = _lesson(weekType: WeekType.numerator);
      // 20.07.2026 — понедельник, неделя 30 (знаменатель)
      expect(isLessonNow(numeratorLesson, DateTime(2026, 7, 20, 9, 30)), isFalse);
    });
  });

  group('Lesson.fromJson', () {
    test('парсит ответ API с вложенным преподавателем', () {
      final lesson = Lesson.fromJson({
        'id': 7,
        'group_id': 3,
        'weekday': 2,
        'pair_number': 3,
        'starts_at': '13:10:00',
        'ends_at': '14:45:00',
        'subject': 'Микроэкономика',
        'room': '221',
        'week_type': 'numerator',
        'subgroup': 0,
        'teacher': {'id': 1, 'full_name': 'Иванова Елена Петровна'},
      });
      expect(lesson.subject, 'Микроэкономика');
      expect(lesson.weekType, WeekType.numerator);
      expect(lesson.teacherName, 'Иванова Елена Петровна');
    });

    test('teacher: null — teacherName null', () {
      final lesson = Lesson.fromJson({
        'id': 8,
        'group_id': 3,
        'weekday': 2,
        'pair_number': 4,
        'starts_at': '15:00:00',
        'ends_at': '16:35:00',
        'subject': 'Физкультура',
        'room': null,
        'week_type': 'both',
        'subgroup': 0,
        'teacher': null,
      });
      expect(lesson.teacherName, isNull);
    });
  });
}
