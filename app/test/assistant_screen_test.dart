import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sfedu_econ/core/prefs.dart';
import 'package:sfedu_econ/features/assistant/assistant_api.dart';
import 'package:sfedu_econ/features/assistant/assistant_providers.dart';
import 'package:sfedu_econ/features/assistant/assistant_screen.dart';
import 'package:sfedu_econ/features/contacts/contacts_providers.dart';
import 'package:sfedu_econ/features/contacts/contacts_repository.dart';
import 'package:sfedu_econ/features/news/news_providers.dart';
import 'package:sfedu_econ/features/people/people_providers.dart';
import 'package:sfedu_econ/features/news/news_repository.dart';
import 'package:sfedu_econ/features/onboarding/selected_group.dart';
import 'package:sfedu_econ/features/schedule/schedule_data.dart';
import 'package:sfedu_econ/features/schedule/schedule_providers.dart';
import 'package:sfedu_econ/main.dart';

/// Соседние вкладки в фоне ходят в реальную drift-БД/dio — здесь это
/// не по теме, подменяем на пустые мгновенные состояния.
class _FakeSync extends SyncStatusNotifier {
  @override
  Future<void> sync() async {}
}

class _FakeFeed extends NewsFeedNotifier {
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

class _FakeApi implements AssistantApi {
  _FakeApi(this._result);
  final AskResult _result;
  final List<String> questions = [];

  @override
  Future<AskResult> ask(String question, String deviceId) async {
    questions.add(question);
    return _result;
  }
}

Future<Widget> _app(_FakeApi api) async {
  SharedPreferences.setMockInitialValues({});
  final prefs = await SharedPreferences.getInstance();
  return ProviderScope(
    overrides: [
      sharedPreferencesProvider.overrideWithValue(prefs),
      selectedGroupIdProvider.overrideWith(() => FakeSelectedGroupId(3)),
      scheduleDataProvider
          .overrideWith((ref) => Stream.value(const ScheduleData.empty())),
      syncStatusProvider.overrideWith(_FakeSync.new),
      newsFeedProvider.overrideWith(_FakeFeed.new),
      contactsFeedProvider.overrideWith(_FakeContactsFeed.new),
      peopleProvider.overrideWith((ref) async => const []),
      assistantApiProvider.overrideWithValue(api),
    ],
    child: const SfeduEconApp(),
  );
}

/// Открывает вкладку помощника с готовым фейком API.
Future<_FakeApi> _openAssistant(WidgetTester tester, AskResult result) async {
  final api = _FakeApi(result);
  await tester.pumpWidget(await _app(api));
  await tester.pumpAndSettle();
  await tester.tap(find.text('Помощник'));
  await tester.pumpAndSettle();
  return api;
}

Future<void> _send(WidgetTester tester, String question) async {
  await tester.enterText(find.byType(TextField), question);
  await tester.tap(find.byTooltip('Отправить'));
  await tester.pumpAndSettle();
}

const _answer = AskAnswer(text: 'Справку берут в 305 кабинете', fallback: false);

void main() {
  testWidgets('пустой чат показывает подсказки типовых вопросов',
      (tester) async {
    await _openAssistant(tester, _answer);

    expect(find.text('Задайте вопрос о факультете'), findsOneWidget);
    for (final suggestion in assistantSuggestions) {
      expect(find.text(suggestion), findsOneWidget);
    }
  });

  testWidgets('тап по подсказке отправляет её', (tester) async {
    final api = await _openAssistant(tester, _answer);

    await tester.tap(find.text(assistantSuggestions.first));
    await tester.pumpAndSettle();

    expect(api.questions, [assistantSuggestions.first]);
    expect(find.text(assistantSuggestions.first), findsOneWidget); // уже в ленте
  });

  testWidgets('отправленный вопрос и ответ видны в ленте', (tester) async {
    await _openAssistant(tester, _answer);

    await _send(tester, 'Где взять справку?');

    expect(find.text('Где взять справку?'), findsOneWidget);
    expect(find.text('Справку берут в 305 кабинете'), findsOneWidget);
  });

  testWidgets('под ответом есть дисклеймер и чип «Контакты деканата»',
      (tester) async {
    await _openAssistant(tester, _answer);

    await _send(tester, 'Где взять справку?');

    expect(find.text(assistantDisclaimer), findsOneWidget);
    expect(find.text('Контакты деканата'), findsOneWidget);
  });

  testWidgets('под заглушкой бэкенда нет подписи «Ответ AI»: модели там не было',
      (tester) async {
    await _openAssistant(
      tester,
      const AskAnswer(
        text: 'Сейчас не могу ответить. Обратитесь в деканат',
        fallback: true,
      ),
    );

    await _send(tester, 'Где взять справку?');

    expect(find.text('Сейчас не могу ответить. Обратитесь в деканат'),
        findsOneWidget);
    expect(find.text(assistantDisclaimer), findsNothing);
    // а вот чип контактов под заглушкой как раз к месту
    expect(find.text('Контакты деканата'), findsOneWidget);
  });

  testWidgets('у сообщения пользователя дисклеймера нет', (tester) async {
    await _openAssistant(tester, const AskFailed());

    await _send(tester, 'Где взять справку?');

    // ответа модели не было — дисклеймеру неоткуда взяться
    expect(find.text(assistantDisclaimer), findsNothing);
  });

  testWidgets('тап по чипу ведёт на вкладку контактов', (tester) async {
    await _openAssistant(tester, _answer);
    await _send(tester, 'Где взять справку?');

    await tester.tap(find.text('Контакты деканата'));
    await tester.pumpAndSettle();

    expect(find.text('Справочник пуст'), findsOneWidget);
  });

  testWidgets('при ошибке сети видно честное «нужен интернет»',
      (tester) async {
    await _openAssistant(tester, const AskFailed());

    await _send(tester, 'Где взять справку?');

    expect(find.textContaining('Нужен интернет'), findsOneWidget);
  });

  testWidgets('при исчерпанном лимите видно текст лимита от сервера',
      (tester) async {
    await _openAssistant(
      tester,
      const AskRateLimited(detail: 'Не больше 5 вопросов за 24 часа'),
    );

    await _send(tester, 'Где взять справку?');

    expect(find.text('Не больше 5 вопросов за 24 часа'), findsOneWidget);
  });

  testWidgets('поле ввода очищается после отправки', (tester) async {
    await _openAssistant(tester, _answer);

    await _send(tester, 'Где взять справку?');

    expect(
      tester.widget<TextField>(find.byType(TextField)).controller?.text,
      isEmpty,
    );
  });
}
