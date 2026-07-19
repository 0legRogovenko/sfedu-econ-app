import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sfedu_econ/core/clock.dart';
import 'package:sfedu_econ/features/onboarding/group_repository.dart';
import 'package:sfedu_econ/features/people/people_providers.dart';
import 'package:sfedu_econ/features/people/person.dart';
import 'package:sfedu_econ/features/people/person_schedule_screen.dart';
import 'package:sfedu_econ/features/people/people_search_screen.dart';
import 'package:sfedu_econ/features/schedule/lesson.dart';
import 'package:sfedu_econ/features/schedule/schedule_data.dart';

final _now = DateTime(2026, 7, 13, 9, 30); // понедельник

const _person = Person(
  id: 'p1',
  shortName: 'Груданова И.Ю.',
  fullName: 'Груданова И.Ю.',
  sections: [],
  roles: [],
  email: null,
  hasSchedule: true,
  lessonCount: 2,
);

const _groups = [
  Group(
    id: 3,
    course: 2,
    number: '2.1',
    program: null,
    level: EducationLevel.bachelor,
    subgroupCount: 2,
  ),
];

final _data = ScheduleData(
  lessons: const [
    Lesson(
      id: 1,
      groupId: 3,
      weekday: 0,
      pairNumber: 1,
      startsAt: '09:00:00',
      endsAt: '10:35:00',
      subject: 'Матанализ',
      room: '220',
      weekType: null,
      subgroup: 0,
      teacherName: 'Груданова И.Ю.',
    ),
  ],
  modules: const [],
  weekCalendar: const [],
);

ProviderContainer _container({ScheduleData? data, Object? error}) =>
    ProviderContainer(overrides: [
      clockProvider.overrideWithValue(() => _now),
      groupsProvider.overrideWith((ref) async => _groups),
      personScheduleProvider.overrideWith((ref, id) async {
        if (error != null) throw error;
        return data ?? _data;
      }),
    ]);

Future<void> _pump(WidgetTester tester, ProviderContainer c, Widget w) async {
  await tester.pumpWidget(UncontrolledProviderScope(
    container: c,
    child: MaterialApp(home: w),
  ));
  await tester.pumpAndSettle();
}

void main() {
  group('расписание человека', () {
    testWidgets('карточка пары подписана ГРУППОЙ, а не человеком',
        (tester) async {
      final c = _container();
      addTearDown(c.dispose);
      await _pump(tester, c, const PersonScheduleScreen(person: _person));

      // Карточка подписана группой; имя человека — только в заголовке.
      expect(find.text('ауд. 220 · 2.1'), findsOneWidget);
      expect(find.widgetWithText(AppBar, 'Груданова И.Ю.'), findsOneWidget);
      expect(find.text('ауд. 220 · Груданова И.Ю.'), findsNothing);
    });

    testWidgets('офлайн — честная плашка про сеть', (tester) async {
      final c = _container(error: Exception('нет сети'));
      addTearDown(c.dispose);
      await _pump(tester, c, const PersonScheduleScreen(person: _person));

      expect(find.textContaining('Нужна сеть'), findsOneWidget);
    });
  });

  group('поиск преподавателя из расписания', () {
    ProviderContainer searchContainer(List<Person> people) =>
        ProviderContainer(overrides: [
          peopleProvider.overrideWith((ref) async => people),
        ]);

    testWidgets('показывает только людей с расписанием', (tester) async {
      final c = searchContainer(const [
        _person,
        Person(
          id: 'p2',
          shortName: 'Методистов М.М.',
          fullName: 'Методистов Максим Максимович',
          sections: ['Деканат'],
          roles: ['методист'],
          email: 'm@sfedu.ru',
          hasSchedule: false,
          lessonCount: 0,
        ),
      ]);
      addTearDown(c.dispose);
      await _pump(tester, c, const PeopleSearchScreen());

      expect(find.text('Груданова И.Ю.'), findsOneWidget);
      expect(find.text('Методистов М.М.'), findsNothing);
    });
  });
}
