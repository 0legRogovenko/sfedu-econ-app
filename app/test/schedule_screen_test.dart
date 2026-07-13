import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sfedu_econ/core/clock.dart';
import 'package:sfedu_econ/features/onboarding/selected_group.dart';
import 'package:sfedu_econ/features/schedule/lesson.dart';
import 'package:sfedu_econ/features/schedule/schedule_providers.dart';
import 'package:sfedu_econ/features/schedule/schedule_screen.dart';

// 13.07.2026 — понедельник, ISO-неделя 29 (числитель), 09:30 — идёт 1-я пара
final _now = DateTime(2026, 7, 13, 9, 30);

const _lessons = [
  Lesson(
    id: 1,
    groupId: 3,
    weekday: 0,
    pairNumber: 1,
    startsAt: '09:00:00',
    endsAt: '10:35:00',
    subject: 'Макроэкономика',
    room: '220',
    weekType: WeekType.both,
    subgroup: 0,
    teacherName: 'Иванова Е. П.',
  ),
  Lesson(
    id: 2,
    groupId: 3,
    weekday: 0,
    pairNumber: 2,
    startsAt: '10:50:00',
    endsAt: '12:25:00',
    subject: 'Эконометрика',
    room: '305',
    weekType: WeekType.numerator,
    subgroup: 0,
    teacherName: 'Петров А. С.',
  ),
  Lesson(
    id: 3,
    groupId: 3,
    weekday: 1, // вторник
    pairNumber: 1,
    startsAt: '09:00:00',
    endsAt: '10:35:00',
    subject: 'Иностранный язык',
    room: '118',
    weekType: WeekType.both,
    subgroup: 1,
    teacherName: null,
  ),
];

/// Фоновый sync в initState не должен трогать реальную drift-БД в тестах.
class _FakeSync extends SyncStatusNotifier {
  @override
  Future<void> sync() async {}
}

Widget _screen() => ProviderScope(
      overrides: [
        selectedGroupIdProvider.overrideWith(() => FakeSelectedGroupId(3)),
        lessonsProvider.overrideWith((ref) => Stream.value(_lessons)),
        clockProvider.overrideWithValue(() => _now),
        syncStatusProvider.overrideWith(_FakeSync.new),
      ],
      child: const MaterialApp(home: ScheduleScreen()),
    );

void main() {
  testWidgets('показывает пары сегодняшнего дня', (tester) async {
    await tester.pumpWidget(_screen());
    await tester.pumpAndSettle();

    expect(find.text('Макроэкономика'), findsOneWidget);
    expect(find.text('Эконометрика'), findsOneWidget);
    expect(find.text('Иностранный язык'), findsNothing); // вторник
  });

  testWidgets('текущая пара помечена «Сейчас»', (tester) async {
    await tester.pumpWidget(_screen());
    await tester.pumpAndSettle();

    expect(find.text('Сейчас'), findsOneWidget);
  });

  testWidgets('свайп влево — следующий день', (tester) async {
    await tester.pumpWidget(_screen());
    await tester.pumpAndSettle();

    await tester.fling(find.byType(PageView), const Offset(-400, 0), 1000);
    await tester.pumpAndSettle();

    expect(find.text('Иностранный язык'), findsOneWidget);
    expect(find.text('Макроэкономика'), findsNothing);
  });

  testWidgets('тап по дню в ленте переключает страницу', (tester) async {
    await tester.pumpWidget(_screen());
    await tester.pumpAndSettle();

    await tester.tap(find.text('Вт'));
    await tester.pumpAndSettle();

    expect(find.text('Иностранный язык'), findsOneWidget);
  });

  testWidgets('пустой день — дружелюбная заглушка', (tester) async {
    await tester.pumpWidget(_screen());
    await tester.pumpAndSettle();

    await tester.tap(find.text('Сб'));
    await tester.pumpAndSettle();

    expect(find.text('Пар нет — отдыхаем'), findsOneWidget);
  });
}
