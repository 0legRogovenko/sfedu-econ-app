import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sfedu_econ/core/prefs.dart';
import 'package:sfedu_econ/features/contacts/contacts_providers.dart';
import 'package:sfedu_econ/features/contacts/contacts_repository.dart';
import 'package:sfedu_econ/features/news/news_providers.dart';
import 'package:sfedu_econ/features/news/news_repository.dart';
import 'package:sfedu_econ/features/onboarding/selected_group.dart';
import 'package:sfedu_econ/features/people/people_providers.dart';
import 'package:sfedu_econ/features/people/person.dart';
import 'package:sfedu_econ/features/schedule/schedule_data.dart';
import 'package:sfedu_econ/features/schedule/schedule_providers.dart';
import 'package:sfedu_econ/main.dart';

/// Вкладка «Контакты» — единый справочник людей. Расписание и новости в фоне
/// ходят в реальную БД, здесь не по теме — подменяем пустыми состояниями.
class _FakeSync extends SyncStatusNotifier {
  @override
  Future<void> sync() async {}
}

class _FakeNewsFeed extends NewsFeedNotifier {
  @override
  Future<NewsFeed> build() async =>
      const NewsFeed(items: [], offline: false, hasMore: false);
  @override
  Future<void> refresh() async {}
}

class _FakeContactsFeed extends ContactsFeedNotifier {
  @override
  Future<ContactsFeed> build() async =>
      const ContactsFeed(items: [], offline: false);
  @override
  Future<void> refresh() async {}
}

Person _person({
  String id = 'p1',
  String shortName = 'Вольчик В.В.',
  String fullName = 'Вольчик Вячеслав Витальевич',
  List<String> sections = const ['Экономическая теория'],
  List<String> roles = const ['доцент'],
  String? email = 'volchik@sfedu.ru',
  bool hasSchedule = true,
  int lessonCount = 5,
}) =>
    Person(
      id: id,
      shortName: shortName,
      fullName: fullName,
      sections: sections,
      roles: roles,
      email: email,
      hasSchedule: hasSchedule,
      lessonCount: lessonCount,
      examCount: 0,
    );

Future<Widget> _app(List<Person> people, {Object? error}) async {
  SharedPreferences.setMockInitialValues({});
  final prefs = await SharedPreferences.getInstance();
  return ProviderScope(
    overrides: [
      sharedPreferencesProvider.overrideWithValue(prefs),
      selectedGroupIdProvider.overrideWith(() => FakeSelectedGroupId(3)),
      scheduleDataProvider
          .overrideWith((ref) => Stream.value(const ScheduleData.empty())),
      syncStatusProvider.overrideWith(_FakeSync.new),
      newsFeedProvider.overrideWith(_FakeNewsFeed.new),
      contactsFeedProvider.overrideWith(_FakeContactsFeed.new),
      peopleProvider.overrideWith((ref) async {
        if (error != null) throw error;
        return people;
      }),
    ],
    child: const SfeduEconApp(),
  );
}

Future<void> _openContacts(WidgetTester tester) async {
  await tester.pumpAndSettle();
  await tester.tap(find.text('Контакты'));
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('справочник группирует по секциям, деканат первым',
      (tester) async {
    await tester.pumpWidget(await _app([
      _person(
          id: '1',
          shortName: 'Белов Б.Б.',
          sections: const ['Бухгалтерский учет'],
          hasSchedule: false),
      _person(
          id: '2',
          shortName: 'Деканов Д.Д.',
          sections: const ['Деканат'],
          hasSchedule: false),
    ]));
    await _openContacts(tester);

    final deanery = tester.getTopLeft(find.text('Деканат')).dy;
    final other = tester.getTopLeft(find.text('Бухгалтерский учет')).dy;
    expect(deanery, lessThan(other)); // деканат выше кафедры
  });

  testWidgets('короткое имя в списке, не полное', (tester) async {
    await tester.pumpWidget(await _app([_person(shortName: 'Вольчик В.В.')]));
    await _openContacts(tester);

    expect(find.text('Вольчик В.В.'), findsOneWidget);
    expect(find.text('Вольчик Вячеслав Витальевич'), findsNothing);
  });

  testWidgets('поиск находит внешнего преподавателя без контакта',
      (tester) async {
    // Ключевое: ОДИН поиск. По пустому запросу внешних преподавателей не
    // видно, но по фамилии — находятся, хотя секции у них нет.
    await tester.pumpWidget(await _app([
      _person(id: '1', shortName: 'Деканов Д.Д.', sections: const ['Деканат']),
      _person(
        id: '2',
        shortName: 'Груданова И.Ю.',
        fullName: 'Груданова И.Ю.',
        sections: const [],
        roles: const [],
        email: null,
      ),
    ]));
    await _openContacts(tester);

    expect(find.text('Груданова И.Ю.'), findsNothing);

    await tester.enterText(find.byType(TextField), 'Груд');
    await tester.pumpAndSettle();

    expect(find.text('Груданова И.Ю.'), findsOneWidget);
  });

  testWidgets('тап по человеку открывает карточку с полным именем',
      (tester) async {
    await tester.pumpWidget(await _app([_person()]));
    await _openContacts(tester);

    await tester.tap(find.text('Вольчик В.В.'));
    await tester.pumpAndSettle();

    expect(find.text('Вольчик Вячеслав Витальевич'), findsOneWidget);
    expect(find.widgetWithText(FilledButton, 'Расписание'), findsOneWidget);
  });

  testWidgets('у человека без расписания кнопки расписания нет',
      (tester) async {
    await tester.pumpWidget(await _app([
      _person(shortName: 'Методистов М.М.', hasSchedule: false, lessonCount: 0),
    ]));
    await _openContacts(tester);
    await tester.tap(find.text('Методистов М.М.'));
    await tester.pumpAndSettle();

    expect(find.widgetWithText(FilledButton, 'Расписание'), findsNothing);
  });

  testWidgets('кнопка письма в списке есть только при почте', (tester) async {
    await tester.pumpWidget(await _app([
      _person(id: '1', shortName: 'Спочтой С.С.', email: 'a@sfedu.ru'),
      _person(id: '2', shortName: 'Безпочты Б.Б.', email: null),
    ]));
    await _openContacts(tester);

    expect(
        find.widgetWithIcon(IconButton, Icons.email_outlined), findsOneWidget);
  });

  testWidgets('долгое нажатие на иконку копирует email', (tester) async {
    String? copiedText;
    final messenger =
        TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger;
    messenger.setMockMethodCallHandler(SystemChannels.platform, (call) async {
      if (call.method == 'Clipboard.setData') {
        copiedText =
            (call.arguments as Map<Object?, Object?>)['text'] as String?;
      }
      return null;
    });
    addTearDown(
      () => messenger.setMockMethodCallHandler(SystemChannels.platform, null),
    );

    await tester.pumpWidget(await _app([
      _person(email: 'volchik@sfedu.ru'),
    ]));
    await _openContacts(tester);

    await tester.longPress(find.byIcon(Icons.email_outlined));
    await tester.pump();

    expect(copiedText, 'volchik@sfedu.ru');
    expect(find.text('Почта скопирована'), findsOneWidget);
  });

  testWidgets('офлайн: честно про сеть, а не пустой справочник',
      (tester) async {
    await tester.pumpWidget(await _app(const [], error: Exception('нет сети')));
    await _openContacts(tester);

    expect(find.textContaining('Нужна сеть'), findsOneWidget);
  });

  testWidgets('кнопка настроек в AppBar ведёт на экран настроек',
      (tester) async {
    await tester.pumpWidget(await _app([_person()]));
    await _openContacts(tester);

    await tester.tap(find.byIcon(Icons.settings));
    await tester.pumpAndSettle();

    expect(find.text('Настройки'), findsOneWidget);
  });
}
