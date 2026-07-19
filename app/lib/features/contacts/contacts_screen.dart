import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/offline_text.dart';

import '../teachers/teacher.dart';
import '../teachers/teachers_providers.dart';
import 'contact.dart';
import 'contacts_providers.dart';
import 'contacts_repository.dart';
import 'contacts_search.dart';

class ContactsScreen extends ConsumerStatefulWidget {
  const ContactsScreen({super.key});

  @override
  ConsumerState<ContactsScreen> createState() => _ContactsScreenState();
}

class _ContactsScreenState extends ConsumerState<ContactsScreen> {
  String _query = '';

  /// Офлайн-первый: пока в кэше что-то есть — показываем его, даже если
  /// последний ответ сервера был ошибкой. Экран ошибки — только когда
  /// показать нечего (итог ревью).
  Widget _body(AsyncValue<ContactsFeed> feedAsync) {
    // Преподаватели живут не в справочнике, а в расписании: их заводит импорт,
    // а не админ. Показываем их ТОЛЬКО в результатах поиска — иначе 129 голых
    // фамилий без кабинета и почты засорили бы справочник. Зато поиск фамилии
    // перестаёт быть тупиком: раньше он давал «никого не нашли» при том, что
    // приложение знает этого человека и его расписание.
    final teachers = _query.trim().isEmpty
        ? const <Teacher>[]
        : filterTeachers(
            ref.watch(teachersProvider).maybeWhen(
                  data: (list) => list,
                  orElse: () => const <Teacher>[],
                ),
            _query,
          );

    Widget list(ContactsFeed feed) => _ContactsList(
          feed: feed,
          query: _query,
          teachers: teachers,
          onRefresh: () => ref.read(contactsFeedProvider.notifier).refresh(),
        );

    final cached = feedAsync.value;
    if (cached != null && cached.items.isNotEmpty) return list(cached);

    return feedAsync.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (error, _) =>
          const Center(child: Text('Не удалось загрузить контакты')),
      data: list,
    );
  }

  @override
  Widget build(BuildContext context) {
    final feedAsync = ref.watch(contactsFeedProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Контакты'),
        actions: [
          IconButton(
            icon: const Icon(Icons.settings),
            tooltip: 'Настройки',
            // push, не go: go заменяет стек, и аппаратная «назад» закрывала
            // бы приложение вместо возврата к справочнику (итог ревью)
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
                hintText: 'Поиск по имени',
                prefixIcon: Icon(Icons.search),
                isDense: true,
                border: OutlineInputBorder(),
              ),
              onChanged: (value) => setState(() => _query = value),
            ),
          ),
          Expanded(child: _body(feedAsync)),
        ],
      ),
    );
  }
}

class _ContactsList extends StatelessWidget {
  const _ContactsList({
    required this.feed,
    required this.query,
    required this.teachers,
    required this.onRefresh,
  });

  final ContactsFeed feed;
  final String query;

  /// Преподаватели, подошедшие под запрос. Пусто, когда поиска нет.
  final List<Teacher> teachers;

  final Future<void> Function() onRefresh;

  Widget _sectionTitle(BuildContext context, String text) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 8),
        child: Text(
          text,
          style: Theme.of(context).textTheme.titleSmall?.copyWith(
                color: Theme.of(context).colorScheme.primary,
                fontWeight: FontWeight.bold,
              ),
        ),
      );

  /// Карточки преподавателей: контактных полей у них нет (импорт расписания
  /// заводит только ФИО), поэтому единственное, что мы честно можем дать, —
  /// переход к расписанию.
  List<Widget> _teacherSection(BuildContext context) => [
        _sectionTitle(context, 'Преподаватели'),
        for (final teacher in teachers) ...[
          Card(
            child: ListTile(
              title: Text(teacher.fullName),
              subtitle: const Text('Расписание преподавателя'),
              trailing: const Icon(Icons.chevron_right),
              onTap: () =>
                  context.push('/teachers/schedule', extra: teacher),
            ),
          ),
          const SizedBox(height: 8),
        ],
      ];

  @override
  Widget build(BuildContext context) {
    final grouped = groupBySection(filterContacts(feed.items, query));

    final Widget listBody;
    if (grouped.isEmpty && teachers.isNotEmpty) {
      // Контактов не нашлось, но нашёлся преподаватель — это не пустой
      // результат, а другой раздел ответа.
      listBody = ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(12),
        children: _teacherSection(context),
      );
    } else if (grouped.isEmpty) {
      // «Никого не нашли» — только если реально что-то искали. Пустой
      // справочник без запроса при неудачном синке — это «не загрузилось»:
      // кэш был бы непустым, если бы хоть раз загрузился.
      final String message;
      if (query.trim().isNotEmpty) {
        message = 'Никого не нашли';
      } else if (feed.offline) {
        message = noDataText;
      } else {
        message = 'Справочник пуст';
      }
      listBody = ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        children: [
          SizedBox(
            height: 300,
            child: Center(child: Text(message)),
          ),
        ],
      );
    } else {
      listBody = ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(12),
        children: [
          for (final entry in grouped.entries) ...[
            _sectionTitle(context, entry.key),
            for (final contact in entry.value) ...[
              _ContactCard(contact: contact),
              const SizedBox(height: 8),
            ],
          ],
          if (teachers.isNotEmpty) ..._teacherSection(context),
        ],
      );
    }

    return Column(
      children: [
        // Только когда есть что показывать — иначе плашка обещает кэш,
        // которого нет.
        if (feed.offline && feed.items.isNotEmpty)
          MaterialBanner(
            content: const Text('Нет сети. Показаны сохранённые контакты'),
            actions: [
              TextButton(onPressed: onRefresh, child: const Text('Обновить')),
            ],
          ),
        Expanded(
          child: RefreshIndicator(onRefresh: onRefresh, child: listBody),
        ),
      ],
    );
  }
}

/// Открывает внешнее приложение (почта/телефон); если его нет — говорит
/// об этом, а не падает молча (итог ревью).
Future<void> _launchOrTell(
  BuildContext context,
  Uri uri,
  String failureText,
) async {
  try {
    final ok = await launchUrl(uri, mode: LaunchMode.externalApplication);
    if (!ok && context.mounted) {
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text(failureText)));
    }
  } catch (_) {
    if (context.mounted) {
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text(failureText)));
    }
  }
}

class _ContactCard extends StatelessWidget {
  const _ContactCard({required this.contact});

  final Contact contact;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final details = [
      if (contact.office != null) 'ауд. ${contact.office}',
      if (contact.officeHours != null) contact.officeHours!,
    ].join(' · ');

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(contact.name, style: theme.textTheme.titleMedium),
                  if (contact.role != null) ...[
                    const SizedBox(height: 2),
                    Text(contact.role!, style: theme.textTheme.bodySmall),
                  ],
                  if (details.isNotEmpty) ...[
                    const SizedBox(height: 4),
                    Text(details, style: theme.textTheme.bodySmall),
                  ],
                ],
              ),
            ),
            if (contact.email != null)
              IconButton(
                icon: const Icon(Icons.email_outlined),
                tooltip: 'Написать письмо',
                onPressed: () => _launchOrTell(
                  context,
                  Uri.parse('mailto:${contact.email}'),
                  'Не удалось открыть почту',
                ),
              ),
            if (contact.phone != null)
              IconButton(
                icon: const Icon(Icons.call_outlined),
                tooltip: 'Позвонить',
                onPressed: () => _launchOrTell(
                  context,
                  Uri.parse('tel:${contact.phone}'),
                  'Не удалось открыть телефон',
                ),
              ),
          ],
        ),
      ),
    );
  }
}
