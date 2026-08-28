import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/prefs.dart';
import '../onboarding/selected_group.dart';

const _prefsPrefix = 'muam_of_';

/// Выбранная дисциплина блока МУАМ по группам. Полное название служит
/// локальным ключом и позволяет карточке показать конкретный выбранный курс.
class MuamFilters extends Notifier<Map<int, String>> {
  @override
  Map<int, String> build() {
    final prefs = ref.read(sharedPreferencesProvider);
    final result = <int, String>{};
    for (final key in prefs.getKeys()) {
      if (!key.startsWith(_prefsPrefix)) continue;
      final groupId = int.tryParse(key.substring(_prefsPrefix.length));
      final subject = groupId == null ? null : prefs.getString(key);
      if (subject != null && subject.isNotEmpty) result[groupId!] = subject;
    }
    return result;
  }

  Future<void> set(int groupId, String? subject) async {
    final prefs = ref.read(sharedPreferencesProvider);
    final key = '$_prefsPrefix$groupId';
    final next = {...state};
    if (subject == null) {
      next.remove(groupId);
      await prefs.remove(key);
    } else {
      next[groupId] = subject;
      await prefs.setString(key, subject);
    }
    state = next;
  }
}

final muamFiltersProvider = NotifierProvider<MuamFilters, Map<int, String>>(
  MuamFilters.new,
);

final activeMuamSubjectProvider = Provider<String?>((ref) {
  final groupId = ref.watch(selectedGroupIdProvider);
  if (groupId == null) return null;
  return ref.watch(muamFiltersProvider)[groupId];
});
