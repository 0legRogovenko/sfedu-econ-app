import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import 'news_date.dart';
import 'news_item.dart';

class NewsDetailScreen extends StatelessWidget {
  const NewsDetailScreen({super.key, required this.item});

  final NewsItem item;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(title: const Text('Новости')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text(item.title, style: theme.textTheme.titleLarge),
          const SizedBox(height: 8),
          Text(
            '${item.sourceLabel} · ${formatNewsDate(item.publishedAt)}',
            style: theme.textTheme.bodySmall,
          ),
          const SizedBox(height: 16),
          SelectableText(item.body, style: theme.textTheme.bodyMedium),
          const SizedBox(height: 24),
          OutlinedButton.icon(
            onPressed: () => launchUrl(
              Uri.parse(item.url),
              mode: LaunchMode.externalApplication,
            ),
            icon: const Icon(Icons.open_in_new),
            label: const Text('Открыть на сайте'),
          ),
        ],
      ),
    );
  }
}
