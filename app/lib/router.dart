import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'features/assistant/assistant_screen.dart';
import 'features/contacts/contacts_screen.dart';
import 'features/exams/exams_screen.dart';
import 'features/news/news_detail_screen.dart';
import 'features/news/news_item.dart';
import 'features/news/news_screen.dart';
import 'features/onboarding/onboarding_screen.dart';
import 'features/onboarding/selected_group.dart';
import 'features/schedule/schedule_screen.dart';
import 'features/settings/settings_screen.dart';
import 'features/teachers/teacher.dart';
import 'features/teachers/teacher_schedule_screen.dart';
import 'features/teachers/teacher_search_screen.dart';

final routerProvider = Provider<GoRouter>((ref) {
  // ref.read, не watch: роутер создаётся один раз на старте; после выбора
  // группы онбординг сам делает context.go('/schedule')
  final hasGroup = ref.read(selectedGroupIdProvider) != null;
  return GoRouter(
    initialLocation: hasGroup ? '/schedule' : '/onboarding',
    redirect: (context, state) {
      final hasGroup = ref.read(selectedGroupIdProvider) != null;
      final onOnboarding = state.matchedLocation == '/onboarding';
      if (!hasGroup && !onOnboarding) return '/onboarding';
      if (hasGroup && onOnboarding) return '/schedule';
      return null;
    },
    routes: [
      GoRoute(
        path: '/onboarding',
        builder: (context, state) => const OnboardingScreen(),
      ),
      StatefulShellRoute.indexedStack(
        builder: (context, state, shell) => _ShellScaffold(shell: shell),
        branches: [
          StatefulShellBranch(routes: [
            GoRoute(
              path: '/schedule',
              builder: (context, state) => const ScheduleScreen(),
            ),
          ]),
          StatefulShellBranch(routes: [
            GoRoute(
              path: '/news',
              builder: (context, state) => const NewsScreen(),
            ),
          ]),
          StatefulShellBranch(routes: [
            GoRoute(
              path: '/assistant',
              builder: (context, state) => const AssistantScreen(),
            ),
          ]),
          StatefulShellBranch(routes: [
            GoRoute(
              path: '/contacts',
              builder: (context, state) => const ContactsScreen(),
            ),
          ]),
        ],
      ),
      GoRoute(
        path: '/news/detail',
        builder: (context, state) =>
            NewsDetailScreen(item: state.extra! as NewsItem),
      ),
      GoRoute(
        path: '/exams',
        builder: (context, state) => const ExamsScreen(),
      ),
      GoRoute(
        path: '/settings',
        builder: (context, state) => const SettingsScreen(),
      ),
      GoRoute(
        path: '/teachers',
        builder: (context, state) => const TeacherSearchScreen(),
      ),
      // Преподаватель передаётся объектом (extra), а не id в пути: ФИО нужно
      // в заголовке сразу, а отдельной ручки «преподаватель по id» нет.
      GoRoute(
        path: '/teachers/schedule',
        builder: (context, state) =>
            TeacherScheduleScreen(teacher: state.extra! as Teacher),
      ),
    ],
  );
});

class _ShellScaffold extends StatelessWidget {
  const _ShellScaffold({required this.shell});

  final StatefulNavigationShell shell;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: shell,
      bottomNavigationBar: NavigationBar(
        selectedIndex: shell.currentIndex,
        onDestinationSelected: shell.goBranch,
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.calendar_today_outlined),
            selectedIcon: Icon(Icons.calendar_today),
            label: 'Расписание',
          ),
          NavigationDestination(
            icon: Icon(Icons.newspaper_outlined),
            selectedIcon: Icon(Icons.newspaper),
            label: 'Новости',
          ),
          NavigationDestination(
            icon: Icon(Icons.chat_bubble_outline),
            selectedIcon: Icon(Icons.chat_bubble),
            label: 'Помощник',
          ),
          NavigationDestination(
            icon: Icon(Icons.people_outline),
            selectedIcon: Icon(Icons.people),
            label: 'Контакты',
          ),
        ],
      ),
    );
  }
}
