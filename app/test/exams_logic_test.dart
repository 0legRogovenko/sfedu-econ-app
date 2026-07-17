import 'package:flutter_test/flutter_test.dart';
import 'package:sfedu_econ/features/exams/exam_event.dart';
import 'package:sfedu_econ/features/exams/exams_logic.dart';

ExamEvent _exam({int id = 1, DateTime? examAt}) => ExamEvent(
      id: id,
      groupId: 3,
      subject: 'Предмет $id',
      teacher: null,
      consultationAt: null,
      examAt: examAt,
      room: null,
      kind: null,
    );

void main() {
  group('splitExams', () {
    final now = DateTime(2026, 4, 10, 12);

    test('прошедший экзамен — в past, будущий — в upcoming', () {
      final split = splitExams([
        _exam(id: 1, examAt: DateTime(2026, 4, 1, 9)), // прошёл
        _exam(id: 2, examAt: DateTime(2026, 4, 20, 9)), // будущий
      ], now);
      expect(split.past.map((e) => e.id), [1]);
      expect(split.upcoming.map((e) => e.id), [2]);
    });

    test('экзамен без даты («уточняется») — в upcoming, в конце', () {
      final split = splitExams([
        _exam(id: 1, examAt: null),
        _exam(id: 2, examAt: DateTime(2026, 4, 20, 9)),
      ], now);
      expect(split.upcoming.map((e) => e.id), [2, 1]); // null — в конце
      expect(split.past, isEmpty);
    });

    test('экзамен сегодня утром остаётся ближайшим (не прошедшим)', () {
      final split = splitExams([
        _exam(id: 1, examAt: DateTime(2026, 4, 10, 9)),
      ], now);
      expect(split.upcoming.map((e) => e.id), [1]);
      expect(split.past, isEmpty);
    });

    test('ближайшие сортируются по дате по возрастанию', () {
      final split = splitExams([
        _exam(id: 1, examAt: DateTime(2026, 4, 25)),
        _exam(id: 2, examAt: DateTime(2026, 4, 15)),
      ], now);
      expect(split.upcoming.map((e) => e.id), [2, 1]);
    });
  });

  group('formatExamDateTime', () {
    test('null → «уточняется»', () {
      expect(formatExamDateTime(null), 'уточняется');
    });
    test('дата и время с ведущими нулями', () {
      expect(formatExamDateTime(DateTime(2026, 4, 9, 9, 0)), '09.04.2026, 09:00');
    });
  });

  group('ExamEvent.fromJson', () {
    test('парсит поля, null-даты допустимы', () {
      final e = ExamEvent.fromJson({
        'id': 7,
        'group_id': 5,
        'subject': 'Экосистема современной организации',
        'teacher': 'Чернова О.А.',
        'consultation_at': '2026-04-08T11:00:00',
        'exam_at': '2026-04-09T09:00:00',
        'room': '214',
        'kind': 'устный',
      });
      expect(e.subject, 'Экосистема современной организации');
      expect(e.teacher, 'Чернова О.А.');
      expect(e.consultationAt, DateTime(2026, 4, 8, 11));
      expect(e.examAt, DateTime(2026, 4, 9, 9));
      expect(e.kind, 'устный');
    });

    test('null-поля не роняют разбор', () {
      final e = ExamEvent.fromJson({
        'id': 8,
        'group_id': 5,
        'subject': 'Матанализ',
        'teacher': null,
        'consultation_at': null,
        'exam_at': null,
        'room': null,
        'kind': null,
      });
      expect(e.teacher, isNull);
      expect(e.examAt, isNull);
      expect(e.room, isNull);
    });
  });
}
