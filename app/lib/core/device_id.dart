import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:uuid/uuid.dart';

import 'prefs.dart';

const _prefsKey = 'device_id';

/// Анонимный идентификатор устройства для rate-limit на /api/assistant/ask.
/// Генерируется один раз при первом обращении и живёт в prefs;
/// персональных данных не содержит.
final deviceIdProvider = Provider<String>((ref) {
  final prefs = ref.watch(sharedPreferencesProvider);
  final saved = prefs.getString(_prefsKey);
  if (saved != null && saved.isNotEmpty) return saved;

  final id = const Uuid().v4();
  // Запись асинхронна, но id уже возвращён: в этом запуске значение держит
  // кэш провайдера, в следующем — prefs.
  unawaited(prefs.setString(_prefsKey, id));
  return id;
});
