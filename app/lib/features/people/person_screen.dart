import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:url_launcher/url_launcher.dart';

import 'person.dart';

/// Карточка человека: ПОЛНОЕ имя, должность(и), кафедра, почта и — если у
/// человека есть занятия — переход к его расписанию. У методистов деканата
/// расписания нет по должности, у них кнопки не будет.
class PersonScreen extends StatelessWidget {
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
  Widget build(BuildContext context) {
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
            OutlinedButton.icon(
              onPressed: () => _email(context),
              icon: const Icon(Icons.email_outlined),
              label: Text(person.email!),
            ),
          if (person.hasSchedule) ...[
            const SizedBox(height: 12),
            FilledButton.icon(
              onPressed: () =>
                  context.push('/people/schedule', extra: person),
              icon: const Icon(Icons.calendar_today_outlined),
              label: const Text('Расписание'),
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
