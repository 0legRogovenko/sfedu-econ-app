import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'core/app_version.dart';
import 'core/prefs.dart';
import 'core/release_config.dart';
import 'core/theme.dart';
import 'core/theme_mode.dart';
import 'router.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  late final ReleaseConfig releaseConfig;
  try {
    releaseConfig = loadReleaseConfig();
  } on ReleaseConfigurationException catch (error) {
    runApp(ReleaseConfigurationErrorApp(message: error.message));
    return;
  }
  final prefs = await SharedPreferences.getInstance();
  runApp(
    ProviderScope(
      overrides: [
        sharedPreferencesProvider.overrideWithValue(prefs),
        releaseConfigProvider.overrideWithValue(releaseConfig),
      ],
      child: const SfeduEconApp(),
    ),
  );
}

class ReleaseConfigurationErrorApp extends StatelessWidget {
  const ReleaseConfigurationErrorApp({required this.message, super.key});

  final String message;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Эконом ЮФУ',
      home: Scaffold(
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(32),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.error_outline, size: 56),
                const SizedBox(height: 16),
                const Text('Ошибка конфигурации'),
                const SizedBox(height: 8),
                Text(message, textAlign: TextAlign.center),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class SfeduEconApp extends ConsumerWidget {
  const SfeduEconApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // Версионный гейт: если сервер сказал, что этот build больше не
    // поддерживается, показываем блокирующий экран вместо приложения —
    // несовместимый контракт API опаснее блокировки. Офлайн/сбой проверки
    // НЕ блокирует (см. minBuildProvider).
    if (ref.watch(mustUpdateProvider)) {
      return MaterialApp(
        title: 'Эконом ЮФУ',
        theme: buildLightTheme(),
        darkTheme: buildDarkTheme(),
        themeMode: ref.watch(themeModeProvider),
        home: const UpdateRequiredScreen(),
      );
    }
    final router = ref.watch(routerProvider);
    return MaterialApp.router(
      title: 'Эконом ЮФУ',
      theme: buildLightTheme(),
      darkTheme: buildDarkTheme(),
      themeMode: ref.watch(themeModeProvider),
      routerConfig: router,
    );
  }
}

/// Блокирующий экран «обновите приложение»: показывается, когда сервер
/// объявил текущий build ниже минимально поддерживаемого.
class UpdateRequiredScreen extends StatelessWidget {
  const UpdateRequiredScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      body: Center(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 32),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.system_update_alt,
                  size: 56, color: theme.colorScheme.primary),
              const SizedBox(height: 16),
              Text('Нужно обновление',
                  style: theme.textTheme.headlineSmall,
                  textAlign: TextAlign.center),
              const SizedBox(height: 8),
              const Text(
                'Эта версия приложения устарела и больше не поддерживается. '
                'Обновите «Эконом ЮФУ» в App Store или Google Play.',
                textAlign: TextAlign.center,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
