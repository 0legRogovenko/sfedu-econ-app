import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/clock.dart';
import 'lesson.dart';
import 'schedule_providers.dart';
import 'schedule_repository.dart';
import 'week_logic.dart';

const _weekdayShort = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб'];

class ScheduleScreen extends ConsumerStatefulWidget {
  const ScheduleScreen({super.key});

  @override
  ConsumerState<ScheduleScreen> createState() => _ScheduleScreenState();
}

class _ScheduleScreenState extends ConsumerState<ScheduleScreen> {
  late final PageController _pageController;
  late int _dayIndex; // 0 = понедельник … 5 = суббота

  @override
  void initState() {
    super.initState();
    final now = ref.read(clockProvider)();
    // воскресенье показываем как понедельник следующей недели
    _dayIndex = (now.weekday - 1).clamp(0, 5);
    _pageController = PageController(initialPage: _dayIndex);
    // фоновая синхронизация при открытии экрана
    Future.microtask(() => ref.read(syncStatusProvider.notifier).sync());
  }

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }

  /// Дата, соответствующая выбранному дню текущей недели.
  DateTime _dateForIndex(int index) {
    final now = ref.read(clockProvider)();
    final monday = now.subtract(Duration(days: now.weekday - 1));
    return DateTime(monday.year, monday.month, monday.day)
        .add(Duration(days: index));
  }

  @override
  Widget build(BuildContext context) {
    final lessonsAsync = ref.watch(lessonsProvider);
    final syncStatus = ref.watch(syncStatusProvider);
    final weekType = weekTypeForDate(_dateForIndex(_dayIndex));

    return Scaffold(
      appBar: AppBar(
        title: const Text('Расписание'),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 16),
            child: Center(
              child: Text(
                weekType == WeekType.numerator ? 'числитель' : 'знаменатель',
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
                '${_formatDate(syncStatus.syncedAt!)}',
              ),
              actions: [
                TextButton(
                  onPressed: () =>
                      ref.read(syncStatusProvider.notifier).sync(),
                  child: const Text('Обновить'),
                ),
              ],
            ),
          _DayStrip(
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
            child: lessonsAsync.when(
              loading: () =>
                  const Center(child: CircularProgressIndicator()),
              error: (error, _) =>
                  const Center(child: Text('Не удалось открыть расписание')),
              data: (lessons) => PageView.builder(
                controller: _pageController,
                itemCount: 6,
                onPageChanged: (index) =>
                    setState(() => _dayIndex = index),
                itemBuilder: (context, index) => _DayPage(
                  lessons: lessonsForDay(lessons, _dateForIndex(index)),
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

String _formatDate(DateTime date) =>
    '${date.day.toString().padLeft(2, '0')}.'
    '${date.month.toString().padLeft(2, '0')}.${date.year}';

class _DayStrip extends StatelessWidget {
  const _DayStrip({required this.selected, required this.onSelect});

  final int selected;
  final ValueChanged<int> onSelect;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          for (var i = 0; i < 6; i++)
            ChoiceChip(
              label: Text(_weekdayShort[i]),
              selected: selected == i,
              selectedColor: scheme.primary,
              labelStyle: TextStyle(
                color: selected == i ? scheme.onPrimary : null,
              ),
              onSelected: (_) => onSelect(i),
            ),
        ],
      ),
    );
  }
}

class _DayPage extends ConsumerWidget {
  const _DayPage({required this.lessons, required this.onRefresh});

  final List<Lesson> lessons;
  final Future<void> Function() onRefresh;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final now = ref.watch(clockProvider)();

    return RefreshIndicator(
      onRefresh: onRefresh,
      child: lessons.isEmpty
          ? ListView(
              children: const [
                SizedBox(height: 120),
                Center(child: Text('Пар нет — отдыхаем')),
              ],
            )
          : ListView.separated(
              padding: const EdgeInsets.all(12),
              itemCount: lessons.length,
              separatorBuilder: (_, _) => const SizedBox(height: 8),
              itemBuilder: (context, index) => _LessonCard(
                lesson: lessons[index],
                isNow: isLessonNow(lessons[index], now),
              ),
            ),
    );
  }
}

class _LessonCard extends StatelessWidget {
  const _LessonCard({required this.lesson, required this.isNow});

  final Lesson lesson;
  final bool isNow;

  String _hhmm(String hhmmss) => hhmmss.substring(0, 5);

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final details = [
      if (lesson.room != null) 'ауд. ${lesson.room}',
      if (lesson.teacherName != null) lesson.teacherName!,
      if (lesson.subgroup != 0) '${lesson.subgroup}-я подгруппа',
    ].join(' · ');

    return Card(
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: isNow
            ? BorderSide(color: scheme.primary, width: 2)
            : BorderSide.none,
      ),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Text(
                  '${_hhmm(lesson.startsAt)}–${_hhmm(lesson.endsAt)}',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
                const Spacer(),
                if (isNow)
                  Container(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 8, vertical: 2),
                    decoration: BoxDecoration(
                      color: scheme.primary,
                      borderRadius: BorderRadius.circular(999),
                    ),
                    child: Text(
                      'Сейчас',
                      style: TextStyle(color: scheme.onPrimary, fontSize: 12),
                    ),
                  ),
              ],
            ),
            const SizedBox(height: 4),
            Text(lesson.subject,
                style: Theme.of(context).textTheme.titleMedium),
            if (details.isNotEmpty) ...[
              const SizedBox(height: 2),
              Text(details, style: Theme.of(context).textTheme.bodySmall),
            ],
          ],
        ),
      ),
    );
  }
}
