import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/prefs.dart';
import 'selected_group.dart';

const _prefsKey = 'favorite_group_ids';

/// Избранные группы (id в порядке добавления). Активная группа — отдельный
/// [selectedGroupIdProvider]: она НЕ обязана быть избранной (пикер в настройках
/// может выбрать любую группу).
///
/// Мягкая миграция: если избранных в prefs ещё нет, текущая группа становится
/// единственной избранной (пользователи до этой версии ничего не настраивали).
class FavoriteGroupIds extends Notifier<List<int>> {
  @override
  List<int> build() {
    final prefs = ref.read(sharedPreferencesProvider);
    final stored = prefs.getStringList(_prefsKey);
    if (stored != null) return stored.map(int.parse).toList();
    final current = ref.read(selectedGroupIdProvider);
    if (current == null) return const []; // онбординг ещё не пройден
    // Сразу закрепляем миграцию в prefs, чтобы она была одноразовой.
    prefs.setStringList(_prefsKey, ['$current']);
    return [current];
  }

  Future<void> _persist(List<int> ids) async {
    state = ids;
    await ref
        .read(sharedPreferencesProvider)
        .setStringList(_prefsKey, [for (final id in ids) '$id']);
  }

  Future<void> add(int groupId) async {
    if (state.contains(groupId)) return;
    await _persist([...state, groupId]);
  }

  /// Удаление избранной. Зафиксированное решение: активную удалить МОЖНО —
  /// активной становится первая из оставшихся избранных. Если оставшихся нет,
  /// активная группа сохраняется (просто перестаёт быть избранной): экран
  /// расписания никогда не остаётся без группы.
  Future<void> remove(int groupId) async {
    final rest = state.where((id) => id != groupId).toList();
    await _persist(rest);
    if (groupId == ref.read(selectedGroupIdProvider) && rest.isNotEmpty) {
      await ref.read(selectedGroupIdProvider.notifier).select(rest.first);
    }
  }
}

final favoriteGroupIdsProvider =
    NotifierProvider<FavoriteGroupIds, List<int>>(FavoriteGroupIds.new);
