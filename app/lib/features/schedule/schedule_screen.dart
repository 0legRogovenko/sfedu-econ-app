import 'dart:async';

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
import 'semester.dart';
import 'muam_filter.dart';
import 'subgroup_filter.dart';
import 'week_logic.dart';

class ScheduleScreen extends ConsumerStatefulWidget {
  const ScheduleScreen({super.key});

  @override
  ConsumerState<ScheduleScreen> createState() => _ScheduleScreenState();
}

class _ScheduleScreenState extends ConsumerState<ScheduleScreen> {
  late final PageController _pageController;
  // Пересчитывается на каждый build от выбранного семестра, поэтому НЕ final.
  late DateTime _baseMonday;
  late int _dayIndex; // 0 = понедельник … 5 = суббота

  @override
  void initState() {
    super.initState();
    final now = ref.read(clockProvider)();
    _baseMonday = currentWeekMonday(now);
    _dayIndex = now.weekday == DateTime.sunday ? 0 : now.weekday - 1;
    _pageController = PageController(initialPage: _dayIndex);
    // Серверный импорт может пересоздать группы с другими id. Сверяем
    // SharedPreferences с живым справочником до показа переключателя.
    ref.listenManual(groupsProvider, (_, next) {
      next.whenData((groups) {
        unawaited(
          ref.read(favoriteGroupIdsProvider.notifier).reconcile([
            for (final group in groups) group.id,
          ]),
        );
      });
    }, fireImmediately: true);
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

  /// Выбор семестра из меню кнопки. Пишет ключ в общий провайдер — то же
  /// значение читает расписание преподавателя, поэтому оно открывается на том
  /// же семестре.
  void _selectSemester(Semester semester, Semester current) {
    if (semester.seasonKey == current.seasonKey) return; // тот же — ничего
    ref.read(viewedSemesterProvider.notifier).select(semester.seasonKey);
    // Возврат к понедельнику: у не текущего семестра осмысленна первая неделя
    // целиком, а сегодняшний день недели там ни при чём.
    setState(() => _dayIndex = 0);
    if (_pageController.hasClients) _pageController.jumpToPage(0);
  }

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
    final now = ref.read(clockProvider)();

    // Семестры из данных расписания; переключатель — только если их больше
    // одного. Выбранный семестр (общий с расписанием преподавателя) задаёт,
    // какую неделю показываем.
    final semesters = scheduleAsync.maybeWhen(
      data: detectSemesters,
      orElse: () => const <Semester>[],
    );
    final chosenKey = ref.watch(viewedSemesterProvider);
    final selectedSemester = resolveSemester(semesters, chosenKey, now);
    _baseMonday = mondayForSemester(selectedSemester, now);

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
    final noData =
        syncStatus.lastResult == SyncResult.failed &&
        syncStatus.syncedAt == null &&
        scheduleAsync.maybeWhen(
          data: (data) => data.lessons.isEmpty,
          orElse: () => false,
        );
    // Фильтр «моя подгруппа» активной группы; null — показывать все пары.
    final subgroup = ref.watch(activeSubgroupProvider);
    final muamSubject = ref.watch(activeMuamSubjectProvider);
    final nowWeekType = scheduleAsync.maybeWhen(
      data: (data) => weekTypeForDate(
        data.weekCalendar,
        DateTime(now.year, now.month, now.day),
      ),
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
          // Кнопка выбора семестра — на месте прежнего бейджа недели. Показана,
          // только когда семестров больше одного (у группы обычно осенний и
          // весенний).
          if (semesters.length >= 2 && selectedSemester != null)
            SemesterButton(
              semesters: semesters,
              selected: selectedSemester,
              onSelect: (semester) =>
                  _selectSemester(semester, selectedSemester),
            ),
          IconButton(
            icon: const Icon(Icons.person_search_outlined),
            tooltip: 'Расписание преподавателя',
            onPressed: () => context.push('/people'),
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
                  onPressed: () => ref.read(syncStatusProvider.notifier).sync(),
                  child: const Text('Обновить'),
                ),
              ],
            ),
          // Межсезонье: семестры в данных есть, но сегодня не входит ни в один
          // (лето, зимние каникулы) — показана первая неделя выбранного
          // семестра, и об этом говорим явно.
          if (selectedSemester != null &&
              !semesters.any((s) => s.contains(now)))
            VacationBanner(semester: selectedSemester),
          DayStrip(
            selected: _dayIndex,
            onSelect: (index) {
              setState(() => _dayIndex = index);
              // Полоса дней вне scheduleAsync.when — она доступна и в loading,
              // когда PageView ещё не построен (см. тот же комментарий в
              // экране преподавателя). Здесь тёплый кэш обычно маскирует
              // проблему, но на первом запуске окно такое же.
              if (_pageController.hasClients) {
                _pageController.animateToPage(
                  index,
                  duration: const Duration(milliseconds: 250),
                  curve: Curves.easeOut,
                );
              }
            },
          ),
          Expanded(
            child: scheduleAsync.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (error, _) =>
                  const Center(child: Text('Не удалось открыть расписание')),
              data: (data) => PageView.builder(
                controller: _pageController,
                itemCount: 6,
                onPageChanged: (index) => setState(() => _dayIndex = index),
                itemBuilder: (context, index) => DayPage(
                  lessons: lessonsForDay(
                    data,
                    _dateForIndex(index),
                    subgroup: subgroup,
                    muamSubject: muamSubject,
                  ),
                  nowWeekType: nowWeekType,
                  noData: noData,
                  onRefresh: () => ref.read(syncStatusProvider.notifier).sync(),
                  selectedMuamSubject: muamSubject,
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
    final storedFavorites = ref.watch(favoriteGroupIdsProvider);
    // Справочник имён; при устаревшем id не показываем внутренний ключ БД.
    final groups = ref
        .watch(groupsProvider)
        .maybeWhen(data: (list) => list, orElse: () => const <Group>[]);
    final validIds = groups.map((group) => group.id).toSet();
    final favorites = storedFavorites.where(validIds.contains).toList();
    if (groupId == null) return const Text('Расписание');
    final title = Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Flexible(
          child: Text(
            groupNameOf(groups, groupId),
            overflow: TextOverflow.ellipsis,
          ),
        ),
        if (favorites.isNotEmpty) const Icon(Icons.arrow_drop_down),
      ],
    );
    if (favorites.isEmpty) return title;
    return PopupMenuButton<int>(
      tooltip: 'Избранные группы',
      onSelected: (id) => ref.read(selectedGroupIdProvider.notifier).select(id),
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
