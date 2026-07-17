import 'exam_event.dart';

/// Экзамены, разложенные на ближайшие и прошедшие.
class SplitExams {
  const SplitExams({required this.upcoming, required this.past});
  final List<ExamEvent> upcoming;
  final List<ExamEvent> past;
}

/// Ключ сортировки: пары без даты («уточняется») — в конец списка ближайших.
DateTime _sortKey(ExamEvent e) => e.examAt ?? DateTime(9999);

/// Разбивает экзамены на ближайшие (дата экзамена сегодня/в будущем или ещё не
/// известна) и прошедшие (строго раньше сегодняшнего дня). Обе группы
/// сортируются по дате экзамена по возрастанию.
SplitExams splitExams(List<ExamEvent> items, DateTime now) {
  final startOfToday = DateTime(now.year, now.month, now.day);
  final upcoming = <ExamEvent>[];
  final past = <ExamEvent>[];
  for (final e in items) {
    if (e.examAt != null && e.examAt!.isBefore(startOfToday)) {
      past.add(e);
    } else {
      upcoming.add(e);
    }
  }
  upcoming.sort((a, b) => _sortKey(a).compareTo(_sortKey(b)));
  past.sort((a, b) => _sortKey(a).compareTo(_sortKey(b)));
  return SplitExams(upcoming: upcoming, past: past);
}

String _pad(int n) => n.toString().padLeft(2, '0');

/// Дата-время экзамена для UI. null — дыра источника, показываем «уточняется»,
/// а не прячем запись.
String formatExamDateTime(DateTime? dt) {
  if (dt == null) return 'уточняется';
  return '${_pad(dt.day)}.${_pad(dt.month)}.${dt.year}, '
      '${_pad(dt.hour)}:${_pad(dt.minute)}';
}
