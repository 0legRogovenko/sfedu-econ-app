import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/device_id.dart';
import '../../core/theme_mode.dart';
import '../assistant/assistant_providers.dart';
import '../onboarding/favorite_groups.dart';
import '../onboarding/group_picker.dart';
import '../onboarding/group_repository.dart';
import '../onboarding/selected_group.dart';
import '../schedule/schedule_providers.dart';
import '../schedule/subgroup_filter.dart';

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
          Text('Избранные группы', style: theme.textTheme.titleMedium),
          const SizedBox(height: 8),
          // Пустой справочник, а не пустая секция: офлайн заголовок «Избранные
          // группы» висел бы над пустотой, и убрать избранную было бы нельзя.
          // Имена подставит groupNameOf («Группа N»), как в заголовке
          // расписания.
          _FavoriteGroupsSection(
            groups: groupsAsync.maybeWhen(
              data: (groups) => groups,
              orElse: () => const <Group>[],
            ),
          ),
          const SizedBox(height: 24),
          Text('Моя подгруппа', style: theme.textTheme.titleMedium),
          const SizedBox(height: 8),
          const _SubgroupSection(),
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
            onPressed: () => _openSite(context, 'https://sfedu.ru'),
            icon: const Icon(Icons.open_in_new),
            label: const Text('sfedu.ru'),
          ),
          const SizedBox(height: 8),
          // Канал обратной связи: неверное расписание, битые данные, идеи.
          OutlinedButton.icon(
            onPressed: () => _reportProblem(context),
            icon: const Icon(Icons.bug_report_outlined),
            label: const Text('Сообщить об ошибке'),
          ),
          const SizedBox(height: 24),
          Text('Данные и приватность', style: theme.textTheme.titleMedium),
          const SizedBox(height: 8),
          const Text(
            'На сервере хранятся только обезличенные обращения к помощнику '
            '(для ограничения числа запросов). Их можно удалить. Настройки на '
            'телефоне (группа, тема, избранное) хранятся локально.',
          ),
          const SizedBox(height: 8),
          OutlinedButton.icon(
            onPressed: () => _deleteMyData(context, ref),
            icon: const Icon(Icons.delete_outline),
            label: const Text('Удалить мои данные'),
          ),
        ],
      ),
    );
  }
}

/// «Удалить мои данные»: сносит с сервера логи помощника этого устройства.
/// Спрашивает подтверждение и честно сообщает результат.
Future<void> _deleteMyData(BuildContext context, WidgetRef ref) async {
  final confirmed = await showDialog<bool>(
    context: context,
    builder: (ctx) => AlertDialog(
      title: const Text('Удалить мои данные?'),
      content: const Text(
        'С сервера будут удалены сохранённые обращения к помощнику с этого '
        'устройства. Настройки на телефоне не затрагиваются.',
      ),
      actions: [
        TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Отмена')),
        TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Удалить')),
      ],
    ),
  );
  if (confirmed != true || !context.mounted) return;

  final ok = await ref
      .read(assistantApiProvider)
      .forget(ref.read(deviceIdProvider));
  if (!context.mounted) return;
  ScaffoldMessenger.of(context).showSnackBar(
    SnackBar(
      content: Text(ok ? 'Данные удалены' : 'Не удалось удалить. Нужна сеть'),
    ),
  );
}

/// Открывает ссылку в браузере; если не вышло — говорит об этом через SnackBar,
/// а не падает молча (как _openSite в детальном экране новостей).
Future<void> _openSite(BuildContext context, String url) async {
  const failure = 'Не удалось открыть браузер';
  try {
    final ok = await launchUrl(
      Uri.parse(url),
      mode: LaunchMode.externalApplication,
    );
    if (!ok && context.mounted) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text(failure)));
    }
  } catch (_) {
    if (context.mounted) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text(failure)));
    }
  }
}

/// Письмо разработчику: тема подставлена, чтобы фидбек не терялся в почте.
Future<void> _reportProblem(BuildContext context) async {
  const failure = 'Не удалось открыть почту';
  final uri = Uri(
    scheme: 'mailto',
    path: '080806oleg@gmail.com',
    query: 'subject=Эконом ЮФУ: ошибка или предложение',
  );
  try {
    final ok = await launchUrl(uri, mode: LaunchMode.externalApplication);
    if (!ok && context.mounted) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text(failure)));
    }
  } catch (_) {
    if (context.mounted) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text(failure)));
    }
  }
}

/// Выбор подгруппы для АКТИВНОЙ группы: «Все» снимает фильтр. Хранится по
/// группам, поэтому переключение активной показывает её собственный выбор.
class _SubgroupSection extends ConsumerWidget {
  const _SubgroupSection();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final groupId = ref.watch(selectedGroupIdProvider);
    final current = ref.watch(activeSubgroupProvider);
    if (groupId == null) return const Text('Сначала выберите группу');

    // Число подгрупп считаем ПО САМИМ ПАРАМ, а не по Group.subgroupCount:
    // поле группы импорт не заполняет (в живой базе оно равно 1 у всех 40
    // групп, при том что у трёх есть пары второй подгруппы), и опора на него
    // отняла бы у этих студентов выбор своей подгруппы. Жёсткие «1 и 2» тоже
    // не годятся: разбиение приходит из файла ЮФУ и двумя не ограничено.
    final count = ref
        .watch(scheduleDataProvider)
        .maybeWhen(
          data: (data) => data.lessons.fold<int>(
            0,
            (max, l) => l.subgroup > max ? l.subgroup : max,
          ),
          orElse: () => 0,
        );

    // Ноль — у группы нет ни одной пары по подгруппам. Показывать фильтр,
    // который ничего не изменит, значит обещать несуществующую настройку.
    if (count == 0) {
      return const Text(
        'У вашей группы нет занятий по подгруппам — фильтровать нечего.',
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Пары всей группы показываются всегда — фильтр прячет только '
          'занятия чужой подгруппы.',
        ),
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          children: [
            for (final (value, label) in [
              (null, 'Все'),
              for (var i = 1; i <= count; i++) (i, '$i-я'),
            ])
              ChoiceChip(
                label: Text(label),
                selected: current == value,
                // Повторный тап по выбранному чипу шлёт selected: false —
                // тогда ничего не меняем, иначе выбор нельзя было бы вернуть.
                onSelected: (selected) {
                  if (!selected) return;
                  ref
                      .read(subgroupFiltersProvider.notifier)
                      .set(groupId, value);
                },
              ),
          ],
        ),
      ],
    );
  }
}

/// Список избранных групп: тап делает активной, корзина удаляет (семантика
/// удаления — в FavoriteGroupIds: активная переключается на первую оставшуюся).
class _FavoriteGroupsSection extends ConsumerWidget {
  const _FavoriteGroupsSection({required this.groups});

  final List<Group> groups;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final validIds = groups.map((group) => group.id).toSet();
    final favorites = ref
        .watch(favoriteGroupIdsProvider)
        .where(validIds.contains)
        .toList();
    final selectedId = ref.watch(selectedGroupIdProvider);
    final selectedExists = selectedId != null && validIds.contains(selectedId);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (favorites.isEmpty) const Text('Избранных групп пока нет'),
        for (final id in favorites)
          ListTile(
            contentPadding: EdgeInsets.zero,
            leading: id == selectedId
                ? const Icon(Icons.check)
                : const SizedBox(width: 24),
            title: Text(groupNameOf(groups, id)),
            trailing: IconButton(
              icon: const Icon(Icons.delete_outline),
              tooltip: 'Удалить из избранных',
              onPressed: () =>
                  ref.read(favoriteGroupIdsProvider.notifier).remove(id),
            ),
            onTap: () => ref.read(selectedGroupIdProvider.notifier).select(id),
          ),
        // Активная группа не обязана быть избранной (пикер выше выбирает
        // любую) — кнопка появляется, когда текущей нет в списке.
        if (selectedExists && !favorites.contains(selectedId)) ...[
          const SizedBox(height: 8),
          OutlinedButton.icon(
            onPressed: () =>
                ref.read(favoriteGroupIdsProvider.notifier).add(selectedId),
            icon: const Icon(Icons.star_border),
            label: const Text('Добавить текущую в избранные'),
          ),
        ],
      ],
    );
  }
}
