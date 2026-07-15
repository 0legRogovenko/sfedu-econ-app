import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'news_date.dart';
import 'news_item.dart';
import 'news_providers.dart';
import 'news_repository.dart';

class NewsScreen extends ConsumerStatefulWidget {
  const NewsScreen({super.key});

  @override
  ConsumerState<NewsScreen> createState() => _NewsScreenState();
}

class _NewsScreenState extends ConsumerState<NewsScreen> {
  final _controller = ScrollController();

  @override
  void initState() {
    super.initState();
    _controller.addListener(_onScroll);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _onScroll() {
    // подгрузка при приближении к концу списка
    if (_controller.position.pixels >=
        _controller.position.maxScrollExtent - 400) {
      ref.read(newsFeedProvider.notifier).loadMore();
    }
  }

  @override
  Widget build(BuildContext context) {
    final feedAsync = ref.watch(newsFeedProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Новости')),
      body: feedAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) =>
            const Center(child: Text('Не удалось загрузить новости')),
        data: (feed) => _NewsList(
          feed: feed,
          onRefresh: () => ref.read(newsFeedProvider.notifier).refresh(),
          controller: _controller,
        ),
      ),
    );
  }
}

class _NewsList extends StatelessWidget {
  const _NewsList({
    required this.feed,
    required this.onRefresh,
    required this.controller,
  });

  final NewsFeed feed;
  final Future<void> Function() onRefresh;
  final ScrollController controller;

  @override
  Widget build(BuildContext context) {
    if (feed.items.isEmpty && !feed.offline) {
      return const Center(child: Text('Новостей пока нет'));
    }

    return Column(
      children: [
        if (feed.offline)
          MaterialBanner(
            content: const Text('Нет сети. Показаны сохранённые новости'),
            actions: [
              TextButton(onPressed: onRefresh, child: const Text('Обновить')),
            ],
          ),
        Expanded(
          child: RefreshIndicator(
            onRefresh: onRefresh,
            child: ListView.separated(
              controller: controller,
              padding: const EdgeInsets.all(12),
              itemCount: feed.items.length + (feed.loadingMore ? 1 : 0),
              separatorBuilder: (_, _) => const SizedBox(height: 8),
              itemBuilder: (context, index) {
                if (index >= feed.items.length) {
                  return const Padding(
                    padding: EdgeInsets.all(16),
                    child: Center(child: CircularProgressIndicator()),
                  );
                }
                return _NewsCard(item: feed.items[index]);
              },
            ),
          ),
        ),
      ],
    );
  }
}

class _NewsCard extends StatelessWidget {
  const _NewsCard({required this.item});

  final NewsItem item;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final scheme = theme.colorScheme;
    final isEcon = item.source == 'econ';

    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        // push, не go: go заменял стек — с детального экрана нельзя было
        // вернуться (на iOS вообще некуда), аппаратная «назад» закрывала
        // приложение (итог ревью)
        onTap: () => context.push('/news/detail', extra: item),
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  _Chip(
                    label: item.sourceLabel,
                    color: isEcon ? scheme.primary : scheme.outline,
                  ),
                  if (item.isImportant) ...[
                    const SizedBox(width: 6),
                    _Chip(label: 'Важное', color: scheme.error),
                  ],
                  const Spacer(),
                  Text(
                    formatNewsDate(item.publishedAt),
                    style: theme.textTheme.bodySmall,
                  ),
                ],
              ),
              const SizedBox(height: 6),
              Text(item.title, style: theme.textTheme.titleMedium),
              if (item.body.isNotEmpty) ...[
                const SizedBox(height: 4),
                Text(
                  item.body,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: theme.textTheme.bodySmall,
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _Chip extends StatelessWidget {
  const _Chip({required this.label, required this.color});

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        label,
        style:
            TextStyle(color: color, fontSize: 12, fontWeight: FontWeight.w600),
      ),
    );
  }
}
