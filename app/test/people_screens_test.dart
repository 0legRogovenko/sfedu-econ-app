import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sfedu_econ/core/clock.dart';
import 'package:sfedu_econ/features/onboarding/group_repository.dart';
import 'package:sfedu_econ/features/people/people_providers.dart';
import 'package:sfedu_econ/features/people/person.dart';
import 'package:sfedu_econ/features/exams/exam_event.dart';
import 'package:sfedu_econ/features/people/person_schedule_screen.dart';
import 'package:sfedu_econ/features/people/person_screen.dart';
import 'package:sfedu_econ/features/people/people_search_screen.dart';
import 'package:sfedu_econ/features/schedule/lesson.dart';
import 'package:sfedu_econ/features/schedule/schedule_data.dart';
import 'package:sfedu_econ/features/schedule/schedule_providers.dart';

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
  examCount: 0,
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

// Год с двумя семестрами у преподавателя: осень (верхняя неделя) и весна
// (нижняя неделя). Пара «Матанализ» — на ВЕРХНЕЙ неделе, поэтому видна только
// осенью. Так можно проверить, что расписание преподавателя следует за выбором
// семестра, а не всегда показывает текущую неделю.
final _yearData = ScheduleData(
  lessons: const [
    Lesson(
      id: 1,
      groupId: 3,
      weekday: 0, // понедельник
      pairNumber: 1,
      startsAt: '09:00:00',
      endsAt: '10:35:00',
      subject: 'Матанализ',
      room: '220',
      weekType: WeekType.upper,
      subgroup: 0,
      teacherName: 'Груданова И.Ю.',
    ),
  ],
  modules: [
    Module(
        id: 1,
        name: 'I модуль',
        dateFrom: DateTime(2025, 9, 1),
        dateTo: DateTime(2026, 1, 11)),
    Module(
        id: 2,
        name: 'I модуль',
        dateFrom: DateTime(2026, 2, 9),
        dateTo: DateTime(2026, 6, 22)),
  ],
  weekCalendar: [
    WeekCalendarEntry(
        dateFrom: DateTime(2025, 9, 1),
        dateTo: DateTime(2025, 9, 7),
        weekType: WeekType.upper), // осень, первая неделя — верхняя
    WeekCalendarEntry(
        dateFrom: DateTime(2026, 2, 9),
        dateTo: DateTime(2026, 2, 15),
        weekType: WeekType.lower), // весна, первая неделя — нижняя
  ],
);

ProviderContainer _container({ScheduleData? data, Object? error, DateTime? now}) =>
    ProviderContainer(overrides: [
      clockProvider.overrideWithValue(() => now ?? _now),
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

    testWidgets('в каникулы видна плашка межсезонья', (tester) async {
      // _now — июль: семестры в данных есть, но дата вне всех — экран
      // преподавателя, как и студенческий, явно говорит про каникулы.
      final c = _container(data: _yearData);
      addTearDown(c.dispose);
      await _pump(tester, c, const PersonScheduleScreen(person: _person));

      expect(find.textContaining('каникулы'), findsOneWidget);
    });

    testWidgets('в шапке НЕТ типа недели (верхняя/нижняя)', (tester) async {
      // Бейдж «верхняя/нижняя» убран у преподавателя, как и у студента: он был
      // справочным, а пары и так отфильтрованы по типу недели.
      final c = _container(data: _yearData);
      addTearDown(c.dispose);
      await _pump(tester, c, const PersonScheduleScreen(person: _person));

      expect(find.textContaining('верхняя'), findsNothing);
      expect(find.textContaining('нижняя'), findsNothing);
    });

    testWidgets('переключатель семестра показывает выбор студента',
        (tester) async {
      // Общий провайдер: студент выбрал осенний — расписание преподавателя
      // открывается на нём же, а не на текущей (по дате — весенней) неделе.
      final c = _container(data: _yearData);
      addTearDown(c.dispose);
      c.read(viewedSemesterProvider.notifier).select('2025-Осенний');
      await _pump(tester, c, const PersonScheduleScreen(person: _person));

      expect(find.byTooltip('Выбор семестра'), findsOneWidget);
      expect(find.widgetWithText(AppBar, 'Осенний'), findsOneWidget);
    });

    testWidgets('осенний выбор — видна верхненедельная пара', (tester) async {
      // Осень: первая неделя верхняя, пара на верхней неделе — видна, хотя по
      // дате (июль) текущий семестр весенний.
      final c = _container(data: _yearData);
      addTearDown(c.dispose);
      c.read(viewedSemesterProvider.notifier).select('2025-Осенний');
      await _pump(tester, c, const PersonScheduleScreen(person: _person));
      expect(find.text('Матанализ'), findsOneWidget);
    });

    testWidgets('весенний выбор — той же верхненедельной пары нет',
        (tester) async {
      // Весна: первая неделя нижняя — верхненедельной пары там не должно быть.
      final c = _container(data: _yearData);
      addTearDown(c.dispose);
      c.read(viewedSemesterProvider.notifier).select('2026-Весенний');
      await _pump(tester, c, const PersonScheduleScreen(person: _person));
      expect(find.text('Матанализ'), findsNothing);
      expect(find.text('Пар нет — отдыхаем'), findsOneWidget);
    });

    testWidgets('не текущий семестр открывается с понедельника, не с сегодня',
        (tester) async {
      // Сегодня среда (2026-07-15), выбран осенний (не текущий). Пара стоит в
      // понедельник — она видна, значит экран открылся на понедельнике первой
      // недели, а не на сегодняшней среде.
      final c = _container(data: _yearData, now: DateTime(2026, 7, 15, 9, 30));
      addTearDown(c.dispose);
      c.read(viewedSemesterProvider.notifier).select('2025-Осенний');
      await _pump(tester, c, const PersonScheduleScreen(person: _person));
      expect(find.text('Матанализ'), findsOneWidget);
    });

    testWidgets('переключение семестра у преподавателя не трогает выбор студента',
        (tester) async {
      // Студент ничего не выбирал (провайдер null). На экране преподавателя
      // листаем на осенний — общий провайдер должен остаться null, чтобы
      // домашнее расписание студента не переехало на чужой семестр.
      final c = _container(data: _yearData);
      addTearDown(c.dispose);
      await _pump(tester, c, const PersonScheduleScreen(person: _person));

      // По дате (июль) стартово показан весенний; переключаем на осенний.
      await tester.tap(find.byTooltip('Выбор семестра'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Осенний'));
      await tester.pumpAndSettle();

      // Локально переключилось (видна осенняя верхненедельная пара)…
      expect(find.text('Матанализ'), findsOneWidget);
      // …но общий выбор студента не тронут.
      expect(c.read(viewedSemesterProvider), isNull);
    });
  });

  group('карточка человека', () {
    testWidgets('показывает экзамены преподавателя', (tester) async {
      const examPerson = Person(
        id: 'p9',
        shortName: 'Ласкова Т.С.',
        fullName: 'Ласкова Татьяна Сергеевна',
        sections: [],
        roles: [],
        email: null,
        hasSchedule: true,
        lessonCount: 0,
        examCount: 1,
      );
      final c = ProviderContainer(overrides: [
        personExamsProvider.overrideWith((ref, id) async => [
              ExamEvent(
                id: 1,
                groupId: 3,
                subject: 'Экономика',
                teacher: 'Ласкова Т.С.',
                consultationAt: null,
                examAt: DateTime(2026, 1, 15, 10, 0),
                room: '220',
                kind: null,
              ),
            ]),
      ]);
      addTearDown(c.dispose);
      await _pump(tester, c, const PersonScreen(person: examPerson));

      expect(find.text('Экзамены'), findsOneWidget);
      expect(find.text('Экономика'), findsOneWidget);
    });

    testWidgets('без экзаменов секции нет', (tester) async {
      final c = ProviderContainer();
      addTearDown(c.dispose);
      await _pump(tester, c, const PersonScreen(person: _person));

      expect(find.text('Экзамены'), findsNothing);
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
          examCount: 0,
        ),
      ]);
      addTearDown(c.dispose);
      await _pump(tester, c, const PeopleSearchScreen());

      expect(find.text('Груданова И.Ю.'), findsOneWidget);
      expect(find.text('Методистов М.М.'), findsNothing);
    });
  });
}
