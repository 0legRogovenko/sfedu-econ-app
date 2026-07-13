import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Инжектируемое «сейчас» — в тестах переопределяется фиксированной датой.
final clockProvider = Provider<DateTime Function()>((ref) => DateTime.now);
