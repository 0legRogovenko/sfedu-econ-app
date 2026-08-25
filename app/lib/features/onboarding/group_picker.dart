import 'package:flutter/material.dart';

import 'group_repository.dart';

/// Разложенный по уровням список групп для селектора.
///
/// Бакалавры и магистры не смешиваются: у бакалавра шаг «курс → группа»,
/// у магистра — «направление → курс». Всё уже отсортировано, поэтому виджету
/// остаётся только рисовать чипы в готовом порядке.
class GroupPickerModel {
  const GroupPickerModel({
    required this.levels,
    required this.bachelorByCourse,
    required this.masterByProgram,
  });

  /// Только реально присутствующие уровни, бакалавр перед магистром.
  final List<EducationLevel> levels;

  /// Бакалавр: курс → группы этого курса, отсортированные по номеру.
  final Map<int, List<Group>> bachelorByCourse;

  /// Магистр: направление (программа) → группы, отсортированные по курсу.
  final Map<String, List<Group>> masterByProgram;
}

/// Раскладывает плоский список групп по уровням/курсам/направлениям и
/// сортирует. Чистая функция: без сети, состояния и side-эффектов.
GroupPickerModel buildGroupPickerModel(List<Group> groups) {
  final bachelorByCourse = <int, List<Group>>{};
  final masterByProgram = <String, List<Group>>{};

  for (final group in groups) {
    switch (group.level) {
      case EducationLevel.bachelor:
        bachelorByCourse.putIfAbsent(group.course, () => []).add(group);
      case EducationLevel.master:
        // У магистра направление — обязательный ключ. Если программы нет,
        // группировать не по чему: отправляем в бакалаврский путь по курсу,
        // чтобы группа не пропала из селектора.
        final program = group.program;
        if (program == null) {
          bachelorByCourse.putIfAbsent(group.course, () => []).add(group);
        } else {
          masterByProgram.putIfAbsent(program, () => []).add(group);
        }
    }
  }

  // Курсы бакалавра — по возрастанию, группы внутри — натуральной сортировкой
  // (чтобы 2.2 шла раньше 2.10, а не наоборот при строковом сравнении).
  final sortedBachelor = <int, List<Group>>{};
  for (final course in bachelorByCourse.keys.toList()..sort()) {
    final list = bachelorByCourse[course]!
      ..sort((a, b) => _naturalCompare(a.displayName, b.displayName));
    sortedBachelor[course] = list;
  }

  // Направления магистра — по алфавиту, курсы внутри — по возрастанию.
  final sortedMaster = <String, List<Group>>{};
  for (final program in masterByProgram.keys.toList()..sort()) {
    final list = masterByProgram[program]!
      ..sort((a, b) => a.course.compareTo(b.course));
    sortedMaster[program] = list;
  }

  final levels = <EducationLevel>[
    if (sortedBachelor.isNotEmpty) EducationLevel.bachelor,
    if (sortedMaster.isNotEmpty) EducationLevel.master,
  ];

  return GroupPickerModel(
    levels: levels,
    bachelorByCourse: sortedBachelor,
    masterByProgram: sortedMaster,
  );
}

/// Натуральное сравнение строк: числовые куски сравниваются как числа, а не
/// посимвольно. Так «2.2» < «2.10».
int _naturalCompare(String a, String b) {
  final ax = _chunks(a);
  final bx = _chunks(b);
  for (var i = 0; i < ax.length && i < bx.length; i++) {
    final an = int.tryParse(ax[i]);
    final bn = int.tryParse(bx[i]);
    final int cmp;
    if (an != null && bn != null) {
      cmp = an.compareTo(bn);
    } else {
      cmp = ax[i].compareTo(bx[i]);
    }
    if (cmp != 0) return cmp;
  }
  return ax.length.compareTo(bx.length);
}

List<String> _chunks(String s) =>
    RegExp(r'\d+|\D+').allMatches(s).map((m) => m[0]!).toList();

String _levelLabel(EducationLevel level) => switch (level) {
      EducationLevel.bachelor => 'Бакалавриат',
      EducationLevel.master => 'Магистратура',
    };

/// Двухшаговый селектор группы: уровень → (курс → группа | направление → курс).
///
/// Виджет сам ведёт состояние выбора и сообщает наверх через [onSelected]:
/// готовая [Group] при выборе конечного чипа, `null` — когда выбор сброшен
/// (например, сменили уровень). Смена уровня всегда сбрасывает нижний выбор.
class GroupPicker extends StatefulWidget {
  const GroupPicker({
    super.key,
    required this.groups,
    required this.onSelected,
    this.initialSelectedId,
  });

  final List<Group> groups;

  /// Колбэк выбора: [Group] — выбрана конечная группа, `null` — выбор сброшен.
  final ValueChanged<Group?> onSelected;

  /// Если задан и найден в списке — пикер открывается раскрытым на этой группе
  /// (нужно экрану смены группы, чтобы показать текущий выбор).
  final int? initialSelectedId;

  @override
  State<GroupPicker> createState() => _GroupPickerState();
}

class _GroupPickerState extends State<GroupPicker> {
  late GroupPickerModel _model;

  EducationLevel? _level;
  int? _course; // бакалаврский путь
  String? _program; // магистерский путь
  int? _selectedId;

  @override
  void initState() {
    super.initState();
    _model = buildGroupPickerModel(widget.groups);
    _restoreInitial();
  }

  @override
  void didUpdateWidget(GroupPicker oldWidget) {
    super.didUpdateWidget(oldWidget);
    // Список групп приходит асинхронно; при его смене пересобираем модель.
    if (!identical(oldWidget.groups, widget.groups)) {
      _model = buildGroupPickerModel(widget.groups);
    }
  }

  /// Раскрывает пикер на [GroupPicker.initialSelectedId], если он есть в списке.
  void _restoreInitial() {
    final id = widget.initialSelectedId;
    if (id == null) return;
    for (final group in widget.groups) {
      if (group.id != id) continue;
      _selectedId = group.id;
      _level = group.level;
      if (group.level == EducationLevel.bachelor) {
        _course = group.course;
      } else {
        _program = group.program;
      }
      return;
    }
  }

  void _selectLevel(EducationLevel level) {
    setState(() {
      _level = level;
      _course = null;
      _program = null;
      _selectedId = null;
    });
    // Смена уровня сбрасывает нижний выбор — сообщаем наверх, чтобы, например,
    // погасла кнопка «Начать».
    widget.onSelected(null);
  }

  void _selectCourse(int course) {
    setState(() {
      _course = course;
      _selectedId = null;
    });
    widget.onSelected(null);
  }

  void _selectProgram(String program) {
    setState(() {
      _program = program;
      _selectedId = null;
    });
    widget.onSelected(null);
  }

  void _selectGroup(Group group) {
    setState(() => _selectedId = group.id);
    widget.onSelected(group);
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _ChipRow(
          children: [
            for (final level in _model.levels)
              ChoiceChip(
                label: Text(_levelLabel(level)),
                selected: _level == level,
                onSelected: (_) => _selectLevel(level),
              ),
          ],
        ),
        if (_level == EducationLevel.bachelor) ..._bachelorSteps(),
        if (_level == EducationLevel.master) ..._masterSteps(),
      ],
    );
  }

  List<Widget> _bachelorSteps() {
    final courses = _model.bachelorByCourse.keys.toList();
    final groups =
        _course == null ? const <Group>[] : _model.bachelorByCourse[_course]!;
    return [
      const SizedBox(height: 16),
      _ChipRow(
        children: [
          for (final course in courses)
            ChoiceChip(
              label: Text('$course курс'),
              selected: _course == course,
              onSelected: (_) => _selectCourse(course),
            ),
        ],
      ),
      if (groups.isNotEmpty) ...[
        const SizedBox(height: 16),
        _GroupChipRow(
          children: [
            for (final group in groups)
              ChoiceChip(
                label: Text(group.displayName),
                selected: _selectedId == group.id,
                onSelected: (_) => _selectGroup(group),
                showCheckmark: false,
                visualDensity: VisualDensity.compact,
                materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                labelPadding: const EdgeInsets.symmetric(horizontal: 2),
              ),
          ],
        ),
      ],
    ];
  }

  List<Widget> _masterSteps() {
    final programs = _model.masterByProgram.keys.toList();
    final groups = _program == null
        ? const <Group>[]
        : _model.masterByProgram[_program]!;
    return [
      const SizedBox(height: 16),
      _ChipRow(
        children: [
          for (final program in programs)
            ChoiceChip(
              label: Text(program),
              selected: _program == program,
              onSelected: (_) => _selectProgram(program),
            ),
        ],
      ),
      if (groups.isNotEmpty) ...[
        const SizedBox(height: 16),
        _GroupChipRow(
          children: [
            for (final group in groups)
              ChoiceChip(
                label: Text('${group.course} курс'),
                selected: _selectedId == group.id,
                onSelected: (_) => _selectGroup(group),
                visualDensity: VisualDensity.compact,
                materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                labelPadding: const EdgeInsets.symmetric(horizontal: 2),
              ),
          ],
        ),
      ],
    ];
  }
}

class _ChipRow extends StatelessWidget {
  const _ChipRow({required this.children});

  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    return Wrap(spacing: 8, runSpacing: 8, children: children);
  }
}

/// Конечный ряд групп не переносится: у каждого курса шесть коротких номеров,
/// поэтому делим доступную ширину поровну. Уровни/курсы/длинные направления
/// выше остаются Wrap — перенос там полезен и ожидаем.
class _GroupChipRow extends StatelessWidget {
  const _GroupChipRow({required this.children});

  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        for (var index = 0; index < children.length; index++)
          Expanded(
            child: Padding(
              padding: EdgeInsets.only(
                right: index == children.length - 1 ? 0 : 4,
              ),
              child: SizedBox(width: double.infinity, child: children[index]),
            ),
          ),
      ],
    );
  }
}
