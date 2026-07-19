import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:url_launcher/url_launcher.dart';

import '../people/people_providers.dart';
import '../people/person.dart';

/// Единый справочник людей — ОДИН поиск вместо двух (был отдельный по контактам
/// и отдельный по преподавателям расписания). По пустому запросу показываем
/// сотрудников факультета, сгруппированных по секциям (деканат первым). При
/// вводе ищем по ВСЕМ людям, включая общевузовских преподавателей, у которых
/// контакта нет, но есть расписание.
const _deanerySection = 'Деканат';

class ContactsScreen extends ConsumerStatefulWidget {
  const ContactsScreen({super.key});

  @override
  ConsumerState<ContactsScreen> createState() => _ContactsScreenState();
}

class _ContactsScreenState extends ConsumerState<ContactsScreen> {
  String _query = '';

  @override
  Widget build(BuildContext context) {
    final peopleAsync = ref.watch(peopleProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Контакты'),
        actions: [
          IconButton(
            icon: const Icon(Icons.settings),
            tooltip: 'Настройки',
            onPressed: () => context.push('/settings'),
          ),
        ],
      ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(12, 12, 12, 0),
            child: TextField(
              decoration: const InputDecoration(
                hintText: 'Поиск по фамилии',
                prefixIcon: Icon(Icons.search),
                isDense: true,
                border: OutlineInputBorder(),
              ),
              onChanged: (value) => setState(() => _query = value),
            ),
          ),
          Expanded(
            child: peopleAsync.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              // Кэша нет: офлайн честно про сеть, а не пустой справочник.
              error: (error, _) => const Center(
                child: Padding(
                  padding: EdgeInsets.symmetric(horizontal: 24),
                  child: Text(
                    'Не удалось загрузить справочник. Нужна сеть',
                    textAlign: TextAlign.center,
                  ),
                ),
              ),
              data: (people) => _query.trim().isEmpty
                  ? _GroupedDirectory(people: people)
                  : _SearchResults(
                      people: filterPeople(people, _query),
                    ),
            ),
          ),
        ],
      ),
    );
  }
}

/// Пустой запрос: сотрудники по секциям, деканат первым. Внешних
/// преподавателей (без секции) в этом виде не показываем — они находятся
/// поиском; иначе экономфаковский справочник тонул бы в общевузовских именах.
class _GroupedDirectory extends StatelessWidget {
  const _GroupedDirectory({required this.people});

  final List<Person> people;

  @override
  Widget build(BuildContext context) {
    final bySection = <String, List<Person>>{};
    for (final person in people) {
      if (person.sections.isEmpty) continue;
      bySection.putIfAbsent(person.sections.first, () => []).add(person);
    }
    if (bySection.isEmpty) {
      return const Center(child: Text('Справочник пуст'));
    }

    final sections = bySection.keys.toList()
      ..sort((a, b) {
        if (a == _deanerySection) return -1;
        if (b == _deanerySection) return 1;
        return a.compareTo(b);
      });

    return ListView(
      padding: const EdgeInsets.all(12),
      children: [
        for (final section in sections) ...[
          _SectionTitle(section),
          for (final person in bySection[section]!)
            _PersonTile(person: person),
        ],
      ],
    );
  }
}

class _SearchResults extends StatelessWidget {
  const _SearchResults({required this.people});

  final List<Person> people;

  @override
  Widget build(BuildContext context) {
    if (people.isEmpty) {
      return const Center(child: Text('Никого не нашли'));
    }
    return ListView(
      padding: const EdgeInsets.all(12),
      children: [for (final person in people) _PersonTile(person: person)],
    );
  }
}

class _SectionTitle extends StatelessWidget {
  const _SectionTitle(this.text);

  final String text;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Text(
        text,
        style: theme.textTheme.titleSmall?.copyWith(
          color: theme.colorScheme.primary,
          fontWeight: FontWeight.bold,
        ),
      ),
    );
  }
}

class _PersonTile extends StatelessWidget {
  const _PersonTile({required this.person});

  final Person person;

  Future<void> _email(BuildContext context) async {
    try {
      final ok = await launchUrl(
        Uri.parse('mailto:${person.email}'),
        mode: LaunchMode.externalApplication,
      );
      if (!ok && context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Не удалось открыть почту')),
        );
      }
    } catch (_) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Не удалось открыть почту')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    // Подпись: должность, а у внешнего преподавателя без должности — намёк, что
    // у человека есть расписание.
    final subtitle = person.roles.isNotEmpty
        ? person.roles.join(' · ')
        : (person.hasSchedule ? 'Преподаватель' : null);

    return Card(
      child: ListTile(
        title: Text(person.shortName),
        subtitle: subtitle == null ? null : Text(subtitle),
        // Кнопка письма прямо в списке — частый сценарий, не заставляем
        // открывать карточку ради одного тапа.
        trailing: person.email != null
            ? IconButton(
                icon: const Icon(Icons.email_outlined),
                tooltip: 'Написать письмо',
                onPressed: () => _email(context),
              )
            : (person.hasSchedule
                ? const Icon(Icons.chevron_right)
                : null),
        onTap: () => context.push('/people/person', extra: person),
      ),
    );
  }
}
