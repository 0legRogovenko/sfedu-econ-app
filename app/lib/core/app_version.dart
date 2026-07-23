import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'api_client.dart';

/// Build-номер приложения. ДОЛЖЕН совпадать с числом после «+» в version:
/// pubspec.yaml — тест app_version_test.dart сверяет и падает при рассинхроне.
/// Меняется вместе с релизом.
const appBuild = 1;

/// Минимальный build, который сервер считает рабочим (GET /api/version).
/// null — не удалось узнать (офлайн/сбой): НЕ блокируем, офлайн-первое
/// приложение обязано работать без сети.
final minBuildProvider = FutureProvider<int?>((ref) async {
  final dio = ref.watch(dioProvider);
  try {
    final response = await dio.get<Map<String, dynamic>>('/api/version');
    final raw = response.data?['min_build'];
    return raw is int ? raw : null;
  } on DioException {
    return null;
  }
});

/// true — версия старше минимально поддерживаемой, работать нельзя
/// (несовместимый контракт API опаснее, чем блокировка).
final mustUpdateProvider = Provider<bool>((ref) {
  final min = ref.watch(minBuildProvider).asData?.value;
  return min != null && appBuild < min;
});
