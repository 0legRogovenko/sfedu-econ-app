import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api_client.dart';
import 'teacher.dart';

/// Справочник преподавателей с бэкенда (отсортирован сервером по ФИО).
/// Кэша в drift нет намеренно: список нужен только на экране поиска, а без
/// сети открывать поиск незачем — расписание уже открытого преподавателя
/// читается из своего скоупа кэша.
final teachersProvider = FutureProvider<List<Teacher>>((ref) async {
  final dio = ref.watch(dioProvider);
  final response = await dio.get<List<dynamic>>('/api/teachers');
  return (response.data ?? [])
      .map((item) => Teacher.fromJson(item as Map<String, dynamic>))
      .toList();
});
