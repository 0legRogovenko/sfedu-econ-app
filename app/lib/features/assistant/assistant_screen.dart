import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'assistant_message.dart';
import 'assistant_providers.dart';

/// Подсказки на пустом экране: с чего начать разговор. Список короткий —
/// это примеры жанра вопроса, а не меню.
const assistantSuggestions = [
  'Как получить справку об обучении?',
  'Когда пересдачи?',
  'Как оформить стипендию?',
  'Часы работы деканата',
];

const assistantDisclaimer = 'Ответ AI — важное проверяйте в деканате';

/// Ограничение бэкенда (`question` максимум 1000 символов): режем здесь,
/// чтобы длинный вопрос не улетал в 422 вместо ответа.
const _maxQuestionLength = 1000;

class AssistantScreen extends ConsumerStatefulWidget {
  const AssistantScreen({super.key});

  @override
  ConsumerState<AssistantScreen> createState() => _AssistantScreenState();
}

class _AssistantScreenState extends ConsumerState<AssistantScreen> {
  final _controller = TextEditingController();
  final _scroll = ScrollController();

  @override
  void dispose() {
    _controller.dispose();
    _scroll.dispose();
    super.dispose();
  }

  Future<void> _ask(String question) async {
    if (question.trim().isEmpty) return;
    _controller.clear();
    await ref.read(chatProvider.notifier).ask(question);
    if (!_scroll.hasClients) return;
    await _scroll.animateTo(
      _scroll.position.maxScrollExtent,
      duration: const Duration(milliseconds: 200),
      curve: Curves.easeOut,
    );
  }

  @override
  Widget build(BuildContext context) {
    final messages = ref.watch(chatProvider);
    final waiting = messages.any((m) => m.pending);

    return Scaffold(
      appBar: AppBar(title: const Text('Помощник')),
      body: Column(
        children: [
          Expanded(
            child: messages.isEmpty
                ? _Suggestions(onTap: _ask)
                : ListView.builder(
                    controller: _scroll,
                    padding: const EdgeInsets.all(12),
                    itemCount: messages.length,
                    itemBuilder: (context, index) =>
                        _MessageBubble(message: messages[index]),
                  ),
          ),
          _Composer(
            controller: _controller,
            enabled: !waiting,
            onSubmit: () => _ask(_controller.text),
          ),
        ],
      ),
    );
  }
}

class _Suggestions extends StatelessWidget {
  const _Suggestions({required this.onTap});

  final void Function(String question) onTap;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return ListView(
      padding: const EdgeInsets.all(24),
      children: [
        const SizedBox(height: 24),
        Icon(
          Icons.chat_bubble_outline,
          size: 48,
          color: theme.colorScheme.primary,
        ),
        const SizedBox(height: 16),
        Text(
          'Задайте вопрос о факультете',
          textAlign: TextAlign.center,
          style: theme.textTheme.titleMedium,
        ),
        const SizedBox(height: 24),
        Wrap(
          alignment: WrapAlignment.center,
          spacing: 8,
          runSpacing: 8,
          children: [
            for (final suggestion in assistantSuggestions)
              ActionChip(
                label: Text(suggestion),
                onPressed: () => onTap(suggestion),
              ),
          ],
        ),
      ],
    );
  }
}

class _MessageBubble extends StatelessWidget {
  const _MessageBubble({required this.message});

  final AssistantMessage message;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isUser = message.role == AssistantRole.user;

    final Color background;
    if (isUser) {
      background = theme.colorScheme.primaryContainer;
    } else if (message.isError) {
      background = theme.colorScheme.errorContainer;
    } else {
      background = theme.colorScheme.surfaceContainerHighest;
    }

    return Align(
      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Column(
        crossAxisAlignment:
            isUser ? CrossAxisAlignment.end : CrossAxisAlignment.start,
        children: [
          Container(
            constraints: const BoxConstraints(maxWidth: 320),
            margin: const EdgeInsets.only(bottom: 4),
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
            decoration: BoxDecoration(
              color: background,
              borderRadius: BorderRadius.circular(16),
            ),
            child: message.pending
                ? const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : Text(message.text, style: theme.textTheme.bodyMedium),
          ),
          if (message.isAnswer) ...[
            if (message.showsDisclaimer) ...[
              Text(
                assistantDisclaimer,
                style: theme.textTheme.bodySmall?.copyWith(
                  color: theme.colorScheme.onSurfaceVariant,
                ),
              ),
              const SizedBox(height: 4),
            ],
            ActionChip(
              avatar: const Icon(Icons.people_outline, size: 18),
              label: const Text('Контакты деканата'),
              // go, не push: контакты — соседняя вкладка shell, push открыл бы
              // второй справочник поверх чата
              onPressed: () => context.go('/contacts'),
            ),
          ],
          const SizedBox(height: 12),
        ],
      ),
    );
  }
}

class _Composer extends StatelessWidget {
  const _Composer({
    required this.controller,
    required this.enabled,
    required this.onSubmit,
  });

  final TextEditingController controller;
  final bool enabled;
  final VoidCallback onSubmit;

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      top: false,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(12, 8, 12, 8),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Expanded(
              child: TextField(
                controller: controller,
                enabled: enabled,
                maxLength: _maxQuestionLength,
                maxLines: 4,
                minLines: 1,
                textInputAction: TextInputAction.send,
                onSubmitted: (_) => onSubmit(),
                decoration: const InputDecoration(
                  hintText: 'Ваш вопрос',
                  isDense: true,
                  counterText: '',
                  border: OutlineInputBorder(),
                ),
              ),
            ),
            const SizedBox(width: 8),
            IconButton.filled(
              icon: const Icon(Icons.send),
              tooltip: 'Отправить',
              onPressed: enabled ? onSubmit : null,
            ),
          ],
        ),
      ),
    );
  }
}
