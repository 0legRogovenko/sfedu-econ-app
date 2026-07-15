import 'package:drift/drift.dart';

import '../../core/db.dart';
import 'contact.dart';
import 'contacts_api.dart';

/// Состояние справочника контактов.
class ContactsFeed {
  const ContactsFeed({required this.items, required this.offline});

  final List<Contact> items;
  final bool offline; // последний refresh не удался — показан кэш
}

class ContactsRepository {
  ContactsRepository(this._api, this._db);

  final ContactsApi _api;
  final AppDatabase _db;

  Contact _fromRow(CachedContact r) => Contact(
        id: r.id,
        section: r.section,
        name: r.name,
        role: r.role,
        office: r.office,
        email: r.email,
        phone: r.phone,
        officeHours: r.officeHours,
      );

  CachedContactsCompanion _toRow(Contact c) => CachedContactsCompanion.insert(
        id: Value(c.id),
        section: c.section,
        name: c.name,
        role: Value(c.role),
        office: Value(c.office),
        email: Value(c.email),
        phone: Value(c.phone),
        officeHours: Value(c.officeHours),
      );

  /// Начальное состояние из кэша (мгновенно, до первого refresh).
  Future<ContactsFeed> loadCached() async {
    final rows = await _db.allContacts();
    return ContactsFeed(items: rows.map(_fromRow).toList(), offline: false);
  }

  /// Загружает справочник целиком, заменяет кэш.
  /// Ошибка сети -> offline, кэш цел.
  Future<ContactsFeed> refresh() async {
    final data = await _api.fetchContacts();
    if (data == null) {
      final rows = await _db.allContacts();
      return ContactsFeed(items: rows.map(_fromRow).toList(), offline: true);
    }
    final items = data.map(Contact.fromJson).toList();
    await _db.replaceContactsCache(items.map(_toRow).toList());
    return ContactsFeed(items: items, offline: false);
  }
}
