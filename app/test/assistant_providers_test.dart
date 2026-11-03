import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sfedu_econ/core/device_id.dart';
import 'package:sfedu_econ/features/assistant/assistant_api.dart';
import 'package:sfedu_econ/features/assistant/assistant_message.dart';
import 'package:sfedu_econ/features/assistant/assistant_providers.dart';

/// Фейковый API: отдаёт заданный результат, по желанию — с задержкой,
/// чтобы поймать состояние ожидания.
class _FakeApi implements AssistantApi {
  _FakeApi(this._result, {this.gate});

  final AskResult _result;
  final Completer<void>? gate;
  final List<({String question, String deviceId})> calls = [];

  @override
  Future<AskResult> ask(String question, String deviceId) async {
    calls.add((question: question, deviceId: deviceId));
    if (gate != null) await gate!.future;
    return _result;
  }

  @override
  Future<bool> forget(String deviceId) async => true;
}

/// API, который падает неожиданным исключением мимо всех наших типов ошибок.
class _ThrowingApi implements AssistantApi {
  final List<String> calls = [];

  @override
  Future<AskResult> ask(String question, String deviceId) async {
    calls.add(question);
    throw StateError('что-то, чего мы не предусмотрели');
  }

  @override
  Future<bool> forget(String deviceId) async => true;
}

/// Транспорт, который ведёт себя как настоящий: рвёт запрос по receiveTimeout
/// из опций Dio. Реальных пауз нет — сравниваем длительности, а не ждём их.
class _GenerationAdapter implements HttpClientAdapter {
  _GenerationAdapter(this._generationTime);

  final Duration _generationTime;

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    final limit = options.receiveTimeout;
    if (limit != null && _generationTime > limit) {
      throw DioException.receiveTimeout(
        timeout: limit,
        requestOptions: options,
      );
    }
    return ResponseBody.fromString(
      jsonEncode({'answer': 'Справку берут в 305', 'fallback': false}),
      200,
      headers: {
        Headers.contentTypeHeader: [Headers.jsonContentType],
      },
    );
  }

  @override
  void close({bool force = false}) {}
}

ProviderContainer _container(_FakeApi api) {
  final container = ProviderContainer(
    overrides: [
      assistantApiProvider.overrideWithValue(api),
      deviceIdProvider.overrideWithValue('dev-42'),
    ],
  );
  addTearDown(container.dispose);
  return container;
}

void main() {
  test('чат начинается пустым', () {
    final container = _container(_FakeApi(const AskFailed()));
    expect(container.read(chatProvider), isEmpty);
  });

  test('вопрос виден сразу, ответ — после', () async {
    final gate = Completer<void>();
    final api = _FakeApi(
      const AskAnswer(text: 'Справку берут в 305', fallback: false),
      gate: gate,
    );
    final container = _container(api);

    final asking = container.read(chatProvider.notifier).ask('Где справка?');

    // вопрос уже в ленте, ответа ещё нет
    final pendingState = container.read(chatProvider);
    expect(pendingState.first.role, AssistantRole.user);
    expect(pendingState.first.text, 'Где справка?');
    expect(pendingState.any((m) => m.pending), isTrue);

    gate.complete();
    await asking;

    final state = container.read(chatProvider);
    expect(state.any((m) => m.pending), isFalse);
    expect(state.last.text, 'Справку берут в 305');
    expect(state.last.isAnswer, isTrue);
    expect(api.calls.single.deviceId, 'dev-42');
  });

  test('пустой вопрос не отправляется', () async {
    final api = _FakeApi(const AskAnswer(text: 'ответ', fallback: false));
    final container = _container(api);

    await container.read(chatProvider.notifier).ask('   ');

    expect(container.read(chatProvider), isEmpty);
    expect(api.calls, isEmpty);
  });

  test('вопрос обрезается по краям', () async {
    final api = _FakeApi(const AskAnswer(text: 'ответ', fallback: false));
    final container = _container(api);

    await container.read(chatProvider.notifier).ask('  Где справка?  ');

    expect(api.calls.single.question, 'Где справка?');
  });

  test('пока ждём ответ, второй вопрос не уходит', () async {
    final gate = Completer<void>();
    final api = _FakeApi(
      const AskAnswer(text: 'ответ', fallback: false),
      gate: gate,
    );
    final container = _container(api);

    final first = container.read(chatProvider.notifier).ask('Первый');
    await container.read(chatProvider.notifier).ask('Второй');

    expect(api.calls, hasLength(1));
    gate.complete();
    await first;
  });

  test('ошибка сети даёт сообщение-ошибку, а не исключение', () async {
    final container = _container(_FakeApi(const AskFailed()));

    await container.read(chatProvider.notifier).ask('Вопрос');

    final last = container.read(chatProvider).last;
    expect(last.isError, isTrue);
    expect(last.isAnswer, isFalse);
    expect(last.text, contains('Нужен интернет'));
  });

  test('429 показывает текст лимита от сервера, а не своё число', () async {
    final container = _container(
      _FakeApi(const AskRateLimited(detail: 'Не больше 5 вопросов за 24 часа')),
    );

    await container.read(chatProvider.notifier).ask('Вопрос');

    final last = container.read(chatProvider).last;
    expect(last.isError, isTrue);
    expect(last.text, 'Не больше 5 вопросов за 24 часа');
  });

  test('429 без detail — запасной текст без выдуманного числа', () async {
    final container = _container(_FakeApi(const AskRateLimited()));

    await container.read(chatProvider.notifier).ask('Вопрос');

    final last = container.read(chatProvider).last;
    expect(last.text, rateLimitMessage);
    expect(last.text, isNot(contains('20')));
  });

  test('ошибка сервера не врёт про интернет', () async {
    final container = _container(_FakeApi(const AskUnavailable()));

    await container.read(chatProvider.notifier).ask('Вопрос');

    final last = container.read(chatProvider).last;
    expect(last.isError, isTrue);
    expect(last.text, unavailableMessage);
    expect(last.text, isNot(contains('интернет')));
  });

  test(
    'fallback-ответ показывается как ответ, но без подписи «Ответ AI»',
    () async {
      final container = _container(
        _FakeApi(
          const AskAnswer(text: 'Сейчас не могу ответить', fallback: true),
        ),
      );

      await container.read(chatProvider.notifier).ask('Вопрос');

      final last = container.read(chatProvider).last;
      expect(last.isAnswer, isTrue); // чип контактов уместен
      expect(last.text, 'Сейчас не могу ответить');
      expect(last.showsDisclaimer, isFalse);
    },
  );

  test('обычный ответ модели подписан «Ответ AI»', () async {
    final container = _container(
      _FakeApi(const AskAnswer(text: 'Справку берут в 305', fallback: false)),
    );

    await container.read(chatProvider.notifier).ask('Вопрос');

    expect(container.read(chatProvider).last.showsDisclaimer, isTrue);
  });

  test('неожиданное исключение не запирает экран навсегда', () async {
    final api = _ThrowingApi();
    final container = ProviderContainer(
      overrides: [
        assistantApiProvider.overrideWithValue(api),
        deviceIdProvider.overrideWithValue('dev-42'),
      ],
    );
    addTearDown(container.dispose);

    await container.read(chatProvider.notifier).ask('Первый');

    // плейсхолдер снят, значит поле ввода снова активно
    expect(container.read(chatProvider).any((m) => m.pending), isFalse);
    expect(container.read(chatProvider).last.isError, isTrue);

    // и следующий вопрос действительно уходит
    await container.read(chatProvider.notifier).ask('Второй');
    expect(api.calls, ['Первый', 'Второй']);
  });

  test(
    'генерация дольше 10s не рвётся таймаутом: у помощника свой Dio',
    () async {
      final container = ProviderContainer(
        overrides: [deviceIdProvider.overrideWithValue('dev-42')],
      );
      addTearDown(container.dispose);
      container.read(assistantDioProvider).httpClientAdapter =
          _GenerationAdapter(const Duration(seconds: 15));

      await container.read(chatProvider.notifier).ask('Где справка?');

      final last = container.read(chatProvider).last;
      expect(last.isAnswer, isTrue, reason: 'ответ, а не «нужен интернет»');
      expect(last.text, 'Справку берут в 305');
    },
  );
}
