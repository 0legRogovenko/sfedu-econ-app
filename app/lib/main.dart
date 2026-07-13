import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'core/theme.dart';

void main() {
  runApp(const ProviderScope(child: SfeduEconApp()));
}

class SfeduEconApp extends StatelessWidget {
  const SfeduEconApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Эконом ЮФУ',
      theme: buildLightTheme(),
      darkTheme: buildDarkTheme(),
      themeMode: ThemeMode.system,
      home: const Scaffold(body: Center(child: Text('Эконом ЮФУ'))),
    );
  }
}
