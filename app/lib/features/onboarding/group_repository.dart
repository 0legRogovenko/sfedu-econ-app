import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api_client.dart';

class Group {
  const Group({
    required this.id,
    required this.course,
    required this.number,
    required this.subgroupCount,
  });

  final int id;
  final int course;
  final String number;
  final int subgroupCount;

  factory Group.fromJson(Map<String, dynamic> json) => Group(
        id: json['id'] as int,
        course: json['course'] as int,
        number: json['number'] as String,
        subgroupCount: json['subgroup_count'] as int,
      );
}

/// Список групп с бэкенда. В тестах переопределяется оверрайдом.
final groupsProvider = FutureProvider<List<Group>>((ref) async {
  final dio = ref.watch(dioProvider);
  final response = await dio.get<List<dynamic>>('/api/groups');
  return (response.data ?? [])
      .map((item) => Group.fromJson(item as Map<String, dynamic>))
      .toList();
});
