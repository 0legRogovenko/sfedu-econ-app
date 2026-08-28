import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sfedu_econ/core/prefs.dart';
import 'package:sfedu_econ/features/onboarding/selected_group.dart';
import 'package:sfedu_econ/features/schedule/muam_filter.dart';

Future<ProviderContainer> _container(Map<String, Object> values) async {
  SharedPreferences.setMockInitialValues(values);
  final prefs = await SharedPreferences.getInstance();
  return ProviderContainer(
    overrides: [
      sharedPreferencesProvider.overrideWithValue(prefs),
      selectedGroupIdProvider.overrideWith(() => FakeSelectedGroupId(3)),
    ],
  );
}

void main() {
  test('выбор МУАМ хранится отдельно для каждой группы', () async {
    final container = await _container({});
    addTearDown(container.dispose);

    await container
        .read(muamFiltersProvider.notifier)
        .set(3, 'МУАМ — Сайтостроение');

    expect(container.read(activeMuamSubjectProvider), 'МУАМ — Сайтостроение');
    expect(
      container.read(sharedPreferencesProvider).getString('muam_of_3'),
      'МУАМ — Сайтостроение',
    );
  });

  test('автоматический выбор удаляет сохранённый фильтр', () async {
    final container = await _container({'muam_of_3': 'МУАМ — Сайтостроение'});
    addTearDown(container.dispose);

    await container.read(muamFiltersProvider.notifier).set(3, null);

    expect(container.read(activeMuamSubjectProvider), isNull);
    expect(
      container.read(sharedPreferencesProvider).containsKey('muam_of_3'),
      isFalse,
    );
  });
}
