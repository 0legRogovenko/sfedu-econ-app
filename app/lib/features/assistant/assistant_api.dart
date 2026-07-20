import 'package:dio/dio.dart';

/// Итог запроса к помощнику. Причина отказа разделена по типам, чтобы UI
/// говорил правду: «нет интернета» и «кончился лимит» — разные истории.
sealed class AskResult {
  const AskResult();
}

/// Ответ получен. `fallback` — сервер не смог сходить в модель и отдал
/// заготовку с контактами деканата.
class AskAnswer extends AskResult {
  const AskAnswer({required this.text, required this.fallback});

  final String text;
  final bool fallback;
}

/// 429 — исчерпана суточная квота вопросов на это устройство.
/// `detail` — текст лимита от сервера: лимит настраивается
/// (ASSISTANT_DAILY_LIMIT), поэтому точное число знает только сервер.
class AskRateLimited extends AskResult {
  const AskRateLimited({this.detail});

  final String? detail;
}

/// Связи нет: запрос не дошёл до сервера (обрыв, таймаут).
class AskFailed extends AskResult {
  const AskFailed();
}

/// Сервер ответил, но ошибкой либо телом, которое мы не понимаем.
/// Связь при этом рабочая — про интернет говорить нельзя.
class AskUnavailable extends AskResult {
  const AskUnavailable();
}

/// Абстракция сетевого доступа к помощнику. В тестах подменяется фейком.
abstract interface class AssistantApi {
  Future<AskResult> ask(String question, String deviceId);

  /// Удаляет с сервера логи помощника этого устройства. true — удалено.
  Future<bool> forget(String deviceId);
}

class DioAssistantApi implements AssistantApi {
  DioAssistantApi(this._dio);
  final Dio _dio;

  @override
  Future<AskResult> ask(String question, String deviceId) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        '/api/assistant/ask',
        data: {'question': question, 'device_id': deviceId},
      );
      // Проверяем тип, а не приводим: `as String` на теле без answer кидал бы
      // TypeError мимо `on DioException` — наружу летело исключение.
      final answer = response.data?['answer'];
      if (answer is! String) return const AskUnavailable();
      return AskAnswer(
        text: answer,
        fallback: response.data?['fallback'] == true,
      );
    } on DioException catch (error) {
      if (error.response?.statusCode == 429) {
        return AskRateLimited(detail: _detail(error.response?.data));
      }
      // Сервер ответил — связь есть, это не «нет интернета».
      if (error.response != null) return const AskUnavailable();
      return const AskFailed();
    }
  }

  @override
  Future<bool> forget(String deviceId) async {
    try {
      final response = await _dio.delete<Map<String, dynamic>>(
        '/api/assistant/data',
        queryParameters: {'device_id': deviceId},
      );
      return response.statusCode == 200;
    } on DioException {
      return false;
    }
  }

  String? _detail(Object? data) {
    if (data is! Map) return null;
    final detail = data['detail'];
    if (detail is! String || detail.trim().isEmpty) return null;
    return detail.trim();
  }
}
