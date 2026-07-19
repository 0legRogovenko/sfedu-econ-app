import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sfedu_econ/core/prefs.dart';
import 'package:sfedu_econ/features/contacts/contact.dart';
import 'package:sfedu_econ/features/contacts/contacts_providers.dart';
import 'package:sfedu_econ/features/contacts/contacts_repository.dart';
import 'package:sfedu_econ/features/news/news_providers.dart';
import 'package:sfedu_econ/features/news/news_repository.dart';
import 'package:sfedu_econ/features/onboarding/selected_group.dart';
import 'package:sfedu_econ/features/schedule/schedule_data.dart';
import 'package:sfedu_econ/features/schedule/schedule_providers.dart';
import 'package:sfedu_econ/features/teachers/teacher.dart';
import 'package:sfedu_econ/features/teachers/teachers_providers.dart';
import 'package:sfedu_econ/main.dart';

/// Экраны расписания и новостей в фоне ходят в реальную drift-БД/dio — здесь
/// это не по теме теста, поэтому подменяем на пустые мгновенные состояния.
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

// Патроним «Игоревна» (не «Петровна») намеренно — иначе имя случайно
// совпадает по подстроке с запросом «петров» в тестах поиска
// (см. тот же приём в contacts_search_test.dart).
Contact _c({
  int id = 1,
  String section = 'Деканат',
  String name = 'Иванова Елена Игоревна',
  String? role = 'Декан',
  String? office = '203',
  String? email = 'dekan@sfedu.ru',
  String? phone,
  String? officeHours = 'Пн–Пт 10:00–12:00',
}) =>
    Contact(
      id: id,
      section: section,
      name: name,
      role: role,
      office: office,
      email: email,
      phone: phone,
      officeHours: officeHours,
    );

/// Фейковый нотифаер: сразу отдаёт готовую ленту, refresh — no-op.
class _FakeContactsFeed extends ContactsFeedNotifier {
  _FakeContactsFeed(this._feed);
  final ContactsFeed _feed;

  @override
  Future<ContactsFeed> build() async => _feed;

  @override
  Future<void> refresh() async {}
}

/// main.dart читает themeModeProvider, которому нужен sharedPreferencesProvider
/// — подменяем на мок, чтобы не падать с UnimplementedError.
/// Экран преподавателя открывается по тапу из поиска: подменяем его источники,
/// иначе он уходит в реальную drift-БД и вечно крутит спиннер.
class _FakeTeacherSync extends TeacherSyncNotifier {
  _FakeTeacherSync(super.teacherId);

  @override
  Future<void> sync() async {}
}

Future<Widget> _app(
  List<Contact> items, {
  bool offline = false,
  List<Teacher> teachers = const [],
}) async {
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
      contactsFeedProvider.overrideWith(
        () => _FakeContactsFeed(
          ContactsFeed(items: items, offline: offline),
        ),
      ),
      teachersProvider.overrideWith((ref) async => teachers),
      teacherScheduleProvider.overrideWith(
          (ref, teacherId) => Stream.value(const ScheduleData.empty())),
      for (final t in teachers)
        teacherSyncProvider(t.id).overrideWith(() => _FakeTeacherSync(t.id)),
    ],
    child: const SfeduEconApp(),
  );
}

void main() {
  testWidgets('секции и контакты рендерятся', (tester) async {
    await tester.pumpWidget(await _app([
      _c(id: 1, section: 'Деканат', name: 'Иванова Елена Петровна'),
      _c(id: 2, section: 'Кафедра экономики', name: 'Петров Андрей Сергеевич'),
    ]));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Контакты'));
    await tester.pumpAndSettle();

    expect(find.text('Деканат'), findsOneWidget);
    expect(find.text('Кафедра экономики'), findsOneWidget);
    expect(find.text('Иванова Елена Петровна'), findsOneWidget);
    expect(find.text('Петров Андрей Сергеевич'), findsOneWidget);
  });

  testWidgets('поиск фильтрует список', (tester) async {
    await tester.pumpWidget(await _app([
      _c(id: 1, name: 'Иванова Елена Игоревна'),
      _c(id: 2, name: 'Петров Андрей Сергеевич'),
    ]));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Контакты'));
    await tester.pumpAndSettle();

    await tester.enterText(find.byType(TextField), 'петров');
    await tester.pumpAndSettle();

    expect(find.text('Петров Андрей Сергеевич'), findsOneWidget);
    expect(find.text('Иванова Елена Игоревна'), findsNothing);
  });

  testWidgets('поиск без результатов', (tester) async {
    await tester.pumpWidget(await _app([_c()]));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Контакты'));
    await tester.pumpAndSettle();

    await tester.enterText(find.byType(TextField), 'зззз');
    await tester.pumpAndSettle();

    expect(find.text('Никого не нашли'), findsOneWidget);
  });

  group('кнопка почты', () {
    testWidgets('у преподавателя кафедры кнопка письма есть', (tester) async {
      // Почты сотрудников приходят с личных страниц ЮФУ; кнопка обязана
      // появляться у любой секции, не только у деканата.
      await tester.pumpWidget(await _app([
        _c(
          id: 1,
          section: 'Экономическая теория',
          name: 'Белокрылова Ольга Спиридоновна',
          role: 'д.э.н., профессор',
          office: null,
          officeHours: null,
          email: 'obelokrylova@sfedu.ru',
        ),
      ]));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Контакты'));
      await tester.pumpAndSettle();

      expect(find.widgetWithIcon(IconButton, Icons.email_outlined),
          findsOneWidget);
    });

    testWidgets('без почты кнопки письма нет', (tester) async {
      await tester.pumpWidget(await _app([
        _c(
          id: 1,
          section: 'Экономическая теория',
          name: 'Без почты Иван Иванович',
          email: null,
          office: null,
          officeHours: null,
        ),
      ]));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Контакты'));
      await tester.pumpAndSettle();

      expect(find.widgetWithIcon(IconButton, Icons.email_outlined), findsNothing);
    });
  });

  group('преподаватели в поиске', () {
    testWidgets('поиск фамилии находит преподавателя, а не «никого не нашли»',
        (tester) async {
      // В справочнике контактов преподавателей нет (их заводит импорт
      // расписания, а не админ), поэтому поиск фамилии упирался в тупик —
      // при том что приложение знает этого человека и его расписание.
      await tester.pumpWidget(await _app(
        [_c(id: 1, name: 'Иванова Елена Петровна')],
        teachers: const [Teacher(id: 7, fullName: 'Ласкова Т.С.')],
      ));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Контакты'));
      await tester.pumpAndSettle();

      await tester.enterText(find.byType(TextField), 'Ласк');
      await tester.pumpAndSettle();

      expect(find.text('Преподаватели'), findsOneWidget);
      expect(find.text('Ласкова Т.С.'), findsOneWidget);
      expect(find.text('Никого не нашли'), findsNothing);
    });

    testWidgets('без запроса преподаватели не засоряют справочник',
        (tester) async {
      // 129 голых фамилий поверх справочника сделали бы его хуже: у них нет
      // ни кабинета, ни почты — только переход к расписанию.
      await tester.pumpWidget(await _app(
        [_c(id: 1, name: 'Иванова Елена Петровна')],
        teachers: const [Teacher(id: 7, fullName: 'Ласкова Т.С.')],
      ));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Контакты'));
      await tester.pumpAndSettle();

      expect(find.text('Преподаватели'), findsNothing);
      expect(find.text('Ласкова Т.С.'), findsNothing);
    });

    testWidgets('тап по преподавателю открывает его расписание',
        (tester) async {
      await tester.pumpWidget(await _app(
        const [],
        teachers: const [Teacher(id: 7, fullName: 'Ласкова Т.С.')],
      ));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Контакты'));
      await tester.pumpAndSettle();

      await tester.enterText(find.byType(TextField), 'Ласк');
      await tester.pumpAndSettle();
      await tester.tap(find.text('Ласкова Т.С.'));
      await tester.pumpAndSettle();

      // Заголовок экрана расписания преподавателя.
      expect(find.widgetWithText(AppBar, 'Ласкова Т.С.'), findsOneWidget);
    });
  });

  testWidgets('офлайн без кэша — «нужна сеть», а не «справочник пуст»',
      (tester) async {
    await tester.pumpWidget(await _app([], offline: true));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Контакты'));
    await tester.pumpAndSettle();

    expect(find.text('Нет данных. Для первой загрузки нужна сеть'),
        findsOneWidget);
    expect(find.text('Справочник пуст'), findsNothing);
    expect(find.textContaining('Показаны сохранённые'), findsNothing);
  });

  testWidgets('офлайн-плашка при недоступной сети', (tester) async {
    await tester.pumpWidget(await _app([_c()], offline: true));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Контакты'));
    await tester.pumpAndSettle();

    expect(
      find.text('Нет сети. Показаны сохранённые контакты'),
      findsOneWidget,
    );
  });

  testWidgets('кнопка настроек в AppBar ведёт на экран настроек',
      (tester) async {
    await tester.pumpWidget(await _app([_c()]));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Контакты'));
    await tester.pumpAndSettle();

    await tester.tap(find.byIcon(Icons.settings));
    await tester.pumpAndSettle();

    expect(find.text('Настройки'), findsOneWidget);
  });
}
