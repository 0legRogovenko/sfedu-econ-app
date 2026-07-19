import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sfedu_econ/core/clock.dart';
import 'package:sfedu_econ/features/exams/exam_event.dart';
import 'package:sfedu_econ/features/exams/exams_providers.dart';
import 'package:sfedu_econ/features/exams/exams_repository.dart';
import 'package:sfedu_econ/features/exams/exams_screen.dart';

// «Сейчас» для экрана — 10.04.2026.
final _now = DateTime(2026, 4, 10, 12);

ExamEvent _exam({
  int id = 1,
  String subject = 'Экосистема организации',
  String? teacher = 'Чернова О.А.',
  DateTime? consultationAt,
  DateTime? examAt,
  String? room = '214',
  String? kind = 'устный',
}) =>
    ExamEvent(
      id: id,
      groupId: 3,
      subject: subject,
      teacher: teacher,
      consultationAt: consultationAt,
      examAt: examAt,
      room: room,
      kind: kind,
    );

/// Фейковый нотифаер: сразу отдаёт готовый feed, refresh — no-op.
class _FakeFeed extends ExamsFeedNotifier {
  _FakeFeed(this._feed);
  final ExamsFeed _feed;

  @override
  Future<ExamsFeed> build() async => _feed;

  @override
  Future<void> refresh() async {}
}

Widget _screen(ExamsFeed feed) => ProviderScope(
      overrides: [
        clockProvider.overrideWithValue(() => _now),
        examsFeedProvider.overrideWith(() => _FakeFeed(feed)),
      ],
      child: const MaterialApp(home: ExamsScreen()),
    );

void main() {
  testWidgets('карточка экзамена: предмет, преподаватель, дата, аудитория, форма',
      (tester) async {
    await tester.pumpWidget(_screen(ExamsFeed(
      items: [
        _exam(
          consultationAt: DateTime(2026, 4, 20, 11),
          examAt: DateTime(2026, 4, 21, 9),
        ),
      ],
      offline: false,
    )));
    await tester.pumpAndSettle();

    expect(find.text('Экосистема организации'), findsOneWidget);
    expect(find.text('Чернова О.А.'), findsOneWidget);
    expect(find.textContaining('21.04.2026, 09:00'), findsOneWidget);
    // номер аудитории — с префиксом, и ровно одним (регрессия «ауд. ауд.118»)
    expect(find.textContaining('ауд. 214'), findsOneWidget);
    expect(find.textContaining('ауд. ауд.'), findsNothing);
    expect(find.textContaining('устный'), findsOneWidget);
  });

  testWidgets('площадка вместо номера — без префикса «ауд.»', (tester) async {
    await tester.pumpWidget(_screen(ExamsFeed(
      items: [
        _exam(
          examAt: DateTime(2026, 4, 21, 9),
          room: 'Microsoft Teams',
        ),
      ],
      offline: false,
    )));
    await tester.pumpAndSettle();

    expect(find.textContaining('Microsoft Teams'), findsOneWidget);
    expect(find.textContaining('ауд. Microsoft Teams'), findsNothing);
  });

  testWidgets('null-поля показываются как «уточняется», запись не прячется',
      (tester) async {
    await tester.pumpWidget(_screen(ExamsFeed(
      items: [
        _exam(
          subject: 'Матанализ',
          teacher: null,
          examAt: null,
          consultationAt: null,
          room: null,
          kind: null,
        ),
      ],
      offline: false,
    )));
    await tester.pumpAndSettle();

    expect(find.text('Матанализ'), findsOneWidget); // запись видна
    expect(find.textContaining('уточняется'), findsWidgets);
    expect(find.text('Преподаватель уточняется'), findsOneWidget);
  });

  testWidgets('прошедшие экзамены — под заголовком «Прошедшие»',
      (tester) async {
    await tester.pumpWidget(_screen(ExamsFeed(
      items: [
        _exam(id: 1, subject: 'Прошедший', examAt: DateTime(2026, 4, 1, 9)),
        _exam(id: 2, subject: 'Будущий', examAt: DateTime(2026, 4, 20, 9)),
      ],
      offline: false,
    )));
    await tester.pumpAndSettle();

    expect(find.text('Прошедшие'), findsOneWidget);
    expect(find.text('Будущий'), findsOneWidget);
    expect(find.text('Прошедший'), findsOneWidget);
  });

  testWidgets('пустой список — дружелюбная заглушка', (tester) async {
    await tester.pumpWidget(
        _screen(const ExamsFeed(items: [], offline: false)));
    await tester.pumpAndSettle();

    expect(find.text('Экзамены не назначены'), findsOneWidget);
  });

  testWidgets('офлайн без кэша — «нужна сеть», а не «экзаменов нет»',
      (tester) async {
    // Пустой список при неудачном синке значит «не загрузилось», а не
    // «экзаменов не назначено»: студент прочитал бы сбой сети как хорошую
    // новость и не стал бы обновлять.
    await tester.pumpWidget(_screen(const ExamsFeed(items: [], offline: true)));
    await tester.pumpAndSettle();

    expect(find.text('Нет данных. Для первой загрузки нужна сеть'),
        findsOneWidget);
    expect(find.text('Экзамены не назначены'), findsNothing);
  });

  testWidgets('офлайн без кэша не обещает сохранённых экзаменов',
      (tester) async {
    // Плашка «Показаны сохранённые экзамены» над пустым экраном — прямая ложь.
    await tester.pumpWidget(_screen(const ExamsFeed(items: [], offline: true)));
    await tester.pumpAndSettle();

    expect(find.textContaining('Показаны сохранённые'), findsNothing);
  });

  testWidgets('офлайн-плашка при недоступной сети', (tester) async {
    await tester.pumpWidget(_screen(ExamsFeed(
      items: [_exam(examAt: DateTime(2026, 4, 21, 9))],
      offline: true,
    )));
    await tester.pumpAndSettle();

    expect(
        find.text('Нет сети. Показаны сохранённые экзамены'), findsOneWidget);
  });
}
