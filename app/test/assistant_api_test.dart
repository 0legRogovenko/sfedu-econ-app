import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sfedu_econ/features/assistant/assistant_api.dart';

/// Подменяет транспорт Dio: отдаёт заданный статус/тело без сети.
class _StubAdapter implements HttpClientAdapter {
  _StubAdapter.reply(this._statusCode, this._body);
  _StubAdapter.fail() : _statusCode = null, _body = null;

  final int? _statusCode;
  final Map<String, dynamic>? _body;
  RequestOptions? lastRequest;

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    lastRequest = options;
    if (_statusCode == null) {
      throw DioException.connectionError(
        requestOptions: options,
        reason: 'нет сети',
      );
    }
    return ResponseBody.fromString(
      jsonEncode(_body),
      _statusCode,
      headers: {
        Headers.contentTypeHeader: [Headers.jsonContentType],
      },
    );
  }

  @override
  void close({bool force = false}) {}
}

DioAssistantApi _api(_StubAdapter adapter) {
  final dio = Dio(BaseOptions(baseUrl: 'http://test'))
    ..httpClientAdapter = adapter;
  return DioAssistantApi(dio);
}

void main() {
  test('успех: 200 отдаёт ответ и флаг fallback', () async {
    final adapter = _StubAdapter.reply(200, {
      'answer': 'Справку берут в 305 кабинете',
      'fallback': false,
    });

    final result = await _api(adapter).ask('Где взять справку?', 'dev-1');

    expect(result, isA<AskAnswer>());
    expect((result as AskAnswer).text, 'Справку берут в 305 кабинете');
    expect(result.fallback, isFalse);
    expect(adapter.lastRequest?.path, '/api/assistant/ask');
    expect(adapter.lastRequest?.data, {
      'question': 'Где взять справку?',
      'device_id': 'dev-1',
    });
  });

  test('fallback: 200 с fallback=true сохраняет флаг', () async {
    final adapter = _StubAdapter.reply(200, {
      'answer': 'Сейчас не могу ответить',
      'fallback': true,
    });

    final result = await _api(adapter).ask('Вопрос', 'dev-1');

    expect((result as AskAnswer).fallback, isTrue);
  });

  test('429 — это исчерпанный лимит, а не общая ошибка', () async {
    final adapter = _StubAdapter.reply(429, {'detail': 'лимит'});

    expect(await _api(adapter).ask('Вопрос', 'dev-1'), isA<AskRateLimited>());
  });

  test('429 несёт detail сервера: лимит настраивается, число знает он',
      () async {
    final adapter = _StubAdapter.reply(429, {
      'detail': 'Не больше 5 вопросов за 24 часа',
    });

    final result = await _api(adapter).ask('Вопрос', 'dev-1');

    expect((result as AskRateLimited).detail, 'Не больше 5 вопросов за 24 часа');
  });

  test('429 без внятного detail — detail пуст, текст возьмут запасной',
      () async {
    final adapter = _StubAdapter.reply(429, {'detail': '   '});

    final result = await _api(adapter).ask('Вопрос', 'dev-1');

    expect((result as AskRateLimited).detail, isNull);
  });

  test('нет сети — AskFailed, а не исключение', () async {
    expect(
      await _api(_StubAdapter.fail()).ask('Вопрос', 'dev-1'),
      isA<AskFailed>(),
    );
  });

  test('ошибка сервера — недоступность, а не «нет интернета»', () async {
    final adapter = _StubAdapter.reply(500, {'detail': 'упал'});

    expect(await _api(adapter).ask('Вопрос', 'dev-1'), isA<AskUnavailable>());
  });

  test('200 без ключа answer — результат, а не TypeError наружу', () async {
    final adapter = _StubAdapter.reply(200, {'reply': 'скью версий'});

    expect(await _api(adapter).ask('Вопрос', 'dev-1'), isA<AskUnavailable>());
  });

  test('200 с answer не-строкой — тоже результат, а не TypeError', () async {
    final adapter = _StubAdapter.reply(200, {'answer': 42});

    expect(await _api(adapter).ask('Вопрос', 'dev-1'), isA<AskUnavailable>());
  });
}
