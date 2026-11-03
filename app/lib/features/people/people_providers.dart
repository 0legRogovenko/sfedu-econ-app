import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api_client.dart';
import '../exams/exam_event.dart';
import '../schedule/schedule_data.dart';
import 'person.dart';

/// Единый справочник людей с бэкенда. Кэша в drift нет: список нужен только на
/// вкладке «Контакты», а офлайн там честная плашка про сеть.
final peopleProvider = FutureProvider<List<Person>>((ref) async {
  final dio = ref.watch(dioProvider);
  final response = await dio.get<List<dynamic>>('/api/persons');
  return (response.data ?? [])
      .map((item) => Person.fromJson(item as Map<String, dynamic>))
      .toList();
});

/// Расписание конкретного человека по id. autoDispose: экранов может быть
/// открыто много (переход из карточки в карточку), держать их вечно незачем.
///
/// Без drift-кэша намеренно: расписание человека смотрят изредка, а офлайн
/// экран честно показывает «нужна сеть» — так проще, чем заводить ещё один
/// скоуп кэша со сменой schemaVersion.
final personScheduleProvider = FutureProvider.autoDispose
    .family<ScheduleData, String>((ref, id) async {
      final dio = ref.watch(dioProvider);
      final response = await dio.get<Map<String, dynamic>>(
        '/api/persons/$id/schedule',
        options: Options(validateStatus: (status) => status == 200),
      );
      return ScheduleData.fromJson(response.data ?? const {});
    });

/// Экзамены человека — для карточки. Той же природы, что personScheduleProvider:
/// без drift-кэша, autoDispose, офлайн — честная ошибка.
final personExamsProvider = FutureProvider.autoDispose
    .family<List<ExamEvent>, String>((ref, id) async {
      final dio = ref.watch(dioProvider);
      final response = await dio.get<List<dynamic>>(
        '/api/persons/$id/exams',
        options: Options(validateStatus: (status) => status == 200),
      );
      return (response.data ?? const [])
          .map((e) => ExamEvent.fromJson(e as Map<String, dynamic>))
          .toList();
    });
