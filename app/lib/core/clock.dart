import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Демо-дата для запуска вне семестра: летом расписание честно пусто, и
/// проверить экран на живых данных иначе нельзя. Только чтение из dart-define,
/// в обычной сборке пусто → реальные часы.
/// Пример: flutter run --dart-define=DEMO_TODAY=2025-09-16
const _demoToday = String.fromEnvironment('DEMO_TODAY');

/// Инжектируемое «сейчас» — в тестах переопределяется фиксированной датой.
// Время устройства; факультет живёт в одном часовом поясе (RU, без DST).
final clockProvider = Provider<DateTime Function()>((ref) {
  if (_demoToday.isNotEmpty) {
    final demo = DateTime.parse(_demoToday);
    // Сохраняем текущее время суток, чтобы подсветка «текущей пары» жила
    return () {
      final now = DateTime.now();
      return DateTime(
          demo.year, demo.month, demo.day, now.hour, now.minute, now.second);
    };
  }
  return DateTime.now;
});
