import 'package:flutter/material.dart';

// TODO(Task 4): смена группы, тема, «О приложении».
class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Настройки')),
      body: const Center(child: Text('Здесь будут настройки')),
    );
  }
}
