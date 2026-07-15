import 'package:dio/dio.dart';

/// Абстракция сетевого доступа к справочнику контактов.
/// В тестах подменяется фейком.
abstract interface class ContactsApi {
  /// null при сетевой ошибке.
  Future<List<Map<String, dynamic>>?> fetchContacts();
}

class DioContactsApi implements ContactsApi {
  DioContactsApi(this._dio);
  final Dio _dio;

  @override
  Future<List<Map<String, dynamic>>?> fetchContacts() async {
    try {
      final response = await _dio.get<List<dynamic>>('/api/contacts');
      return (response.data ?? []).cast<Map<String, dynamic>>();
    } on DioException {
      return null;
    }
  }
}
