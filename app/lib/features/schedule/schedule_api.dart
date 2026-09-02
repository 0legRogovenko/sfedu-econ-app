import 'package:dio/dio.dart';

import 'schedule_scope.dart';

enum ScheduleApiStatus { ok, notModified, failure }

class ScheduleApiResponse {
  const ScheduleApiResponse._(this.status, this.scheduleJson, this.etag);

  factory ScheduleApiResponse.ok(Map<String, dynamic> schedule, String? etag) =>
      ScheduleApiResponse._(ScheduleApiStatus.ok, schedule, etag);

  factory ScheduleApiResponse.notModified() =>
      const ScheduleApiResponse._(ScheduleApiStatus.notModified, null, null);

  factory ScheduleApiResponse.failure() =>
      const ScheduleApiResponse._(ScheduleApiStatus.failure, null, null);

  final ScheduleApiStatus status;
  // Объект {lessons, modules, week_calendar} — breaking change контракта:
  // прежде был плоский массив пар.
  final Map<String, dynamic>? scheduleJson;
  final String? etag;
}

abstract interface class ScheduleApi {
  Future<ScheduleApiResponse> fetchSchedule(ScheduleScope scope, String? etag);
}

class DioScheduleApi implements ScheduleApi {
  DioScheduleApi(this._dio);

  final Dio _dio;

  @override
  Future<ScheduleApiResponse> fetchSchedule(
    ScheduleScope scope,
    String? etag,
  ) async {
    try {
      final response = await _dio.get<Map<String, dynamic>>(
        '/api/schedule',
        // Ручка принимает РОВНО ОДИН из group_id/teacher_id — имя параметра
        // выбирает сам скоуп.
        queryParameters: {scope.queryParam: scope.id},
        options: Options(
          headers: {'If-None-Match': ?etag},
          validateStatus: (status) => status == 200 || status == 304,
        ),
      );
      if (response.statusCode == 304) {
        return ScheduleApiResponse.notModified();
      }
      return ScheduleApiResponse.ok(
        response.data ?? const {},
        response.headers.value('etag'),
      );
    } on DioException {
      return ScheduleApiResponse.failure();
    }
  }
}
