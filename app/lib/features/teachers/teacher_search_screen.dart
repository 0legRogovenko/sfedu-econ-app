import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'teacher.dart';
import 'teachers_providers.dart';

/// Поиск преподавателя. Фильтр локальный (список маленький), поэтому
/// результаты обновляются на каждый символ без запросов к сети.
class TeacherSearchScreen extends ConsumerStatefulWidget {
  const TeacherSearchScreen({super.key});

  @override
  ConsumerState<TeacherSearchScreen> createState() =>
      _TeacherSearchScreenState();
}

class _TeacherSearchScreenState extends ConsumerState<TeacherSearchScreen> {
  final _controller = TextEditingController();
  String _query = '';

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final teachersAsync = ref.watch(teachersProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Преподаватели')),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(12),
            child: TextField(
              controller: _controller,
              autofocus: true,
              decoration: const InputDecoration(
                prefixIcon: Icon(Icons.search),
                hintText: 'Фамилия преподавателя',
                border: OutlineInputBorder(),
              ),
              onChanged: (value) => setState(() => _query = value),
            ),
          ),
          Expanded(
            child: teachersAsync.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              // Кэша списка нет, поэтому офлайн честно говорим про сеть,
              // а не показываем пустой список как «никого не нашлось».
              error: (error, _) => const Center(
                child: Padding(
                  padding: EdgeInsets.symmetric(horizontal: 24),
                  child: Text(
                    'Не удалось загрузить список преподавателей. '
                    'Нужна сеть',
                    textAlign: TextAlign.center,
                  ),
                ),
              ),
              data: (teachers) {
                final found = filterTeachers(teachers, _query);
                if (found.isEmpty) {
                  return const Center(child: Text('Никого не нашлось'));
                }
                return ListView.builder(
                  itemCount: found.length,
                  itemBuilder: (context, index) => ListTile(
                    title: Text(found[index].fullName),
                    onTap: () => context.push(
                      '/teachers/schedule',
                      extra: found[index],
                    ),
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}
