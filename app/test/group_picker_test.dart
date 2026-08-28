import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sfedu_econ/features/onboarding/group_picker.dart';
import 'package:sfedu_econ/features/onboarding/group_repository.dart';

Group _bachelor(int id, int course, String number) => Group(
  id: id,
  course: course,
  number: number,
  program: null,
  level: EducationLevel.bachelor,
  subgroupCount: 2,
);

Group _master(int id, int course, String program) => Group(
  id: id,
  course: course,
  number: null,
  program: program,
  level: EducationLevel.master,
  subgroupCount: 1,
);

// Намеренно перемешанный вход: разные уровни, курсы и номера вперемешку,
// чтобы проверить, что функция сама раскладывает и сортирует.
final _mixed = [
  _master(30, 2, 'Экономическая аналитика'),
  _bachelor(10, 2, '2.10'),
  _master(31, 1, 'Корпоративные финансы'),
  _bachelor(1, 1, '1.2'),
  _bachelor(2, 1, '1.1'),
  _master(32, 2, 'Корпоративные финансы'),
  _bachelor(9, 2, '2.2'),
  _bachelor(8, 2, '2.1'),
];

void main() {
  group('buildGroupPickerModel — чистая группировка', () {
    test('уровни: только присутствующие, бакалавр перед магистром', () {
      final model = buildGroupPickerModel(_mixed);
      expect(model.levels, [EducationLevel.bachelor, EducationLevel.master]);
    });

    test('уровень с одними бакалаврами не показывает магистратуру', () {
      final model = buildGroupPickerModel([_bachelor(1, 1, '1.1')]);
      expect(model.levels, [EducationLevel.bachelor]);
    });

    test('уровень с одними магистрами не показывает бакалавриат', () {
      final model = buildGroupPickerModel([
        _master(1, 1, 'Корпоративные финансы'),
      ]);
      expect(model.levels, [EducationLevel.master]);
    });

    test('бакалавр: курсы отсортированы по возрастанию', () {
      final model = buildGroupPickerModel(_mixed);
      expect(model.bachelorByCourse.keys.toList(), [1, 2]);
    });

    test(
      'бакалавр: группы внутри курса отсортированы натурально (2.2 < 2.10)',
      () {
        final model = buildGroupPickerModel(_mixed);
        expect(model.bachelorByCourse[2]!.map((g) => g.number).toList(), [
          '2.1',
          '2.2',
          '2.10',
        ]);
      },
    );

    test('магистр не попадает в бакалаврские курсы', () {
      final model = buildGroupPickerModel(_mixed);
      for (final list in model.bachelorByCourse.values) {
        expect(list.every((g) => g.level == EducationLevel.bachelor), isTrue);
      }
    });

    test('магистр: направления отсортированы по алфавиту', () {
      final model = buildGroupPickerModel(_mixed);
      expect(model.masterByProgram.keys.toList(), [
        'Корпоративные финансы',
        'Экономическая аналитика',
      ]);
    });

    test('магистр: курсы внутри направления отсортированы, без дублей', () {
      final model = buildGroupPickerModel(_mixed);
      expect(
        model.masterByProgram['Корпоративные финансы']!
            .map((g) => g.course)
            .toList(),
        [1, 2],
      );
    });

    test('бакалавр не попадает в магистерские направления', () {
      final model = buildGroupPickerModel(_mixed);
      for (final list in model.masterByProgram.values) {
        expect(list.every((g) => g.level == EducationLevel.master), isTrue);
      }
    });

    test('нет дублей: суммарно столько же групп, сколько на входе', () {
      final model = buildGroupPickerModel(_mixed);
      final total =
          model.bachelorByCourse.values.fold<int>(0, (s, l) => s + l.length) +
          model.masterByProgram.values.fold<int>(0, (s, l) => s + l.length);
      expect(total, _mixed.length);
    });
  });

  group('GroupPicker — виджет', () {
    Future<void> pump(
      WidgetTester tester, {
      required List<Group> groups,
      required void Function(Group?) onSelected,
      int? initialSelectedId,
    }) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: GroupPicker(
              groups: groups,
              initialSelectedId: initialSelectedId,
              onSelected: onSelected,
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();
    }

    testWidgets('показывает только реально присутствующие уровни', (
      tester,
    ) async {
      await pump(tester, groups: [_bachelor(1, 1, '1.1')], onSelected: (_) {});
      expect(find.text('Бакалавриат'), findsOneWidget);
      expect(find.text('Магистратура'), findsNothing);
    });

    testWidgets('бакалавр: уровень → курс → группа', (tester) async {
      Group? picked;
      await pump(tester, groups: _mixed, onSelected: (g) => picked = g);

      await tester.tap(find.text('Бакалавриат'));
      await tester.pumpAndSettle();
      // Магистерские направления не примешаны к бакалаврскому пути.
      expect(find.text('Корпоративные финансы'), findsNothing);

      await tester.tap(find.text('2 курс'));
      await tester.pumpAndSettle();
      expect(find.text('2.1'), findsOneWidget);
      // Чужой курс не показан.
      expect(find.text('1.1'), findsNothing);

      await tester.tap(find.text('2.1'));
      await tester.pumpAndSettle();
      expect(picked?.number, '2.1');
    });

    testWidgets('магистр: уровень → курс → направление', (tester) async {
      Group? picked;
      await pump(tester, groups: _mixed, onSelected: (g) => picked = g);

      await tester.tap(find.text('Магистратура'));
      await tester.pumpAndSettle();
      // Бакалаврские номера не примешаны к магистерскому пути.
      expect(find.text('1.1'), findsNothing);
      // Курс — отдельный явный шаг, а не спрятан за длинным направлением.
      expect(find.text('1 курс'), findsOneWidget);
      expect(find.text('2 курс'), findsOneWidget);

      await tester.tap(find.text('1 курс'));
      await tester.pumpAndSettle();
      expect(find.text('Корпоративные финансы'), findsOneWidget);
      expect(find.text('Экономическая аналитика'), findsNothing);

      await tester.tap(
        find.widgetWithText(ChoiceChip, 'Корпоративные финансы'),
      );
      await tester.pumpAndSettle();
      expect(picked?.program, 'Корпоративные финансы');
      expect(picked?.course, 1);
    });

    testWidgets('двуязычное направление показывает русское название один раз', (
      tester,
    ) async {
      final bilingual = _master(
        40,
        1,
        'International Economics and Analytics '
        '(Международная экономика и аналитика)',
      );
      await pump(tester, groups: [bilingual], onSelected: (_) {});

      await tester.tap(find.text('Магистратура'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('1 курс'));
      await tester.pumpAndSettle();

      expect(find.text('Международная экономика и аналитика'), findsOneWidget);
      expect(find.textContaining('International Economics'), findsNothing);
      final label = tester.widget<Text>(
        find.text('Международная экономика и аналитика'),
      );
      expect(label.maxLines, 1);
    });

    testWidgets('магистерские направления выровнены по левому краю', (
      tester,
    ) async {
      tester.view.physicalSize = const Size(390, 844);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      await pump(
        tester,
        groups: [_master(41, 1, 'Корпоративные финансы')],
        onSelected: (_) {},
      );

      await tester.tap(find.text('Магистратура'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('1 курс'));
      await tester.pumpAndSettle();

      final chipRect = tester.getRect(
        find.widgetWithText(ChoiceChip, 'Корпоративные финансы'),
      );
      final labelRect = tester.getRect(find.text('Корпоративные финансы'));
      expect(labelRect.left - chipRect.left, lessThan(32));
    });

    testWidgets('смена уровня сбрасывает нижний выбор', (tester) async {
      final picks = <Group?>[];
      await pump(tester, groups: _mixed, onSelected: picks.add);

      await tester.tap(find.text('Бакалавриат'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('2 курс'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('2.1'));
      await tester.pumpAndSettle();
      expect(picks.last?.number, '2.1');

      // Переключаемся на магистратуру — выбор группы должен сброситься.
      await tester.tap(find.text('Магистратура'));
      await tester.pumpAndSettle();
      expect(picks.last, isNull);
      // Бакалаврский курс/группа больше не показаны.
      expect(find.text('2.1'), findsNothing);
      // «2 курс» остаётся как магистерский шаг — это уже другой путь.
      expect(find.text('2 курс'), findsOneWidget);
      expect(find.text('Корпоративные финансы'), findsNothing);
    });

    testWidgets('initialSelectedId открывает пикер на текущей группе', (
      tester,
    ) async {
      Group? picked;
      await pump(
        tester,
        groups: _mixed,
        initialSelectedId: 8, // бакалавр 2.1
        onSelected: (g) => picked = g,
      );

      // Курс уже раскрыт — видна группа текущего курса.
      expect(find.text('2.1'), findsOneWidget);
      expect(picked, isNull); // без явного тапа колбэк не дёргаем
    });

    testWidgets('семь бакалаврских групп помещаются в одну строку', (
      tester,
    ) async {
      tester.view.physicalSize = const Size(390, 844);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      final groups = [
        for (var index = 1; index <= 7; index++)
          _bachelor(index, 3, '3.$index'),
      ];
      await pump(tester, groups: groups, onSelected: (_) {});

      await tester.tap(find.text('Бакалавриат'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('3 курс'));
      await tester.pumpAndSettle();

      final tops = [
        for (var index = 1; index <= 7; index++)
          tester.getTopLeft(find.text('3.$index')).dy,
      ];
      expect(tops.toSet(), hasLength(1));
      expect(tester.getTopRight(find.text('3.7')).dx, lessThanOrEqualTo(390));

      await tester.tap(find.text('3.1'));
      await tester.pumpAndSettle();
      final selectedChip = tester.widget<ChoiceChip>(
        find.widgetWithText(ChoiceChip, '3.1'),
      );
      expect(selectedChip.selected, isTrue);
      // Галочка Material отнимает ширину у короткого номера и превращает
      // выбранное «3.1» в «3…» на реальном iPhone.
      expect(selectedChip.showCheckmark, isFalse);
    });
  });
}
