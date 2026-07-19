import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/clock.dart';
import '../onboarding/group_repository.dart';
import '../schedule/schedule_widgets.dart';
import '../schedule/week_logic.dart';
import 'people_providers.dart';
import 'person.dart';

/// Расписание человека из единого справочника. Карточка пары подписана ГРУППОЙ
/// (у преподавателя их много). Данные приходят из /api/persons/{id}/schedule
/// одним запросом; офлайн-кэша нет — при отсутствии сети честная плашка.
class PersonScheduleScreen extends ConsumerStatefulWidget {
  const PersonScheduleScreen({super.key, required this.person});

  final Person person;

  @override
  ConsumerState<PersonScheduleScreen> createState() =>
      _PersonScheduleScreenState();
}

class _PersonScheduleScreenState extends ConsumerState<PersonScheduleScreen> {
  late final PageController _pageController;
  late final DateTime _baseMonday;
  late int _dayIndex;

  @override
  void initState() {
    super.initState();
    final now = ref.read(clockProvider)();
    final isSunday = now.weekday == DateTime.sunday;
    final monday = now.subtract(Duration(days: now.weekday - 1));
    _baseMonday = DateTime(monday.year, monday.month, monday.day)
        .add(Duration(days: isSunday ? 7 : 0));
    _dayIndex = isSunday ? 0 : now.weekday - 1;
    _pageController = PageController(initialPage: _dayIndex);
  }

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }

  DateTime _dateForIndex(int index) => _baseMonday.add(Duration(days: index));

  @override
  Widget build(BuildContext context) {
    final scheduleAsync = ref.watch(personScheduleProvider(widget.person.id));
    final groups = ref.watch(groupsProvider).maybeWhen(
          data: (list) => list,
          orElse: () => const <Group>[],
        );
    final moduleName = scheduleAsync.maybeWhen(
      data: (data) =>
          activeModule(data.modules, _dateForIndex(_dayIndex))?.name,
      orElse: () => null,
    );
    final weekType = scheduleAsync.maybeWhen(
      data: (data) =>
          weekTypeForDate(data.weekCalendar, _dateForIndex(_dayIndex)),
      orElse: () => null,
    );
    final now = ref.read(clockProvider)();
    final nowWeekType = scheduleAsync.maybeWhen(
      data: (data) => weekTypeForDate(
          data.weekCalendar, DateTime(now.year, now.month, now.day)),
      orElse: () => null,
    );

    return Scaffold(
      appBar: AppBar(
        title: Text(widget.person.shortName),
        actions: [
          if (moduleName != null)
            Center(
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 8),
                child: Text(moduleName,
                    style: Theme.of(context).textTheme.bodySmall),
              ),
            ),
          if (weekType != null)
            Center(
              child: Padding(
                padding: const EdgeInsets.only(right: 12),
                child: Text(weekType.label,
                    style: Theme.of(context).textTheme.bodySmall),
              ),
            ),
        ],
      ),
      body: Column(
        children: [
          DayStrip(
            selected: _dayIndex,
            onSelect: (index) {
              setState(() => _dayIndex = index);
              // hasClients: полоса дней доступна и в loading, когда PageView
              // ещё не построен (та же защита, что на экране преподавателя).
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
              error: (error, _) => const Center(
                child: Padding(
                  padding: EdgeInsets.symmetric(horizontal: 24),
                  child: Text(
                    'Не удалось загрузить расписание. Нужна сеть',
                    textAlign: TextAlign.center,
                  ),
                ),
              ),
              data: (data) => PageView.builder(
                controller: _pageController,
                itemCount: 6,
                onPageChanged: (index) => setState(() => _dayIndex = index),
                itemBuilder: (context, index) => DayPage(
                  lessons: lessonsForDay(data, _dateForIndex(index)),
                  nowWeekType: nowWeekType,
                  noData: false,
                  groupLabelOf: (lesson) => groupNameOf(groups, lesson.groupId),
                  onRefresh: () async =>
                      ref.invalidate(personScheduleProvider(widget.person.id)),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
