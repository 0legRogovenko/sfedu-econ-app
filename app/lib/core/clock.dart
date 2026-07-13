import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Инжектируемое «сейчас» — в тестах переопределяется фиксированной датой.
// Время устройства; факультет живёт в одном часовом поясе (RU, без DST).
final clockProvider = Provider<DateTime Function()>((ref) => DateTime.now);
