import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sfedu_econ/core/prefs.dart';
import 'package:sfedu_econ/features/onboarding/favorite_groups.dart';
import 'package:sfedu_econ/features/onboarding/selected_group.dart';

Future<ProviderContainer> _container({
  Map<String, Object> prefsValues = const {},
}) async {
  SharedPreferences.setMockInitialValues(prefsValues);
  final prefs = await SharedPreferences.getInstance();
  final container = ProviderContainer(
    overrides: [sharedPreferencesProvider.overrideWithValue(prefs)],
  );
  addTearDown(container.dispose);
  return container;
}

void main() {
  test('мягкая миграция: текущая группа становится единственной избранной',
      () async {
    final container = await _container(prefsValues: {'selected_group_id': 3});

    expect(container.read(favoriteGroupIdsProvider), [3]);
    // миграция сразу закреплена в prefs — второй запуск её не повторяет
    expect(
      container.read(sharedPreferencesProvider).getStringList(
          'favorite_group_ids'),
      ['3'],
    );
  });

  test('без выбранной группы избранных нет (до онбординга)', () async {
    final container = await _container();

    expect(container.read(favoriteGroupIdsProvider), isEmpty);
    expect(
      container.read(sharedPreferencesProvider)
          .getStringList('favorite_group_ids'),
      isNull,
    );
  });

  test('сохранённый список читается как есть, миграция не срабатывает',
      () async {
    final container = await _container(prefsValues: {
      'selected_group_id': 3,
      'favorite_group_ids': ['1', '4'],
    });

    expect(container.read(favoriteGroupIdsProvider), [1, 4]);
  });

  test('add добавляет в конец и пишет в prefs, дубликаты игнорируются',
      () async {
    final container = await _container(prefsValues: {'selected_group_id': 3});

    await container.read(favoriteGroupIdsProvider.notifier).add(5);
    await container.read(favoriteGroupIdsProvider.notifier).add(5);

    expect(container.read(favoriteGroupIdsProvider), [3, 5]);
    expect(
      container.read(sharedPreferencesProvider)
          .getStringList('favorite_group_ids'),
      ['3', '5'],
    );
  });

  test('удаление НЕактивной избранной не трогает активную группу', () async {
    final container = await _container(prefsValues: {'selected_group_id': 3});
    await container.read(favoriteGroupIdsProvider.notifier).add(5);

    await container.read(favoriteGroupIdsProvider.notifier).remove(5);

    expect(container.read(favoriteGroupIdsProvider), [3]);
    expect(container.read(selectedGroupIdProvider), 3);
  });

  test('удаление активной избранной переключает активную на первую оставшуюся',
      () async {
    // Зафиксированное решение: активную избранную удалить МОЖНО, активной
    // становится первая из оставшихся — экран расписания не остаётся без группы.
    final container = await _container(prefsValues: {'selected_group_id': 3});
    await container.read(favoriteGroupIdsProvider.notifier).add(5);

    await container.read(favoriteGroupIdsProvider.notifier).remove(3);

    expect(container.read(favoriteGroupIdsProvider), [5]);
    expect(container.read(selectedGroupIdProvider), 5);
  });

  test('удаление единственной избранной оставляет активную группу как есть',
      () async {
    final container = await _container(prefsValues: {'selected_group_id': 3});

    await container.read(favoriteGroupIdsProvider.notifier).remove(3);

    expect(container.read(favoriteGroupIdsProvider), isEmpty);
    // переключать больше не на что — группа остаётся, просто не избранная
    expect(container.read(selectedGroupIdProvider), 3);
  });
}
