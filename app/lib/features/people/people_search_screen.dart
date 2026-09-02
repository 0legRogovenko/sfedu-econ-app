import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'people_providers.dart';
import 'person.dart';

/// Поиск человека ради его расписания (открывается из экрана расписания).
/// Тот же единый список людей, что на вкладке «Контакты», но показываем
/// только тех, у кого расписание есть, и тап ведёт СРАЗУ к расписанию —
/// пользователь пришёл именно за ним.
class PeopleSearchScreen extends ConsumerStatefulWidget {
  const PeopleSearchScreen({super.key});

  @override
  ConsumerState<PeopleSearchScreen> createState() => _PeopleSearchScreenState();
}

class _PeopleSearchScreenState extends ConsumerState<PeopleSearchScreen> {
  final _controller = TextEditingController();
  String _query = '';

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final peopleAsync = ref.watch(peopleProvider);

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
            child: peopleAsync.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (error, _) => const Center(
                child: Padding(
                  padding: EdgeInsets.symmetric(horizontal: 24),
                  child: Text(
                    'Не удалось загрузить список. Нужна сеть',
                    textAlign: TextAlign.center,
                  ),
                ),
              ),
              data: (people) {
                final found = filterPeople(
                  people.where((p) => p.hasSchedule).toList(),
                  _query,
                );
                if (found.isEmpty) {
                  return const Center(child: Text('Никого не нашлось'));
                }
                return ListView.builder(
                  itemCount: found.length,
                  itemBuilder: (context, index) => ListTile(
                    title: Text(found[index].shortName),
                    onTap: () =>
                        context.push('/people/schedule', extra: found[index]),
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
