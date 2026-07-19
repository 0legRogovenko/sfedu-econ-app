import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sfedu_econ/core/clock.dart';
import 'package:sfedu_econ/features/onboarding/group_repository.dart';
import 'package:sfedu_econ/features/schedule/lesson.dart';
import 'package:sfedu_econ/features/schedule/schedule_data.dart';
import 'package:sfedu_econ/features/schedule/schedule_providers.dart';
import 'package:sfedu_econ/features/schedule/schedule_repository.dart';
import 'package:sfedu_econ/features/teachers/teacher.dart';
import 'package:sfedu_econ/features/teachers/teacher_schedule_screen.dart';
import 'package:sfedu_econ/features/teachers/teacher_search_screen.dart';
import 'package:sfedu_econ/features/teachers/teachers_providers.dart';

// 13.07.2026 — понедельник, 09:30.
final _now = DateTime(2026, 7, 13, 9, 30);

const _teacher = Teacher(id: 7, fullName: 'Ласкова Т.С.');

const _groups = [
  Group(
    id: 3,
    course: 2,
    number: '2.1',
    program: null,
    level: EducationLevel.bachelor,
    subgroupCount: 2,
  ),
  Group(
    id: 4,
    course: 2,
    number: '2.2',
    program: null,
    level: EducationLevel.bachelor,
    subgroupCount: 2,
  ),
];

// У преподавателя в один день пары РАЗНЫХ групп — ради этого карточка и
// подписывается группой, а не его собственным именем.
final _data = ScheduleData(
  lessons: const [
    Lesson(
      id: 1,
      groupId: 3,
      weekday: 0,
      pairNumber: 1,
      startsAt: '09:00:00',
      endsAt: '10:35:00',
      subject: 'Макроэкономика',
      room: '220',
      weekType: null,
      subgroup: 0,
      teacherName: 'Ласкова Т.С.',
    ),
    Lesson(
      id: 2,
      groupId: 4,
      weekday: 0,
      pairNumber: 2,
      startsAt: '10:50:00',
      endsAt: '12:25:00',
      subject: 'Микроэкономика',
      room: '221',
      weekType: null,
      subgroup: 0,
      teacherName: 'Ласкова Т.С.',
    ),
  ],
  modules: const [],
  weekCalendar: const [],
);

class _FakeTeacherSync extends TeacherSyncNotifier {
  _FakeTeacherSync(super.teacherId);

  @override
  Future<void> sync() async {}
}

/// Синк уже упал, кэша нет — для честной плашки «нужна сеть».
class _FirstLaunchFailedSync extends TeacherSyncNotifier {
  _FirstLaunchFailedSync(super.teacherId);

  @override
  SyncStatus build() =>
      const SyncStatus(lastResult: SyncResult.failed, syncedAt: null);

  @override
  Future<void> sync() async {}
}

ProviderContainer _container({
  ScheduleData? data,
  List<Teacher>? teachers,
  Object? teachersError,
  TeacherSyncNotifier Function()? sync,
}) =>
    ProviderContainer(
      overrides: [
        clockProvider.overrideWithValue(() => _now),
        groupsProvider.overrideWith((ref) async => _groups),
        teachersProvider.overrideWith((ref) async {
          if (teachersError != null) throw teachersError;
          return teachers ?? const [_teacher];
        }),
        teacherScheduleProvider
            .overrideWith((ref, teacherId) => Stream.value(data ?? _data)),
        // Подменяем ЭЛЕМЕНТ семейства (id 7), а не семейство целиком:
        // override семейства не получает аргумент, и нотифаер пришлось бы
        // строить с чужим id.
        teacherSyncProvider(_teacher.id)
            .overrideWith(sync ?? () => _FakeTeacherSync(_teacher.id)),
      ],
    );

Future<void> _pump(WidgetTester tester, ProviderContainer container,
    Widget screen) async {
  await tester.pumpWidget(UncontrolledProviderScope(
    container: container,
    child: MaterialApp(home: screen),
  ));
  await tester.pumpAndSettle();
}

void main() {
  group('поиск преподавателя', () {
    testWidgets('показывает весь список без запроса', (tester) async {
      final container = _container(teachers: const [
        _teacher,
        Teacher(id: 8, fullName: 'Галич Ж.В.'),
      ]);
      addTearDown(container.dispose);
      await _pump(tester, container, const TeacherSearchScreen());

      expect(find.text('Ласкова Т.С.'), findsOneWidget);
      expect(find.text('Галич Ж.В.'), findsOneWidget);
    });

    testWidgets('ввод фильтрует список', (tester) async {
      final container = _container(teachers: const [
        _teacher,
        Teacher(id: 8, fullName: 'Галич Ж.В.'),
      ]);
      addTearDown(container.dispose);
      await _pump(tester, container, const TeacherSearchScreen());

      await tester.enterText(find.byType(TextField), 'галич');
      await tester.pumpAndSettle();

      expect(find.text('Галич Ж.В.'), findsOneWidget);
      expect(find.text('Ласкова Т.С.'), findsNothing);
    });

    testWidgets('офлайн: честно про сеть, а не «никого не нашлось»',
        (tester) async {
      // Списка преподавателей в кэше нет, поэтому пустой экран здесь означал
      // бы «таких нет» — неправда, которую студент не сможет отличить.
      final container = _container(teachersError: Exception('нет сети'));
      addTearDown(container.dispose);
      await _pump(tester, container, const TeacherSearchScreen());

      expect(find.textContaining('Нужна сеть'), findsOneWidget);
      expect(find.text('Никого не нашлось'), findsNothing);
    });
  });

  group('расписание преподавателя', () {
    testWidgets('карточка подписана ГРУППОЙ, а не преподавателем',
        (tester) async {
      final container = _container();
      addTearDown(container.dispose);
      await _pump(
          tester, container, const TeacherScheduleScreen(teacher: _teacher));

      expect(find.text('ауд. 220 · 2.1'), findsOneWidget);
      expect(find.text('ауд. 221 · 2.2'), findsOneWidget);
      // Собственное имя в каждой карточке бесполезно — оно уже в заголовке.
      expect(find.textContaining('220 · Ласкова'), findsNothing);
    });

    testWidgets('заголовок — ФИО преподавателя', (tester) async {
      final container = _container();
      addTearDown(container.dispose);
      await _pump(
          tester, container, const TeacherScheduleScreen(teacher: _teacher));

      expect(find.widgetWithText(AppBar, 'Ласкова Т.С.'), findsOneWidget);
    });

    testWidgets('пустой кэш после неудачного синка — «нужна сеть»',
        (tester) async {
      final container = _container(
        data: const ScheduleData.empty(),
        sync: () => _FirstLaunchFailedSync(_teacher.id),
      );
      addTearDown(container.dispose);
      await _pump(
          tester, container, const TeacherScheduleScreen(teacher: _teacher));

      expect(find.textContaining('Нет данных'), findsOneWidget);
      expect(find.text('Пар нет — отдыхаем'), findsNothing);
    });
  });
}
