import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/prefs.dart';
import '../onboarding/selected_group.dart';

const _prefsPrefix = 'subgroup_of_';

/// Выбранная подгруппа по группам: `{groupId: 1|2}`. Отсутствие ключа —
/// «показывать все пары».
///
/// Хранится ПО ГРУППАМ, а не одним значением: у разных избранных групп
/// подгруппы свои, и переключение активной не должно уносить чужой выбор.
class SubgroupFilters extends Notifier<Map<int, int>> {
  @override
  Map<int, int> build() {
    final prefs = ref.read(sharedPreferencesProvider);
    final result = <int, int>{};
    for (final key in prefs.getKeys()) {
      if (!key.startsWith(_prefsPrefix)) continue;
      // tryParse, а не parse: под префиксом лежат только наши записи, но
      // падать всем приложением из-за мусора в prefs незачем.
      final groupId = int.tryParse(key.substring(_prefsPrefix.length));
      final subgroup = groupId == null ? null : prefs.getInt(key);
      if (subgroup != null) result[groupId!] = subgroup;
    }
    return result;
  }

  /// [subgroup] null снимает фильтр (показывать все пары группы).
  Future<void> set(int groupId, int? subgroup) async {
    final prefs = ref.read(sharedPreferencesProvider);
    final key = '$_prefsPrefix$groupId';
    final next = {...state};
    if (subgroup == null) {
      next.remove(groupId);
      await prefs.remove(key);
    } else {
      next[groupId] = subgroup;
      await prefs.setInt(key, subgroup);
    }
    state = next;
  }
}

final subgroupFiltersProvider =
    NotifierProvider<SubgroupFilters, Map<int, int>>(SubgroupFilters.new);

/// Фильтр активной группы — то, что нужно экрану расписания.
/// null = группа не выбрана либо фильтр не задан (видны все пары).
final activeSubgroupProvider = Provider<int?>((ref) {
  final groupId = ref.watch(selectedGroupIdProvider);
  if (groupId == null) return null;
  return ref.watch(subgroupFiltersProvider)[groupId];
});
