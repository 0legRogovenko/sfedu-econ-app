import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/clock.dart';
import '../../core/room_format.dart';
import 'exam_event.dart';
import 'exams_logic.dart';
import 'exams_providers.dart';
import 'exams_repository.dart';

class ExamsScreen extends ConsumerWidget {
  const ExamsScreen({super.key});

  /// Офлайн-первый: пока в кэше что-то есть — показываем его, даже если
  /// последний ответ сервера был ошибкой. Экран ошибки — только когда
  /// показать нечего (как в контактах).
  Widget _body(BuildContext context, WidgetRef ref, AsyncValue<ExamsFeed> feed) {
    final now = ref.watch(clockProvider)();
    Widget list(ExamsFeed f) => _ExamsList(
          feed: f,
          now: now,
          onRefresh: () => ref.read(examsFeedProvider.notifier).refresh(),
        );

    final cached = feed.value;
    if (cached != null && cached.items.isNotEmpty) return list(cached);

    return feed.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (error, _) =>
          const Center(child: Text('Не удалось загрузить экзамены')),
      data: list,
    );
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final feed = ref.watch(examsFeedProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('Экзамены')),
      body: _body(context, ref, feed),
    );
  }
}

class _ExamsList extends StatelessWidget {
  const _ExamsList({
    required this.feed,
    required this.now,
    required this.onRefresh,
  });

  final ExamsFeed feed;
  final DateTime now;
  final Future<void> Function() onRefresh;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final split = splitExams(feed.items, now);

    final Widget listBody;
    if (feed.items.isEmpty) {
      listBody = ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        children: const [
          SizedBox(height: 300, child: Center(child: Text('Экзамены не назначены'))),
        ],
      );
    } else {
      listBody = ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(12),
        children: [
          for (final exam in split.upcoming) ...[
            _ExamCard(exam: exam),
            const SizedBox(height: 8),
          ],
          if (split.past.isNotEmpty) ...[
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 8),
              child: Text(
                'Прошедшие',
                style: theme.textTheme.titleSmall?.copyWith(
                  color: theme.colorScheme.outline,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
            for (final exam in split.past) ...[
              _ExamCard(exam: exam, past: true),
              const SizedBox(height: 8),
            ],
          ],
        ],
      );
    }

    return Column(
      children: [
        if (feed.offline)
          MaterialBanner(
            content: const Text('Нет сети. Показаны сохранённые экзамены'),
            actions: [
              TextButton(onPressed: onRefresh, child: const Text('Обновить')),
            ],
          ),
        Expanded(
          child: RefreshIndicator(onRefresh: onRefresh, child: listBody),
        ),
      ],
    );
  }
}

class _ExamCard extends StatelessWidget {
  const _ExamCard({required this.exam, this.past = false});

  final ExamEvent exam;
  final bool past;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    // Приглушаем прошедшие, но не прячем — «уточняется» вместо пустот.
    final color = past ? theme.disabledColor : null;

    Widget row(IconData icon, String label, String value) => Padding(
          padding: const EdgeInsets.only(top: 4),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(icon, size: 16, color: color ?? theme.colorScheme.outline),
              const SizedBox(width: 6),
              Expanded(
                child: Text.rich(
                  TextSpan(children: [
                    TextSpan(
                      text: '$label: ',
                      style: theme.textTheme.bodySmall?.copyWith(color: color),
                    ),
                    TextSpan(
                      text: value,
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: color,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ]),
                ),
              ),
            ],
          ),
        );

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              exam.subject,
              style: theme.textTheme.titleMedium?.copyWith(color: color),
            ),
            const SizedBox(height: 2),
            Text(
              exam.teacher ?? 'Преподаватель уточняется',
              style: theme.textTheme.bodySmall?.copyWith(color: color),
            ),
            const SizedBox(height: 6),
            row(Icons.school_outlined, 'Экзамен',
                formatExamDateTime(exam.examAt)),
            row(Icons.co_present_outlined, 'Консультация',
                formatExamDateTime(exam.consultationAt)),
            row(Icons.meeting_room_outlined, 'Аудитория',
                exam.room == null ? 'уточняется' : formatRoom(exam.room!)),
            row(Icons.assignment_outlined, 'Форма', exam.kind ?? 'уточняется'),
          ],
        ),
      ),
    );
  }
}
