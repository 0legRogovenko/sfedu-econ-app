/// Человекочитаемая дата новости: «сегодня» / «вчера» / dd.MM.yyyy.
/// `now` инжектится для детерминированных тестов.
String formatNewsDate(DateTime published, {DateTime? now}) {
  final today = _dateOnly(now ?? DateTime.now());
  final day = _dateOnly(published);
  final diff = today.difference(day).inDays;
  if (diff == 0) return 'сегодня';
  if (diff == 1) return 'вчера';
  return '${_two(day.day)}.${_two(day.month)}.${day.year}';
}

DateTime _dateOnly(DateTime d) => DateTime(d.year, d.month, d.day);

String _two(int n) => n.toString().padLeft(2, '0');
