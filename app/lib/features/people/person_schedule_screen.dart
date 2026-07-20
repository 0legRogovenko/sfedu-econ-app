import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/clock.dart';
import '../onboarding/group_repository.dart';
import '../schedule/schedule_providers.dart';
import '../schedule/schedule_widgets.dart';
import '../schedule/semester.dart';
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
  // Создаётся лениво — на первом кадре с данными, когда уже известен семестр и
  // корректная стартовая страница (день недели). До этого расписание грузится.
  PageController? _pageController;
  // Пересчитывается на каждый build от выбранного семестра, поэтому НЕ final.
  late DateTime _baseMonday;
  int _dayIndex = 0;

  /// Локальный выбор семестра (seasonKey). Стартово — тот, что выбрал студент на
  /// своём расписании; дальше переключение здесь НЕ трогает домашний экран
  /// студента (одностороннее следование студент→преподаватель).
  String? _chosen;

  /// Одноразовое выравнивание стартового дня по семестру (текущий — на
  /// сегодняшнем дне, не текущий — на понедельнике первой недели).
  bool _dayAligned = false;

  /// Пользователь сам выбрал день в ленте (в т.ч. пока грузилось расписание).
  /// Тогда стартовое выравнивание его НЕ перетирает.
  bool _userPickedDay = false;

  @override
  void initState() {
    super.initState();
    _chosen = ref.read(viewedSemesterProvider); // семестр, выбранный студентом
  }

  @override
  void dispose() {
    _pageController?.dispose();
    super.dispose();
  }

  DateTime _dateForIndex(int index) => _baseMonday.add(Duration(days: index));

  /// Выбор семестра из меню кнопки — ЛОКАЛЬНО, без записи в общий провайдер:
  /// студент листает расписание преподавателя, не меняя своё домашнее.
  void _selectSemester(Semester semester, Semester current) {
    if (semester.seasonKey == current.seasonKey) return;
    setState(() {
      _chosen = semester.seasonKey;
      _dayIndex = 0; // у не текущего семестра осмысленна первая неделя целиком
    });
    _pageController?.jumpToPage(0);
  }

  @override
  Widget build(BuildContext context) {
    final scheduleAsync = ref.watch(personScheduleProvider(widget.person.id));
    final groups = ref
        .watch(groupsProvider)
        .maybeWhen(data: (list) => list, orElse: () => const <Group>[]);
    final now = ref.read(clockProvider)();

    // Семестры из расписания преподавателя; стартовый выбор — тот же, что у
    // студента (seeded в initState), поэтому расписание открывается на нужном
    // семестре, а не всегда на текущей неделе.
    final semesters = scheduleAsync.maybeWhen(
      data: detectSemesters,
      orElse: () => const <Semester>[],
    );
    final selectedSemester = resolveSemester(semesters, _chosen, now);
    _baseMonday = mondayForSemester(selectedSemester, now);

    // Как только данные пришли (семестр известен), один раз выставляем стартовый
    // день: текущий семестр открываем на сегодняшнем дне (чтобы работала метка
    // «Сейчас»), не текущий — на понедельнике его первой недели.
    if (!_dayAligned && scheduleAsync.hasValue) {
      _dayAligned = true;
      // День, выбранный пользователем во время загрузки, сохраняем; иначе
      // выставляем стартовый по семестру.
      if (!_userPickedDay) {
        _dayIndex =
            (selectedSemester != null && !selectedSemester.contains(now))
            ? 0
            : (now.weekday == DateTime.sunday ? 0 : now.weekday - 1);
      }
      _pageController = PageController(initialPage: _dayIndex);
    }

    final moduleName = scheduleAsync.maybeWhen(
      data: (data) =>
          activeModule(data.modules, _dateForIndex(_dayIndex))?.name,
      orElse: () => null,
    );
    final nowWeekType = scheduleAsync.maybeWhen(
      data: (data) => weekTypeForDate(
        data.weekCalendar,
        DateTime(now.year, now.month, now.day),
      ),
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
                child: Text(
                  moduleName,
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ),
            ),
          // Тот же переключатель семестра, что и у студента; тип недели
          // («верхняя/нижняя») в шапке больше не показываем — он был справочным,
          // а пары и так отфильтрованы по нему.
          if (semesters.length >= 2 && selectedSemester != null)
            SemesterButton(
              semesters: semesters,
              selected: selectedSemester,
              onSelect: (semester) =>
                  _selectSemester(semester, selectedSemester),
            ),
        ],
      ),
      body: Column(
        children: [
          // Межсезонье — как на экране группы: семестры есть, а сегодня вне
          // всех; показана первая неделя семестра, о чём говорим явно.
          if (selectedSemester != null &&
              !semesters.any((s) => s.contains(now)))
            VacationBanner(semester: selectedSemester),
          DayStrip(
            selected: _dayIndex,
            onSelect: (index) {
              setState(() {
                _dayIndex = index;
                _userPickedDay = true;
              });
              // hasClients: полоса дней доступна и в loading, когда PageView
              // ещё не построен (та же защита, что на экране студента).
              if (_pageController?.hasClients ?? false) {
                _pageController!.animateToPage(
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
