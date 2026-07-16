enum AssistantRole { user, assistant }

/// Сообщение чата помощника. Живёт только в памяти: постоянного треда
/// в MVP нет, перезапуск очищает историю.
class AssistantMessage {
  const AssistantMessage({
    required this.role,
    required this.text,
    this.pending = false,
    this.isError = false,
    this.fallback = false,
  });

  const AssistantMessage.user(String text)
      : this(role: AssistantRole.user, text: text);

  const AssistantMessage.answer(String text, {bool fallback = false})
      : this(role: AssistantRole.assistant, text: text, fallback: fallback);

  /// Отказ по нашей вине (нет сети, исчерпан лимит) — не ответ модели,
  /// поэтому без дисклеймера.
  const AssistantMessage.error(String text)
      : this(role: AssistantRole.assistant, text: text, isError: true);

  /// Плейсхолдер «печатает» на время запроса: он же флаг ожидания —
  /// пока такой есть в ленте, новый вопрос не отправляется.
  const AssistantMessage.pending()
      : this(role: AssistantRole.assistant, text: '', pending: true);

  final AssistantRole role;
  final String text;
  final bool pending;
  final bool isError;

  /// Заглушка бэкенда вместо ответа модели (сервер не смог сходить в Anthropic).
  final bool fallback;

  /// Чип контактов уместен под любым ответом, включая заглушку.
  bool get isAnswer =>
      role == AssistantRole.assistant && !pending && !isError;

  /// Подпись «Ответ AI» — только там, где отвечала модель. Под заглушкой
  /// бэкенда модель не участвовала вообще: такая подпись прямо врёт.
  bool get showsDisclaimer => isAnswer && !fallback;
}
