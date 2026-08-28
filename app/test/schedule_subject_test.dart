import 'package:flutter_test/flutter_test.dart';
import 'package:sfedu_econ/features/schedule/lesson.dart';

void main() {
  test('длинный вариант курса по выбору в карточке подписан как МУАМ', () {
    expect(
      scheduleSubjectLabel(
        'МУАМ — Современные платформы для построения корп. инф. систем',
      ),
      'МУАМ',
    );
  });

  test('обычный предмет не переименовывается на клиенте', () {
    expect(scheduleSubjectLabel('Эконометрика'), 'Эконометрика');
  });
}
