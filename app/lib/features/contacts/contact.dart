/// Контакт справочника (ответ /api/contacts и строка кэша).
class Contact {
  const Contact({
    required this.id,
    required this.section,
    required this.name,
    required this.role,
    required this.office,
    required this.email,
    required this.phone,
    required this.officeHours,
  });

  final int id;
  final String section;
  final String name;
  final String? role;
  final String? office;
  final String? email;
  final String? phone;
  final String? officeHours;

  factory Contact.fromJson(Map<String, dynamic> json) => Contact(
        id: json['id'] as int,
        section: json['section'] as String,
        name: json['name'] as String,
        role: json['role'] as String?,
        office: json['office'] as String?,
        email: json['email'] as String?,
        phone: json['phone'] as String?,
        officeHours: json['office_hours'] as String?,
      );
}
