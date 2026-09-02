import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sfedu_econ/core/prefs.dart';
import 'package:sfedu_econ/features/onboarding/selected_group.dart';
import 'package:sfedu_econ/features/schedule/subgroup_filter.dart';

Future<ProviderContainer> _container(Map<String, Object> prefsValues) async {
  SharedPreferences.setMockInitialValues(prefsValues);
  final prefs = await SharedPreferences.getInstance();
  return ProviderContainer(
    overrides: [sharedPreferencesProvider.overrideWithValue(prefs)],
  );
}

void main() {
  test('пустые prefs — фильтров нет', () async {
    final c = await _container({});
    addTearDown(c.dispose);
    expect(c.read(subgroupFiltersProvider), isEmpty);
  });

  test('читает сохранённые фильтры по группам', () async {
    final c = await _container({'subgroup_of_3': 1, 'subgroup_of_4': 2});
    addTearDown(c.dispose);
    expect(c.read(subgroupFiltersProvider), {3: 1, 4: 2});
  });

  test('чужие ключи prefs не попадают в фильтры', () async {
    // Префикс просматривается по всем ключам, поэтому важно, чтобы
    // selected_group_id и прочее не разбирались как groupId.
    final c = await _container({'selected_group_id': 3, 'theme_mode': 'dark'});
    addTearDown(c.dispose);
    expect(c.read(subgroupFiltersProvider), isEmpty);
  });

  test('set сохраняет подгруппу и пишет в prefs', () async {
    final c = await _container({});
    addTearDown(c.dispose);

    await c.read(subgroupFiltersProvider.notifier).set(3, 2);

    expect(c.read(subgroupFiltersProvider), {3: 2});
    expect(c.read(sharedPreferencesProvider).getInt('subgroup_of_3'), 2);
  });

  test('set(null) снимает фильтр и удаляет ключ', () async {
    final c = await _container({'subgroup_of_3': 1});
    addTearDown(c.dispose);

    await c.read(subgroupFiltersProvider.notifier).set(3, null);

    expect(c.read(subgroupFiltersProvider), isEmpty);
    expect(
      c.read(sharedPreferencesProvider).containsKey('subgroup_of_3'),
      isFalse,
    );
  });

  test('фильтр хранится отдельно для каждой группы', () async {
    // Смысл хранения по группам: у разных избранных групп подгруппы разные,
    // и переключение активной не должно уносить чужой выбор.
    final c = await _container({});
    addTearDown(c.dispose);

    await c.read(subgroupFiltersProvider.notifier).set(3, 1);
    await c.read(subgroupFiltersProvider.notifier).set(4, 2);

    expect(c.read(subgroupFiltersProvider), {3: 1, 4: 2});
  });

  group('activeSubgroupProvider', () {
    test('отдаёт фильтр активной группы', () async {
      final c = await _container({
        'selected_group_id': 4,
        'subgroup_of_3': 1,
        'subgroup_of_4': 2,
      });
      addTearDown(c.dispose);
      expect(c.read(activeSubgroupProvider), 2);
    });

    test('у активной группы фильтра нет — null', () async {
      final c = await _container({'selected_group_id': 9, 'subgroup_of_3': 1});
      addTearDown(c.dispose);
      expect(c.read(activeSubgroupProvider), isNull);
    });

    test('группа не выбрана — null', () async {
      final c = await _container({'subgroup_of_3': 1});
      addTearDown(c.dispose);
      expect(c.read(activeSubgroupProvider), isNull);
    });

    test('смена активной группы меняет фильтр', () async {
      final c = await _container({
        'selected_group_id': 3,
        'subgroup_of_3': 1,
        'subgroup_of_4': 2,
      });
      addTearDown(c.dispose);
      expect(c.read(activeSubgroupProvider), 1);

      await c.read(selectedGroupIdProvider.notifier).select(4);

      expect(c.read(activeSubgroupProvider), 2);
    });
  });
}
