import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api_client.dart';
import '../../core/device_id.dart';
import 'assistant_api.dart';
import 'assistant_message.dart';

/// Свой Dio: общий настроен под дешёвые JSON-ручки (receiveTimeout 10s),
/// а модель генерирует ответ дольше — на 10s запрос рвался таймаутом, хотя
/// бэкенд уже списал вопрос из квоты. 60s покрывают с запасом худший честный
/// случай бэкенда: он ждёт Anthropic 20s и делает один ретрай (~40s), после
/// чего отвечает заглушкой. Запас нужен, чтобы дождаться этой заглушки, а не
/// показать «нужен интернет» при работающей связи.
final assistantDioProvider = Provider<Dio>((ref) {
  final shared = ref.watch(dioProvider);
  return Dio(
    shared.options.copyWith(receiveTimeout: const Duration(seconds: 60)),
  );
});

final assistantApiProvider = Provider<AssistantApi>(
  (ref) => DioAssistantApi(ref.watch(assistantDioProvider)),
);

/// Тексты отказов по нашей вине: пользователь должен понимать причину
/// и что делать дальше.
const offlineMessage =
    'Нужен интернет — помощник отвечает только онлайн. '
    'Проверьте связь и спросите ещё раз.';
const unavailableMessage =
    'Помощник временно недоступен, попробуйте позже.';

/// Запасной текст: число вопросов настраивается на сервере, поэтому в норме
/// показываем detail из 429-го ответа, а не эту заготовку.
const rateLimitMessage =
    'Помощник отвечает ограниченное число вопросов в сутки. '
    'Попробуйте позже или загляните в контакты деканата.';

/// Чат помощника. История только в памяти: постоянного треда в MVP нет,
/// офлайн-кэш ответу тоже не нужен (он online-only).
class ChatNotifier extends Notifier<List<AssistantMessage>> {
  @override
  List<AssistantMessage> build() => const [];

  bool get _waiting => state.any((m) => m.pending);

  Future<void> ask(String question) async {
    final text = question.trim();
    if (text.isEmpty || _waiting) return;

    state = [
      ...state,
      AssistantMessage.user(text),
      const AssistantMessage.pending(),
    ];

    var reply = const AssistantMessage.error(unavailableMessage);
    try {
      final result = await ref
          .read(assistantApiProvider)
          .ask(text, ref.read(deviceIdProvider));

      reply = switch (result) {
        AskAnswer(text: final answer, fallback: final fallback) =>
          AssistantMessage.answer(answer, fallback: fallback),
        AskRateLimited(detail: final detail) =>
          AssistantMessage.error(detail ?? rateLimitMessage),
        AskUnavailable() => const AssistantMessage.error(unavailableMessage),
        AskFailed() => const AssistantMessage.error(offlineMessage),
      };
    } catch (_) {
      // Глотаем намеренно: reply остаётся заготовкой об ошибке.
    } finally {
      // Плейсхолдер снимается при ЛЮБОМ исходе: пока он в ленте, _waiting
      // остаётся true и поле ввода заблокировано до перезапуска приложения.
      state = [...state.where((m) => !m.pending), reply];
    }
  }
}

final chatProvider =
    NotifierProvider<ChatNotifier, List<AssistantMessage>>(ChatNotifier.new);
