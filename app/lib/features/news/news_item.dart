/// Новость факультета/университета (ответ /api/news и строка кэша).
class NewsItem {
  const NewsItem({
    required this.id,
    required this.title,
    required this.body,
    required this.source,
    required this.url,
    required this.imageUrl,
    required this.isImportant,
    required this.publishedAt,
  });

  final int id;
  final String title;
  final String body;
  final String source; // 'sfedu' | 'econ'
  final String url;
  final String? imageUrl;
  final bool isImportant;
  final DateTime publishedAt;

  /// Человекочитаемая метка источника для чипа в ленте.
  String get sourceLabel =>
      source == 'econ' ? 'Экономический факультет' : 'ЮФУ';

  factory NewsItem.fromJson(Map<String, dynamic> json) => NewsItem(
    id: json['id'] as int,
    title: json['title'] as String,
    body: json['body'] as String,
    source: json['source'] as String,
    url: json['url'] as String,
    imageUrl: json['image_url'] as String?,
    isImportant: json['is_important'] as bool,
    publishedAt: DateTime.parse(json['published_at'] as String),
  );
}
