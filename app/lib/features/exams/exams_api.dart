import 'package:dio/dio.dart';

enum ExamsApiStatus { ok, notModified, failure }

class ExamsApiResponse {
  const ExamsApiResponse._(this.status, this.examsJson, this.etag);

  factory ExamsApiResponse.ok(List<Map<String, dynamic>> exams, String? etag) =>
      ExamsApiResponse._(ExamsApiStatus.ok, exams, etag);

  factory ExamsApiResponse.notModified() =>
      const ExamsApiResponse._(ExamsApiStatus.notModified, null, null);

  factory ExamsApiResponse.failure() =>
      const ExamsApiResponse._(ExamsApiStatus.failure, null, null);

  final ExamsApiStatus status;
  final List<Map<String, dynamic>>? examsJson;
  final String? etag;
}

abstract interface class ExamsApi {
  Future<ExamsApiResponse> fetchExams(int groupId, String? etag);
}

class DioExamsApi implements ExamsApi {
  DioExamsApi(this._dio);

  final Dio _dio;

  @override
  Future<ExamsApiResponse> fetchExams(int groupId, String? etag) async {
    try {
      final response = await _dio.get<List<dynamic>>(
        '/api/exams',
        queryParameters: {'group_id': groupId},
        options: Options(
          headers: {'If-None-Match': ?etag},
          validateStatus: (status) => status == 200 || status == 304,
        ),
      );
      if (response.statusCode == 304) {
        return ExamsApiResponse.notModified();
      }
      return ExamsApiResponse.ok(
        (response.data ?? []).cast<Map<String, dynamic>>(),
        response.headers.value('etag'),
      );
    } on DioException {
      return ExamsApiResponse.failure();
    }
  }
}
