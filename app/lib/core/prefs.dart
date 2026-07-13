import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Переопределяется в main() после асинхронной инициализации
/// и в тестах — mock-значением.
final sharedPreferencesProvider = Provider<SharedPreferences>(
  (ref) => throw UnimplementedError('Переопределяется в main()'),
);
