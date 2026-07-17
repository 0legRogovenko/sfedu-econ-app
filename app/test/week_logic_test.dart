import 'package:flutter_test/flutter_test.dart';
import 'package:sfedu_econ/features/schedule/lesson.dart';
import 'package:sfedu_econ/features/schedule/schedule_data.dart';
import 'package:sfedu_econ/features/schedule/week_logic.dart';

Lesson _lesson({
  int id = 1,
  int weekday = 0,
  int pairNumber = 1,
  String startsAt = '09:00:00',
  String endsAt = '10:35:00',
  WeekType? weekType,
  int subgroup = 0,
  DateTime? validFrom,
  DateTime? validTo,
  int? moduleId,
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
      moduleId: moduleId,
      validFrom: validFrom,
      validTo: validTo,
    );

// Календарь: 01–07.09 верхняя, 08–14.09 нижняя. Дальше — пусто (тип неизвестен).
final _calendar = [
  WeekCalendarEntry(
    dateFrom: DateTime(2025, 9, 1),
    dateTo: DateTime(2025, 9, 7),
    weekType: WeekType.upper,
  ),
  WeekCalendarEntry(
    dateFrom: DateTime(2025, 9, 8),
    dateTo: DateTime(2025, 9, 14),
    weekType: WeekType.lower,
  ),
];

// Два модуля: 1-й 01.09–26.10, 2-й 27.10–31.12.
final _modules = [
  Module(
    id: 1,
    name: '1 модуль',
    dateFrom: DateTime(2025, 9, 1),
    dateTo: DateTime(2025, 10, 26),
  ),
  Module(
    id: 2,
    name: '2 модуль',
    dateFrom: DateTime(2025, 10, 27),
    dateTo: DateTime(2025, 12, 31),
  ),
];

void main() {
  group('weekTypeForDate', () {
    test('дата в диапазоне верхней недели → upper', () {
      expect(weekTypeForDate(_calendar, DateTime(2025, 9, 1)), WeekType.upper);
    });
    test('дата в диапазоне нижней недели → lower', () {
      expect(weekTypeForDate(_calendar, DateTime(2025, 9, 8)), WeekType.lower);
    });
    test('первый день окна включительно', () {
      expect(weekTypeForDate(_calendar, DateTime(2025, 9, 7)), WeekType.upper);
    });
    test('последний день окна включительно', () {
      expect(weekTypeForDate(_calendar, DateTime(2025, 9, 14)), WeekType.lower);
    });
    test('дата вне календаря → null (тип неизвестен)', () {
      expect(weekTypeForDate(_calendar, DateTime(2025, 11, 3)), isNull);
    });
    test('пустой календарь → null', () {
      expect(weekTypeForDate(const [], DateTime(2025, 9, 1)), isNull);
    });
  });

  group('activeModule', () {
    test('дата внутри 1-го модуля', () {
      expect(activeModule(_modules, DateTime(2025, 9, 15))?.id, 1);
    });
    test('дата внутри 2-го модуля', () {
      expect(activeModule(_modules, DateTime(2025, 11, 3))?.id, 2);
    });
    test('граница модуля включительно', () {
      expect(activeModule(_modules, DateTime(2025, 10, 26))?.id, 1);
      expect(activeModule(_modules, DateTime(2025, 10, 27))?.id, 2);
    });
    test('дата вне всех модулей → null', () {
      expect(activeModule(_modules, DateTime(2026, 2, 1)), isNull);
    });
  });

  group('lessonsForDay — правило резолвинга', () {
    // Все пары в понедельник (weekday 0), в окне 1-го модуля.
    final m1From = DateTime(2025, 9, 1);
    final m1To = DateTime(2025, 10, 26);
    final lessons = [
      _lesson(id: 1, pairNumber: 1, validFrom: m1From, validTo: m1To), // каждую
      _lesson(
          id: 2,
          pairNumber: 2,
          weekType: WeekType.upper,
          validFrom: m1From,
          validTo: m1To),
      _lesson(
          id: 3,
          pairNumber: 2,
          weekType: WeekType.lower,
          validFrom: m1From,
          validTo: m1To),
      // Пара 2-го модуля.
      _lesson(
          id: 4,
          pairNumber: 1,
          validFrom: DateTime(2025, 10, 27),
          validTo: DateTime(2025, 12, 31)),
    ];
    final data = ScheduleData(
        lessons: lessons, modules: _modules, weekCalendar: _calendar);

    test('пара без чередования видна всегда, верхняя — только на верхней', () {
      // 01.09.2025 — понедельник, верхняя неделя.
      final day = lessonsForDay(data, DateTime(2025, 9, 1));
      expect(day.map((l) => l.id), [1, 2]); // нижняя (3) исключена
    });

    test('на нижней неделе — другая пара в том же слоте', () {
      // 08.09.2025 — понедельник, нижняя неделя.
      final day = lessonsForDay(data, DateTime(2025, 9, 8));
      expect(day.map((l) => l.id), [1, 3]);
    });

    test('пара 1-го модуля не видна в датах 2-го модуля', () {
      // 03.11.2025 — понедельник, 2-й модуль, тип недели неизвестен.
      final day = lessonsForDay(data, DateTime(2025, 11, 3));
      // Видна только пара 2-го модуля без чередования (id 4).
      expect(day.map((l) => l.id), [4]);
    });

    test('вне календаря видны только пары без чередования', () {
      // 03.11.2025 — тип недели null: пара верхней/нижней не показывается.
      final day = lessonsForDay(data, DateTime(2025, 11, 3));
      expect(day.every((l) => l.weekType == null), isTrue);
    });

    test('пустое окно (validFrom/validTo null) — весь семестр', () {
      final always = ScheduleData(
        lessons: [_lesson(id: 9, pairNumber: 1)],
        modules: _modules,
        weekCalendar: _calendar,
      );
      expect(lessonsForDay(always, DateTime(2025, 9, 1)).map((l) => l.id), [9]);
      expect(lessonsForDay(always, DateTime(2026, 3, 2)).map((l) => l.id), [9]);
    });
  });

  group('isLessonNow', () {
    final lesson = _lesson(); // пн, 09:00–10:35, каждую неделю

    test('во время пары — true', () {
      expect(isLessonNow(lesson, WeekType.upper, DateTime(2025, 9, 1, 9, 30)),
          isTrue);
    });
    test('до начала — false', () {
      expect(isLessonNow(lesson, WeekType.upper, DateTime(2025, 9, 1, 8, 59)),
          isFalse);
    });
    test('после конца — false', () {
      expect(isLessonNow(lesson, WeekType.upper, DateTime(2025, 9, 1, 10, 36)),
          isFalse);
    });
    test('ровно в конце — уже не идёт', () {
      expect(isLessonNow(lesson, WeekType.upper, DateTime(2025, 9, 1, 10, 35)),
          isFalse);
    });
    test('в другой день — false', () {
      expect(isLessonNow(lesson, WeekType.upper, DateTime(2025, 9, 2, 9, 30)),
          isFalse);
    });
    test('пара верхней на нижней неделе — false', () {
      final upper = _lesson(weekType: WeekType.upper);
      expect(isLessonNow(upper, WeekType.lower, DateTime(2025, 9, 8, 9, 30)),
          isFalse);
    });
  });

  group('Lesson.fromJson', () {
    test('парсит новые поля: week_type null, module_id, окно дат', () {
      final lesson = Lesson.fromJson({
        'id': 7,
        'group_id': 3,
        'weekday': 2,
        'pair_number': 3,
        'starts_at': '13:10:00',
        'ends_at': '14:45:00',
        'subject': 'Микроэкономика',
        'room': '221',
        'week_type': null,
        'subgroup': 0,
        'teacher': {'id': 1, 'full_name': 'Иванова Елена Петровна'},
        'module_id': 2,
        'valid_from': '2025-09-01',
        'valid_to': '2025-10-26',
      });
      expect(lesson.subject, 'Микроэкономика');
      expect(lesson.weekType, isNull);
      expect(lesson.teacherName, 'Иванова Елена Петровна');
      expect(lesson.moduleId, 2);
      expect(lesson.validFrom, DateTime(2025, 9, 1));
      expect(lesson.validTo, DateTime(2025, 10, 26));
    });

    test('week_type upper парсится в enum', () {
      final lesson = Lesson.fromJson({
        'id': 8,
        'group_id': 3,
        'weekday': 2,
        'pair_number': 4,
        'starts_at': '15:00:00',
        'ends_at': '16:35:00',
        'subject': 'Физкультура',
        'room': null,
        'week_type': 'upper',
        'subgroup': 0,
        'teacher': null,
        'module_id': null,
        'valid_from': null,
        'valid_to': null,
      });
      expect(lesson.weekType, WeekType.upper);
      expect(lesson.teacherName, isNull);
      expect(lesson.moduleId, isNull);
      expect(lesson.validFrom, isNull);
    });
  });

  group('ScheduleData.fromJson', () {
    test('разбирает объект с lessons, modules, week_calendar', () {
      final data = ScheduleData.fromJson({
        'lessons': [
          {
            'id': 1,
            'group_id': 5,
            'weekday': 0,
            'pair_number': 1,
            'starts_at': '08:00:00',
            'ends_at': '09:35:00',
            'subject': 'История России',
            'room': '407',
            'week_type': null,
            'subgroup': 0,
            'teacher': {'id': 3, 'full_name': 'Галич Ж.В.'},
            'module_id': 2,
            'valid_from': '2025-09-01',
            'valid_to': '2025-10-26',
          }
        ],
        'modules': [
          {
            'id': 2,
            'name': '1 модуль',
            'date_from': '2025-09-01',
            'date_to': '2025-10-26',
          }
        ],
        'week_calendar': [
          {
            'date_from': '2025-09-01',
            'date_to': '2025-09-07',
            'week_type': 'upper',
          }
        ],
      });
      expect(data.lessons.single.subject, 'История России');
      expect(data.modules.single.name, '1 модуль');
      expect(data.weekCalendar.single.weekType, WeekType.upper);
    });

    test('пустые массивы (демо/ручные пары) — валидны', () {
      final data = ScheduleData.fromJson({'lessons': [], 'modules': []});
      expect(data.lessons, isEmpty);
      expect(data.modules, isEmpty);
      expect(data.weekCalendar, isEmpty);
    });
  });
}
