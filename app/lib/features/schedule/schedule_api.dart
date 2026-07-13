import 'package:dio/dio.dart';

enum ScheduleApiStatus { ok, notModified, failure }

class ScheduleApiResponse {
  const ScheduleApiResponse._(this.status, this.lessonsJson, this.etag);

  factory ScheduleApiResponse.ok(
    List<Map<String, dynamic>> lessons,
    String? etag,
  ) =>
      ScheduleApiResponse._(ScheduleApiStatus.ok, lessons, etag);

  factory ScheduleApiResponse.notModified() =>
      const ScheduleApiResponse._(ScheduleApiStatus.notModified, null, null);

  factory ScheduleApiResponse.failure() =>
      const ScheduleApiResponse._(ScheduleApiStatus.failure, null, null);

  final ScheduleApiStatus status;
  final List<Map<String, dynamic>>? lessonsJson;
  final String? etag;
}

abstract interface class ScheduleApi {
  Future<ScheduleApiResponse> fetchSchedule(int groupId, String? etag);
}

class DioScheduleApi implements ScheduleApi {
  DioScheduleApi(this._dio);

  final Dio _dio;

  @override
  Future<ScheduleApiResponse> fetchSchedule(int groupId, String? etag) async {
    try {
      final response = await _dio.get<List<dynamic>>(
        '/api/schedule',
        queryParameters: {'group_id': groupId},
        options: Options(
          headers: {'If-None-Match': ?etag},
          validateStatus: (status) => status == 200 || status == 304,
        ),
      );
      if (response.statusCode == 304) {
        return ScheduleApiResponse.notModified();
      }
      return ScheduleApiResponse.ok(
        (response.data ?? []).cast<Map<String, dynamic>>(),
        response.headers.value('etag'),
      );
    } on DioException {
      return ScheduleApiResponse.failure();
    }
  }
}
