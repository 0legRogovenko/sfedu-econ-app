import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/clock.dart';
import '../onboarding/group_repository.dart';
import '../schedule/schedule_providers.dart';
import '../schedule/schedule_repository.dart';
import '../schedule/schedule_widgets.dart';
import '../schedule/week_logic.dart';
import 'teacher.dart';

/// Расписание преподавателя. Отличий от экрана группы ровно два: данные берутся
/// из скоупа teacher, и карточка подписана ГРУППОЙ вместо преподавателя.
/// Фильтр «моя подгруппа» здесь НЕ применяется: он про свою группу студента,
/// а у преподавателя пары разных групп.
class TeacherScheduleScreen extends ConsumerStatefulWidget {
  const TeacherScheduleScreen({super.key, required this.teacher});

  final Teacher teacher;

  @override
  ConsumerState<TeacherScheduleScreen> createState() =>
      _TeacherScheduleScreenState();
}

class _TeacherScheduleScreenState extends ConsumerState<TeacherScheduleScreen> {
  late final PageController _pageController;
  late final DateTime _baseMonday;
  late int _dayIndex;

  @override
  void initState() {
    super.initState();
    final now = ref.read(clockProvider)();
    // Воскресенье: показываем следующую неделю — как на экране группы.
    final isSunday = now.weekday == DateTime.sunday;
    final monday = now.subtract(Duration(days: now.weekday - 1));
    _baseMonday = DateTime(monday.year, monday.month, monday.day)
        .add(Duration(days: isSunday ? 7 : 0));
    _dayIndex = isSunday ? 0 : now.weekday - 1;
    _pageController = PageController(initialPage: _dayIndex);
    Future.microtask(
        () => ref.read(teacherSyncProvider(widget.teacher.id).notifier).sync());
  }

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }

  DateTime _dateForIndex(int index) => _baseMonday.add(Duration(days: index));

  @override
  Widget build(BuildContext context) {
    final teacherId = widget.teacher.id;
    final scheduleAsync = ref.watch(teacherScheduleProvider(teacherId));
    final syncStatus = ref.watch(teacherSyncProvider(teacherId));
    // Справочник групп — для подписи карточек; офлайн-фолбэк даёт groupNameOf.
    final groups = ref.watch(groupsProvider).maybeWhen(
          data: (list) => list,
          orElse: () => const <Group>[],
        );
    final moduleName = scheduleAsync.maybeWhen(
      data: (data) =>
          activeModule(data.modules, _dateForIndex(_dayIndex))?.name,
      orElse: () => null,
    );
    final noData = syncStatus.lastResult == SyncResult.failed &&
        syncStatus.syncedAt == null &&
        scheduleAsync.maybeWhen(
          data: (data) => data.lessons.isEmpty,
          orElse: () => false,
        );
    final now = ref.read(clockProvider)();
    final nowWeekType = scheduleAsync.maybeWhen(
      data: (data) => weekTypeForDate(
          data.weekCalendar, DateTime(now.year, now.month, now.day)),
      orElse: () => null,
    );

    return Scaffold(
      appBar: AppBar(
        title: Text(widget.teacher.fullName),
        actions: [
          if (moduleName != null)
            Center(
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 12),
                child: Text(
                  moduleName,
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ),
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
                  onPressed: () => ref
                      .read(teacherSyncProvider(teacherId).notifier)
                      .sync(),
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
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (error, _) =>
                  const Center(child: Text('Не удалось открыть расписание')),
              data: (data) => PageView.builder(
                controller: _pageController,
                itemCount: 6,
                onPageChanged: (index) => setState(() => _dayIndex = index),
                itemBuilder: (context, index) => DayPage(
                  lessons: lessonsForDay(data, _dateForIndex(index)),
                  nowWeekType: nowWeekType,
                  noData: noData,
                  groupLabelOf: (lesson) => groupNameOf(groups, lesson.groupId),
                  onRefresh: () => ref
                      .read(teacherSyncProvider(teacherId).notifier)
                      .sync(),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
