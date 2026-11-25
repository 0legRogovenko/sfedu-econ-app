import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sfedu_econ/features/people/person.dart';
import 'package:sfedu_econ/features/people/person_photo.dart';
import 'package:sfedu_econ/features/people/portrait_catalog.dart';

final _id = base64Url
    .encode(utf8.encode('вольчик\u001fв\u001fв'))
    .replaceAll('=', '');

Person _person({bool known = true}) => Person(
  id: known ? _id : 'unknown',
  shortName: 'Вольчик В.В.',
  fullName: 'Вольчик Вячеслав Витальевич',
  sections: const [],
  roles: const [],
  email: null,
  hasSchedule: false,
  lessonCount: 0,
  examCount: 0,
);

void main() {
  test('existing API identity resolves its reviewed bundled portrait', () {
    expect(
      portraitAssetFor(_id, _person().fullName),
      startsWith('assets/people/'),
    );
    expect(portraitAssetFor(_id, 'Вольчик Виктор Владимирович'), isNull);
    expect(portraitAssetFor('unknown', _person().fullName), isNull);
  });

  testWidgets('missing official portrait shows initials in a rectangle', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(body: PersonPhoto(person: _person(known: false))),
      ),
    );
    expect(find.text('ВВ'), findsOneWidget);
    expect(find.byType(Image), findsNothing);
    expect(
      tester.getSize(find.byKey(const Key('person-photo-frame'))),
      const Size(180, 240),
    );
    expect(find.byType(ClipOval), findsNothing);
  });

  testWidgets(
    'real bundled photograph decodes and stays inside its rectangle',
    (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(body: PersonPhoto(person: _person())),
        ),
      );
      final image = tester.widget<Image>(find.byType(Image));
      final provider = image.image is ResizeImage
          ? (image.image as ResizeImage).imageProvider
          : image.image;
      expect(provider, isA<AssetImage>());
      expect(image.fit, BoxFit.contain);
      await tester.runAsync(
        () => precacheImage(image.image, tester.element(find.byType(Image))),
      );
      await tester.pump();
      expect(find.text('ВВ'), findsNothing);
      expect(
        tester.getSize(find.byKey(const Key('person-photo-frame'))),
        const Size(180, 240),
      );
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets('image failure retains the initials fallback', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(body: PersonPhoto(person: _person())),
      ),
    );
    final image = tester.widget<Image>(find.byType(Image));
    final fallback = image.errorBuilder!(
      tester.element(find.byType(Image)),
      Exception('unavailable'),
      StackTrace.empty,
    );
    await tester.pumpWidget(MaterialApp(home: Scaffold(body: fallback)));
    expect(find.text('ВВ'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
