import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api_client.dart';
// databaseProvider переиспользуем из schedule_providers — вся drift-БД живёт
// в одном инстансе (одна и та же локальная база).
import '../schedule/schedule_providers.dart' show databaseProvider;
import 'contacts_api.dart';
import 'contacts_repository.dart';

final contactsApiProvider = Provider<ContactsApi>(
  (ref) => DioContactsApi(ref.watch(dioProvider)),
);

final contactsRepositoryProvider = Provider<ContactsRepository>(
  (ref) => ContactsRepository(
    ref.watch(contactsApiProvider),
    ref.watch(databaseProvider),
  ),
);

/// Справочник контактов: мгновенно из кэша, затем фоновый refresh.
class ContactsFeedNotifier extends AsyncNotifier<ContactsFeed> {
  ContactsRepository get _repo => ref.read(contactsRepositoryProvider);

  @override
  Future<ContactsFeed> build() async {
    final cached = await _repo.loadCached();
    Future.microtask(refresh);
    return cached;
  }

  Future<void> refresh() async {
    // try/catch: refresh дёргается из Future.microtask в build(), где
    // исключение (например, кривой JSON) улетело бы необработанным —
    // показываем ошибку в состоянии (итог ревью)
    try {
      state = AsyncData(await _repo.refresh());
    } catch (error, stack) {
      state = AsyncError(error, stack);
    }
  }
}

final contactsFeedProvider =
    AsyncNotifierProvider<ContactsFeedNotifier, ContactsFeed>(
      ContactsFeedNotifier.new,
    );
