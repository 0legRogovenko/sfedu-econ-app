import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sfedu_econ/core/device_id.dart';
import 'package:sfedu_econ/core/prefs.dart';

Future<ProviderContainer> _container(SharedPreferences prefs) async {
  final container = ProviderContainer(
    overrides: [sharedPreferencesProvider.overrideWithValue(prefs)],
  );
  addTearDown(container.dispose);
  return container;
}

void main() {
  test('при пустых prefs id создаётся', () async {
    SharedPreferences.setMockInitialValues({});
    final prefs = await SharedPreferences.getInstance();
    final container = await _container(prefs);

    expect(container.read(deviceIdProvider), isNotEmpty);
  });

  test('два чтения дают один и тот же id', () async {
    SharedPreferences.setMockInitialValues({});
    final prefs = await SharedPreferences.getInstance();
    final container = await _container(prefs);

    expect(container.read(deviceIdProvider), container.read(deviceIdProvider));
  });

  test('id переживает перезапуск: второй контейнер читает тот же', () async {
    SharedPreferences.setMockInitialValues({});
    final prefs = await SharedPreferences.getInstance();
    final first = (await _container(prefs)).read(deviceIdProvider);
    // запись в prefs асинхронна — даём ей завершиться, как при реальном старте
    await Future<void>.delayed(Duration.zero);

    final second = (await _container(prefs)).read(deviceIdProvider);
    expect(second, first);
  });
}
