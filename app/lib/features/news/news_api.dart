import 'package:dio/dio.dart';

/// Абстракция сетевого доступа к ленте новостей. В тестах подменяется фейком.
abstract interface class NewsApi {
  /// Возвращает страницу новостей или null при сетевой ошибке
  /// (репозиторий сам решает, показать кэш или загрузить дальше).
  Future<List<Map<String, dynamic>>?> fetchPage({
    DateTime? before,
    int? beforeId,
    int limit,
  });
}

class DioNewsApi implements NewsApi {
  DioNewsApi(this._dio);

  final Dio _dio;

  @override
  Future<List<Map<String, dynamic>>?> fetchPage({
    DateTime? before,
    int? beforeId,
    int limit = 20,
  }) async {
    try {
      final response = await _dio.get<List<dynamic>>(
        '/api/news',
        queryParameters: {
          'limit': limit,
          if (before != null) 'before': before.toIso8601String(),
          'before_id': ?beforeId,
        },
      );
      return (response.data ?? []).cast<Map<String, dynamic>>();
    } on DioException {
      return null;
    }
  }
}
