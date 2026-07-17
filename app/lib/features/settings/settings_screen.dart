import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/theme_mode.dart';
import '../onboarding/group_picker.dart';
import '../onboarding/group_repository.dart';
import '../onboarding/selected_group.dart';

class SettingsScreen extends ConsumerWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final groupsAsync = ref.watch(groupsProvider);
    final selectedGroupId = ref.watch(selectedGroupIdProvider);
    final themeMode = ref.watch(themeModeProvider);
    final theme = Theme.of(context);

    return Scaffold(
      // Экран открывается через context.push — стандартная кнопка «назад»
      // и аппаратная «назад» работают сами (итог ревью)
      appBar: AppBar(title: const Text('Настройки')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text('Группа', style: theme.textTheme.titleMedium),
          const SizedBox(height: 8),
          groupsAsync.when(
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (error, _) =>
                const Text('Не удалось загрузить список групп'),
            data: (groups) {
              Group? currentGroup;
              for (final g in groups) {
                if (g.id == selectedGroupId) currentGroup = g;
              }
              return Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Текущая группа: ${currentGroup?.displayName ?? '—'}'),
                  const SizedBox(height: 8),
                  GroupPicker(
                    groups: groups,
                    initialSelectedId: selectedGroupId,
                    // Смена уровня/курса шлёт null — сохраняем группу только
                    // при выборе конечного чипа, иначе стёрли бы текущий выбор.
                    onSelected: (group) {
                      if (group != null) {
                        ref
                            .read(selectedGroupIdProvider.notifier)
                            .select(group.id);
                      }
                    },
                  ),
                ],
              );
            },
          ),
          const SizedBox(height: 24),
          Text('Тема', style: theme.textTheme.titleMedium),
          RadioGroup<ThemeMode>(
            groupValue: themeMode,
            onChanged: (mode) =>
                ref.read(themeModeProvider.notifier).set(mode!),
            child: const Column(
              children: [
                RadioListTile<ThemeMode>(
                  title: Text('Системная'),
                  value: ThemeMode.system,
                ),
                RadioListTile<ThemeMode>(
                  title: Text('Светлая'),
                  value: ThemeMode.light,
                ),
                RadioListTile<ThemeMode>(
                  title: Text('Тёмная'),
                  value: ThemeMode.dark,
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),
          Text('О приложении', style: theme.textTheme.titleMedium),
          const SizedBox(height: 8),
          const Text('Эконом ЮФУ'),
          const SizedBox(height: 4),
          const Text(
            'Расписание, новости и контакты экономического факультета '
            'ЮФУ в одном приложении.',
          ),
          const SizedBox(height: 8),
          const Text(
            'Неофициальное приложение, сделано студентом. '
            'Данные берутся с sfedu.ru.',
          ),
          const SizedBox(height: 8),
          OutlinedButton.icon(
            onPressed: () => launchUrl(
              Uri.parse('https://sfedu.ru'),
              mode: LaunchMode.externalApplication,
            ),
            icon: const Icon(Icons.open_in_new),
            label: const Text('sfedu.ru'),
          ),
        ],
      ),
    );
  }
}
