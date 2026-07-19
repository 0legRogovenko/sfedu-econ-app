import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/clock.dart';
import '../../core/room_format.dart';
import 'lesson.dart';
import 'week_logic.dart';

/// Общие виджеты недели: их делят экран расписания группы и экран расписания
/// преподавателя. Единственное отличие режимов — подпись карточки, и она
/// вынесена в параметр [DayPage.groupLabelOf], а не в копию виджета.

const weekdayShort = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб'];

String formatScheduleDate(DateTime date) =>
    '${date.day.toString().padLeft(2, '0')}.'
    '${date.month.toString().padLeft(2, '0')}.${date.year}';

class DayStrip extends StatelessWidget {
  const DayStrip({super.key, required this.selected, required this.onSelect});

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
              label: Text(weekdayShort[i]),
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

class DayPage extends ConsumerWidget {
  const DayPage({
    super.key,
    required this.lessons,
    required this.nowWeekType,
    required this.noData,
    required this.onRefresh,
    this.groupLabelOf,
  });

  final List<Lesson> lessons;
  final WeekType? nowWeekType; // тип текущей недели для метки «Сейчас»
  final bool noData; // кэш пуст из-за неудачного первого синка (не «пар нет»)
  final Future<void> Function() onRefresh;

  /// Режим преподавателя: чем подписать пару вместо преподавателя. null —
  /// режим группы (подпись остаётся преподавательской).
  final String Function(Lesson)? groupLabelOf;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final now = ref.watch(clockProvider)();

    // Пустой день при пустом кэше и неудачном первом синке — не «пар нет», а
    // «данные ещё не загружены». Честная плашка вместо «Пар нет — отдыхаем».
    final emptyText = noData
        ? 'Нет данных. Для первой загрузки нужна сеть'
        : 'Пар нет — отдыхаем';

    return RefreshIndicator(
      onRefresh: onRefresh,
      child: lessons.isEmpty
          ? ListView(
              children: [
                const SizedBox(height: 120),
                Center(
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 24),
                    child: Text(emptyText, textAlign: TextAlign.center),
                  ),
                ),
              ],
            )
          : ListView.separated(
              padding: const EdgeInsets.all(12),
              itemCount: lessons.length,
              separatorBuilder: (_, _) => const SizedBox(height: 8),
              itemBuilder: (context, index) => LessonCard(
                lesson: lessons[index],
                isNow: isLessonNow(lessons[index], nowWeekType, now),
                groupLabel: groupLabelOf?.call(lessons[index]),
              ),
            ),
    );
  }
}

class LessonCard extends StatelessWidget {
  const LessonCard({
    super.key,
    required this.lesson,
    required this.isNow,
    this.groupLabel,
  });

  final Lesson lesson;
  final bool isNow;

  /// Имя группы вместо преподавателя (режим преподавателя): у преподавателя
  /// групп много, и полезна именно группа, а не собственное имя в каждой паре.
  final String? groupLabel;

  String _hhmm(String hhmmss) => hhmmss.substring(0, 5);

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final details = [
      if (lesson.room != null) formatRoom(lesson.room!),
      if (groupLabel != null)
        groupLabel!
      else if (lesson.teacherName != null)
        lesson.teacherName!,
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
                    padding:
                        const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
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
            Text(lesson.subject, style: Theme.of(context).textTheme.titleMedium),
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
