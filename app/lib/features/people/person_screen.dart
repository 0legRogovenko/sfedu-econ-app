import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/room_format.dart';
import '../contacts/email_copy_region.dart';
import '../exams/exams_logic.dart';
import 'people_providers.dart';
import 'person.dart';

/// Карточка человека: ПОЛНОЕ имя, должность(и), кафедра, почта и — если у
/// человека есть занятия — переход к его расписанию. У методистов деканата
/// расписания нет по должности, у них кнопки не будет.
class PersonScreen extends ConsumerWidget {
  const PersonScreen({super.key, required this.person});

  final Person person;

  Future<void> _email(BuildContext context) async {
    final address = person.email;
    if (address == null) return;
    try {
      final ok = await launchUrl(
        Uri.parse('mailto:$address'),
        mode: LaunchMode.externalApplication,
      );
      if (!ok && context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Не удалось открыть почту')),
        );
      }
    } catch (_) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Не удалось открыть почту')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    // Должность и кафедра в одну строку: у человека с двумя ролями (деканат +
    // кафедра) показываем обе.
    final subtitle = {...person.roles, ...person.sections}.join(' · ');

    return Scaffold(
      appBar: AppBar(title: Text(person.shortName)),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text(person.fullName, style: theme.textTheme.headlineSmall),
          if (subtitle.isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(subtitle, style: theme.textTheme.bodyMedium),
          ],
          const SizedBox(height: 24),
          if (person.email != null)
            EmailCopyRegion(
              email: person.email!,
              child: OutlinedButton.icon(
                onPressed: () => _email(context),
                icon: const Icon(Icons.email_outlined),
                label: Text(person.email!),
              ),
            ),
          if (person.hasSchedule) ...[
            const SizedBox(height: 12),
            FilledButton.icon(
              onPressed: () => context.push('/people/schedule', extra: person),
              icon: const Icon(Icons.calendar_today_outlined),
              label: const Text('Расписание'),
            ),
          ],
          // Экзамены человека: есть у преподавателей из файлов сессий.
          if (person.examCount > 0) ...[
            const SizedBox(height: 24),
            Text('Экзамены', style: theme.textTheme.titleMedium),
            const SizedBox(height: 8),
            ref
                .watch(personExamsProvider(person.id))
                .when(
                  loading: () =>
                      const Center(child: CircularProgressIndicator()),
                  error: (error, _) => Text(
                    'Не удалось загрузить экзамены. Нужна сеть',
                    style: theme.textTheme.bodySmall,
                  ),
                  data: (exams) => Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      for (final exam in exams)
                        Padding(
                          padding: const EdgeInsets.only(bottom: 8),
                          child: Card(
                            child: Padding(
                              padding: const EdgeInsets.all(12),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    exam.subject,
                                    style: theme.textTheme.titleSmall,
                                  ),
                                  const SizedBox(height: 4),
                                  Text(
                                    [
                                      'Экзамен: '
                                          '${formatExamDateTime(exam.examAt)}',
                                      if (exam.room != null)
                                        formatRoom(exam.room!),
                                    ].join(' · '),
                                    style: theme.textTheme.bodySmall,
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ),
                    ],
                  ),
                ),
          ],
          if (person.email == null && !person.hasSchedule) ...[
            const SizedBox(height: 8),
            Text(
              'Контактных данных и расписания пока нет.',
              style: theme.textTheme.bodySmall,
            ),
          ],
        ],
      ),
    );
  }
}
