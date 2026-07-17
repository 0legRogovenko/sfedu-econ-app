import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'group_repository.dart';
import 'selected_group.dart';

class OnboardingScreen extends ConsumerStatefulWidget {
  const OnboardingScreen({super.key});

  @override
  ConsumerState<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends ConsumerState<OnboardingScreen> {
  int? _course;
  Group? _group;

  @override
  Widget build(BuildContext context) {
    final groupsAsync = ref.watch(groupsProvider);

    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: groupsAsync.when(
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (error, _) => _ErrorState(
              onRetry: () => ref.invalidate(groupsProvider),
            ),
            data: (groups) {
              final courses =
                  groups.map((g) => g.course).toSet().toList()..sort();
              final courseGroups = _course == null
                  ? <Group>[]
                  : groups.where((g) => g.course == _course).toList();
              return Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Spacer(),
                  Text('Привет! 👋',
                      style: Theme.of(context).textTheme.headlineLarge),
                  const SizedBox(height: 8),
                  Text(
                    'Выбери курс и группу — и всё готово. Без регистрации.',
                    style: Theme.of(context).textTheme.bodyLarge,
                  ),
                  const SizedBox(height: 24),
                  Wrap(
                    spacing: 8,
                    children: [
                      for (final course in courses)
                        ChoiceChip(
                          label: Text('$course курс'),
                          selected: _course == course,
                          onSelected: (_) => setState(() {
                            _course = course;
                            _group = null;
                          }),
                        ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  Wrap(
                    spacing: 8,
                    children: [
                      for (final group in courseGroups)
                        ChoiceChip(
                          label: Text(group.displayName),
                          selected: _group?.id == group.id,
                          onSelected: (_) => setState(() => _group = group),
                        ),
                    ],
                  ),
                  const Spacer(),
                  SizedBox(
                    width: double.infinity,
                    child: FilledButton(
                      onPressed: _group == null
                          ? null
                          : () async {
                              await ref
                                  .read(selectedGroupIdProvider.notifier)
                                  .select(_group!.id);
                              if (context.mounted) context.go('/schedule');
                            },
                      child: const Text('Начать'),
                    ),
                  ),
                ],
              );
            },
          ),
        ),
      ),
    );
  }
}

class _ErrorState extends StatelessWidget {
  const _ErrorState({required this.onRetry});

  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Text('Не удалось загрузить список групп'),
          const SizedBox(height: 12),
          OutlinedButton(onPressed: onRetry, child: const Text('Повторить')),
        ],
      ),
    );
  }
}
