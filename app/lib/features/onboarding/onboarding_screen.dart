import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'group_picker.dart';
import 'group_repository.dart';
import 'selected_group.dart';

class OnboardingScreen extends ConsumerStatefulWidget {
  const OnboardingScreen({super.key});

  @override
  ConsumerState<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends ConsumerState<OnboardingScreen> {
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
              return Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Spacer(),
                  Text('Привет! 👋',
                      style: Theme.of(context).textTheme.headlineLarge),
                  const SizedBox(height: 8),
                  Text(
                    'Выбери уровень и группу — и всё готово. Без регистрации.',
                    style: Theme.of(context).textTheme.bodyLarge,
                  ),
                  const SizedBox(height: 24),
                  GroupPicker(
                    groups: groups,
                    onSelected: (group) => setState(() => _group = group),
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
