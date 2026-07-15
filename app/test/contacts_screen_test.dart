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
import 'package:sfedu_econ/features/schedule/lesson.dart';
import 'package:sfedu_econ/features/schedule/schedule_providers.dart';
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
Future<Widget> _app(List<Contact> items, {bool offline = false}) async {
  SharedPreferences.setMockInitialValues({});
  final prefs = await SharedPreferences.getInstance();
  return ProviderScope(
    overrides: [
      sharedPreferencesProvider.overrideWithValue(prefs),
      selectedGroupIdProvider.overrideWith(() => FakeSelectedGroupId(3)),
      lessonsProvider.overrideWith((ref) => Stream.value(const <Lesson>[])),
      syncStatusProvider.overrideWith(_FakeSync.new),
      newsFeedProvider.overrideWith(_FakeNewsFeed.new),
      contactsFeedProvider.overrideWith(
        () => _FakeContactsFeed(
          ContactsFeed(items: items, offline: offline),
        ),
      ),
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
