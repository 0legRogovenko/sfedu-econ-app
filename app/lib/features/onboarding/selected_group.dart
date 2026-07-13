import 'package:flutter_riverpod/flutter_riverpod.dart';

/// id выбранной группы; null — группа ещё не выбрана (нужен онбординг).
class SelectedGroupId extends Notifier<int?> {
  @override
  int? build() => null;

  Future<void> select(int groupId) async {
    state = groupId;
  }
}

/// Тестовый вариант с предустановленным значением.
class FakeSelectedGroupId extends SelectedGroupId {
  FakeSelectedGroupId(this._preset);
  final int? _preset;

  @override
  int? build() => _preset;
}

final selectedGroupIdProvider =
    NotifierProvider<SelectedGroupId, int?>(SelectedGroupId.new);
