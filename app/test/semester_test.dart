import 'package:flutter_test/flutter_test.dart';
import 'package:sfedu_econ/features/schedule/lesson.dart';
import 'package:sfedu_econ/features/schedule/schedule_data.dart';
import 'package:sfedu_econ/features/schedule/semester.dart';

// Реальная структура из данных ЮФУ (группа 1.5): осень стык-в-стык из трёх
// модулей, разрыв на зимние каникулы, весна из двух модулей.
ScheduleData _yearData() => ScheduleData(
      lessons: const [],
      modules: [
        Module(id: 1, name: 'I модуль', dateFrom: DateTime(2025, 9, 1), dateTo: DateTime(2025, 11, 2)),
        Module(id: 2, name: '2 модуль', dateFrom: DateTime(2025, 11, 3), dateTo: DateTime(2025, 11, 23)),
        Module(id: 3, name: null, dateFrom: DateTime(2025, 11, 24), dateTo: DateTime(2026, 1, 11)),
        Module(id: 4, name: 'I модуль', dateFrom: DateTime(2026, 2, 9), dateTo: DateTime(2026, 4, 12)),
        Module(id: 5, name: 'II модуль', dateFrom: DateTime(2026, 4, 13), dateTo: DateTime(2026, 6, 22)),
      ],
      weekCalendar: const [],
    );

void main() {
  group('detectSemesters', () {
    test('год делится ровно на два семестра', () {
      final s = detectSemesters(_yearData());
      expect(s.length, 2);
    });

    test('осенний семестр — от сентября до зимних каникул', () {
      final s = detectSemesters(_yearData());
      expect(s[0].from, DateTime(2025, 9, 1));
      expect(s[0].to, DateTime(2026, 1, 11));
      expect(s[0].label, 'Осенний');
    });

    test('весенний семестр — от февраля до июня', () {
      final s = detectSemesters(_yearData());
      expect(s[1].from, DateTime(2026, 2, 9));
      expect(s[1].to, DateTime(2026, 6, 22));
      expect(s[1].label, 'Весенний');
    });

    test('стыкующиеся модули НЕ расщепляются на семестры', () {
      // Три осенних модуля идут день в день — это один семестр, а не три.
      final s = detectSemesters(_yearData());
      expect(s[0].from, DateTime(2025, 9, 1));
      expect(s[0].to, DateTime(2026, 1, 11)); // до конца третьего модуля
    });

    test('перекрытие модулей и календаря недель не плодит семестры', () {
      final data = ScheduleData(
        lessons: const [],
        modules: [
          Module(id: 1, name: '1', dateFrom: DateTime(2025, 9, 1), dateTo: DateTime(2025, 12, 28)),
        ],
        weekCalendar: [
          WeekCalendarEntry(dateFrom: DateTime(2025, 9, 1), dateTo: DateTime(2025, 9, 7), weekType: WeekType.upper),
          WeekCalendarEntry(dateFrom: DateTime(2025, 12, 22), dateTo: DateTime(2025, 12, 28), weekType: WeekType.lower),
        ],
      );
      expect(detectSemesters(data).length, 1);
    });

    test('нет дат — нет семестров', () {
      expect(detectSemesters(const ScheduleData.empty()), isEmpty);
    });

    test('firstMonday — понедельник недели начала семестра', () {
      final s = detectSemesters(_yearData());
      // 01.09.2025 — понедельник, значит он и есть firstMonday.
      expect(s[0].firstMonday, DateTime(2025, 9, 1));
      // 09.02.2026 — понедельник.
      expect(s[1].firstMonday, DateTime(2026, 2, 9));
    });

    test('firstMonday откатывается к понедельнику, если семестр начат в среду', () {
      final data = ScheduleData(
        lessons: const [],
        modules: [
          Module(id: 1, name: '1', dateFrom: DateTime(2025, 9, 3), dateTo: DateTime(2025, 12, 1)),
        ],
        weekCalendar: const [],
      );
      // 03.09.2025 — среда → понедельник 01.09.
      expect(detectSemesters(data).single.firstMonday, DateTime(2025, 9, 1));
    });
  });

  group('currentSemester', () {
    final semesters = detectSemesters(_yearData());

    test('дата внутри осеннего → осенний', () {
      expect(currentSemester(semesters, DateTime(2025, 9, 16)), semesters[0]);
    });

    test('дата внутри весеннего → весенний', () {
      expect(currentSemester(semesters, DateTime(2026, 3, 10)), semesters[1]);
    });

    test('зимние каникулы → ближайший предстоящий (весенний)', () {
      expect(currentSemester(semesters, DateTime(2026, 1, 25)), semesters[1]);
    });

    test('лето после года → последний (весенний)', () {
      expect(currentSemester(semesters, DateTime(2026, 8, 1)), semesters[1]);
    });

    test('до начала года → первый (осенний)', () {
      expect(currentSemester(semesters, DateTime(2025, 8, 1)), semesters[0]);
    });

    test('нет семестров → null', () {
      expect(currentSemester(const [], DateTime(2025, 9, 1)), isNull);
    });
  });
}
