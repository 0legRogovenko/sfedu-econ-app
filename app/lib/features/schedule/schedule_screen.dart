import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/clock.dart';
import '../onboarding/favorite_groups.dart';
import '../onboarding/group_repository.dart';
import '../onboarding/selected_group.dart';
import 'schedule_providers.dart';
import 'schedule_repository.dart';
import 'schedule_widgets.dart';
import 'subgroup_filter.dart';
import 'week_logic.dart';

class ScheduleScreen extends ConsumerStatefulWidget {
  const ScheduleScreen({super.key});

  @override
  ConsumerState<ScheduleScreen> createState() => _ScheduleScreenState();
}

class _ScheduleScreenState extends ConsumerState<ScheduleScreen> {
  late final PageController _pageController;
  late final DateTime _baseMonday;
  late int _dayIndex; // 0 = понедельник … 5 = суббота

  @override
  void initState() {
    super.initState();
    final now = ref.read(clockProvider)();
    // Воскресенье: показываем следующую неделю с понедельника —
    // студент планирует предстоящие пары
    final isSunday = now.weekday == DateTime.sunday;
    final monday = now.subtract(Duration(days: now.weekday - 1));
    _baseMonday = DateTime(monday.year, monday.month, monday.day)
        .add(Duration(days: isSunday ? 7 : 0));
    _dayIndex = isSunday ? 0 : now.weekday - 1;
    _pageController = PageController(initialPage: _dayIndex);
    // фоновая синхронизация при открытии экрана
    Future.microtask(() => ref.read(syncStatusProvider.notifier).sync());
  }

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }

  /// Дата, соответствующая выбранному дню отображаемой недели.
  DateTime _dateForIndex(int index) => _baseMonday.add(Duration(days: index));

  @override
  Widget build(BuildContext context) {
    // Смена группы в настройках должна подтягивать её расписание: initState
    // здесь больше не отрабатывает (экран не пересоздаётся при push/pop),
    // поэтому синкаем по изменению выбранной группы (итог ревью).
    ref.listen<int?>(selectedGroupIdProvider, (previous, next) {
      if (previous != next && next != null) {
        ref.read(syncStatusProvider.notifier).sync();
      }
    });

    final scheduleAsync = ref.watch(scheduleDataProvider);
    final syncStatus = ref.watch(syncStatusProvider);
    // Тип недели выбранного дня — из календаря сервера (не формула).
    final weekType = scheduleAsync.maybeWhen(
      data: (data) =>
          weekTypeForDate(data.weekCalendar, _dateForIndex(_dayIndex)),
      orElse: () => null,
    );
    // Активный модуль выбранного дня (модуль, чей диапазон накрывает дату).
    // null — дата вне всех модулей ИЛИ у модуля нет имени → бейдж скрыт.
    final moduleName = scheduleAsync.maybeWhen(
      data: (data) =>
          activeModule(data.modules, _dateForIndex(_dayIndex))?.name,
      orElse: () => null,
    );
    // Первый офлайн-запуск: кэш пуст И первый синк упал (syncedAt == null).
    // Отличаем «данные не загружены» от «пар правда нет» — иначе показали бы
    // «Пар нет — отдыхаем», и студент решит, что занятий нет.
    final noData = syncStatus.lastResult == SyncResult.failed &&
        syncStatus.syncedAt == null &&
        scheduleAsync.maybeWhen(
          data: (data) => data.lessons.isEmpty,
          orElse: () => false,
        );
    // Фильтр «моя подгруппа» активной группы; null — показывать все пары.
    final subgroup = ref.watch(activeSubgroupProvider);
    final now = ref.read(clockProvider)();
    final nowWeekType = scheduleAsync.maybeWhen(
      data: (data) => weekTypeForDate(
          data.weekCalendar, DateTime(now.year, now.month, now.day)),
      orElse: () => null,
    );

    return Scaffold(
      appBar: AppBar(
        title: const _GroupSwitcherTitle(),
        actions: [
          // Бейдж активного модуля выбранного дня. Скрыт, если дата вне всех
          // модулей (или у модуля нет имени), — как и бейдж недели.
          if (moduleName != null)
            Padding(
              padding: const EdgeInsets.only(right: 8),
              child: Center(
                child: Text(
                  moduleName,
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ),
            ),
          // Бейдж типа недели («верхняя»/«нижняя») — термины ЮФУ. Если дата вне
          // календаря, тип неизвестен — бейдж не показываем.
          if (weekType != null)
            Padding(
              padding: const EdgeInsets.only(right: 8),
              child: Center(
                child: Text(
                  weekType.label,
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ),
            ),
          IconButton(
            icon: const Icon(Icons.person_search_outlined),
            tooltip: 'Расписание преподавателя',
            onPressed: () => context.push('/teachers'),
          ),
          IconButton(
            icon: const Icon(Icons.event_note_outlined),
            tooltip: 'Экзамены',
            // push, не go: аппаратная «назад» вернёт на расписание, а не
            // закроет приложение (как контакты открывают настройки).
            onPressed: () => context.push('/exams'),
          ),
        ],
      ),
      body: Column(
        children: [
          if (syncStatus.lastResult == SyncResult.failed &&
              syncStatus.syncedAt != null)
            MaterialBanner(
              content: Text(
                'Нет сети. Данные от '
                '${formatScheduleDate(syncStatus.syncedAt!)}',
              ),
              actions: [
                TextButton(
                  onPressed: () =>
                      ref.read(syncStatusProvider.notifier).sync(),
                  child: const Text('Обновить'),
                ),
              ],
            ),
          DayStrip(
            selected: _dayIndex,
            onSelect: (index) {
              setState(() => _dayIndex = index);
              _pageController.animateToPage(
                index,
                duration: const Duration(milliseconds: 250),
                curve: Curves.easeOut,
              );
            },
          ),
          Expanded(
            child: scheduleAsync.when(
              loading: () =>
                  const Center(child: CircularProgressIndicator()),
              error: (error, _) =>
                  const Center(child: Text('Не удалось открыть расписание')),
              data: (data) => PageView.builder(
                controller: _pageController,
                itemCount: 6,
                onPageChanged: (index) =>
                    setState(() => _dayIndex = index),
                itemBuilder: (context, index) => DayPage(
                  lessons: lessonsForDay(data, _dateForIndex(index),
                      subgroup: subgroup),
                  nowWeekType: nowWeekType,
                  noData: noData,
                  onRefresh: () =>
                      ref.read(syncStatusProvider.notifier).sync(),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// Заголовок-переключатель: имя активной группы, тап открывает меню избранных.
/// Смена активной — ТОЛЬКО через selectedGroupIdProvider.select(): ref.listen
/// в build экрана сам запустит синхронизацию новой группы.
class _GroupSwitcherTitle extends ConsumerWidget {
  const _GroupSwitcherTitle();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final groupId = ref.watch(selectedGroupIdProvider);
    final favorites = ref.watch(favoriteGroupIdsProvider);
    // Справочник имён; офлайн-фолбэк «Группа N» даёт groupNameOf.
    final groups = ref.watch(groupsProvider).maybeWhen(
          data: (list) => list,
          orElse: () => const <Group>[],
        );
    if (groupId == null) return const Text('Расписание');
    final title = Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Flexible(
          child: Text(groupNameOf(groups, groupId),
              overflow: TextOverflow.ellipsis),
        ),
        if (favorites.isNotEmpty) const Icon(Icons.arrow_drop_down),
      ],
    );
    if (favorites.isEmpty) return title;
    return PopupMenuButton<int>(
      tooltip: 'Избранные группы',
      onSelected: (id) =>
          ref.read(selectedGroupIdProvider.notifier).select(id),
      itemBuilder: (context) => [
        for (final id in favorites)
          PopupMenuItem(
            value: id,
            child: Row(
              children: [
                if (id == groupId)
                  const Icon(Icons.check, size: 18)
                else
                  const SizedBox(width: 18),
                const SizedBox(width: 8),
                Text(groupNameOf(groups, id)),
              ],
            ),
          ),
      ],
      child: title,
    );
  }
}
