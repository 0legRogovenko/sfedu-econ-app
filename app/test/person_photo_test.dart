import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sfedu_econ/features/people/person.dart';
import 'package:sfedu_econ/features/people/person_photo.dart';

const _photo = 'https://econ.sfedu.ru/upload/iblock/photo.jpg';

Person _person({String? photoUrl}) => Person(
  id: 'p1',
  shortName: 'Ищенко-Падукова О.А.',
  fullName: 'Ищенко-Падукова Оксана Александровна',
  sections: const ['Деканат'],
  roles: const [],
  email: 'office@sfedu.ru',
  hasSchedule: false,
  lessonCount: 0,
  examCount: 0,
  photoUrl: photoUrl,
);

void main() {
  test('photo URL is optional for older server responses', () {
    final json = <String, dynamic>{
      'id': 'p1',
      'short_name': 'Вольчик В.В.',
      'full_name': 'Вольчик Вячеслав Витальевич',
    };
    expect(Person.fromJson(json).photoUrl, isNull);
    json['photo_url'] = _photo;
    expect(Person.fromJson(json).photoUrl, _photo);
  });

  testWidgets('missing photo shows initials in a rectangular frame', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(body: PersonPhoto(person: _person())),
      ),
    );
    expect(find.text('ОА'), findsOneWidget);
    expect(find.byType(Image), findsNothing);
    expect(
      tester.getSize(find.byKey(const Key('person-photo-frame'))),
      const Size(180, 240),
    );
    expect(find.byType(ClipOval), findsNothing);
  });

  testWidgets(
    'official portrait keeps the whole source image inside the rectangle',
    (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: PersonPhoto(person: _person(photoUrl: _photo)),
          ),
        ),
      );
      final image = tester.widget<Image>(find.byType(Image));
      final provider = image.image is ResizeImage
          ? (image.image as ResizeImage).imageProvider
          : image.image;
      expect((provider as NetworkImage).url, _photo);
      expect(image.fit, BoxFit.contain);
      expect(
        tester.getSize(find.byKey(const Key('person-photo-frame'))),
        const Size(180, 240),
      );
    },
  );

  testWidgets('a failed image load falls back to initials without a page error', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: PersonPhoto(person: _person(photoUrl: _photo)),
        ),
      ),
    );
    final image = tester.widget<Image>(find.byType(Image));
    // Exercise the same error renderer used by the image stream, without relying
    // on external networking in a widget test.
    final fallback = image.errorBuilder!(
      tester.element(find.byType(Image)),
      Exception('image unavailable'),
      StackTrace.empty,
    );
    await tester.pumpWidget(MaterialApp(home: Scaffold(body: fallback)));
    expect(find.text('ОА'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
