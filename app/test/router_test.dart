import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sfedu_econ/features/onboarding/selected_group.dart';
import 'package:sfedu_econ/main.dart';

Widget _appWithGroup() => ProviderScope(
      overrides: [
        // группа уже выбрана — онбординг не показывается
        selectedGroupIdProvider.overrideWith(() => FakeSelectedGroupId(3)),
      ],
      child: const SfeduEconApp(),
    );

void main() {
  testWidgets('четыре вкладки в нижней панели', (tester) async {
    await tester.pumpWidget(_appWithGroup());
    await tester.pumpAndSettle();

    expect(find.text('Расписание'), findsWidgets);
    expect(find.text('Новости'), findsOneWidget);
    expect(find.text('Помощник'), findsOneWidget);
    expect(find.text('Контакты'), findsOneWidget);
  });

  testWidgets('переключение вкладок работает', (tester) async {
    await tester.pumpWidget(_appWithGroup());
    await tester.pumpAndSettle();

    await tester.tap(find.text('Новости'));
    await tester.pumpAndSettle();
    expect(find.text('Здесь будут новости'), findsOneWidget);

    await tester.tap(find.text('Контакты'));
    await tester.pumpAndSettle();
    expect(find.text('Здесь будет справочник'), findsOneWidget);
  });
}
