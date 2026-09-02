import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/prefs.dart';

const _prefsKey = 'selected_group_id';

/// id выбранной группы; null — группа ещё не выбрана (нужен онбординг).
class SelectedGroupId extends Notifier<int?> {
  @override
  int? build() => ref.read(sharedPreferencesProvider).getInt(_prefsKey);

  Future<void> select(int groupId) async {
    state = groupId;
    await ref.read(sharedPreferencesProvider).setInt(_prefsKey, groupId);
  }
}

/// Тестовый вариант с предустановленным значением (без prefs).
class FakeSelectedGroupId extends SelectedGroupId {
  FakeSelectedGroupId(this._preset);
  final int? _preset;

  @override
  int? build() => _preset;

  @override
  Future<void> select(int groupId) async {
    state = groupId;
  }
}

final selectedGroupIdProvider = NotifierProvider<SelectedGroupId, int?>(
  SelectedGroupId.new,
);
