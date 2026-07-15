import 'contact.dart';

/// Поиск по имени, роли и секции (регистронезависимо).
List<Contact> filterContacts(List<Contact> all, String query) {
  final q = query.trim().toLowerCase();
  if (q.isEmpty) return all;
  return all
      .where((c) =>
          c.name.toLowerCase().contains(q) ||
          (c.role?.toLowerCase().contains(q) ?? false) ||
          c.section.toLowerCase().contains(q))
      .toList();
}

/// Группировка по секциям с сохранением порядка появления
/// (бэкенд уже отдаёт отсортированным).
Map<String, List<Contact>> groupBySection(List<Contact> contacts) {
  final result = <String, List<Contact>>{};
  for (final c in contacts) {
    result.putIfAbsent(c.section, () => []).add(c);
  }
  return result;
}
