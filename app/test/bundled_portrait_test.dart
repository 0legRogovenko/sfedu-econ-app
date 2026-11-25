import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sfedu_econ/features/people/person.dart';
import 'package:sfedu_econ/features/people/person_photo.dart';
import 'package:sfedu_econ/features/people/portrait_catalog.dart';

final _id = base64Url
    .encode(utf8.encode('герасимова\u001fо\u001fя'))
    .replaceAll('=', '');

Person _person({bool known = true}) => Person(
  id: known ? _id : 'unknown',
  shortName: 'Герасимова О.Я.',
  fullName: 'Герасимова Ольга Ярославовна',
  sections: const [],
  roles: const [],
  email: null,
  hasSchedule: false,
  lessonCount: 0,
  examCount: 0,
);

void main() {
  testWidgets('original portrait has no added background or corner crop', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(body: PersonPhoto(person: _person())),
      ),
    );
    final image = tester.widget<Image>(find.byType(Image));
    await tester.runAsync(
      () => precacheImage(image.image, tester.element(find.byType(Image))),
    );
    await tester.pump();
    final frame = find.byKey(const Key('person-photo-frame'));
    expect(
      find.descendant(of: frame, matching: find.byType(ColoredBox)),
      findsNothing,
    );
    expect(
      find.descendant(of: frame, matching: find.byType(ClipRRect)),
      findsNothing,
    );
  });

  test('existing API identity resolves its reviewed bundled portrait', () {
    expect(
      portraitAssetFor(_id, _person().fullName),
      startsWith('assets/people/'),
    );
    expect(portraitAssetFor(_id, 'Герасимова Оксана Яковлевна'), isNull);
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
    expect(find.text('ОЯ'), findsOneWidget);
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
      // Decode the original; a fixed resize can discard detail or upscale it.
      expect(image.image, isA<AssetImage>());
      final provider = image.image is ResizeImage
          ? (image.image as ResizeImage).imageProvider
          : image.image;
      expect(provider, isA<AssetImage>());
      expect(image.fit, BoxFit.contain);
      await tester.runAsync(
        () => precacheImage(image.image, tester.element(find.byType(Image))),
      );
      await tester.pump();
      expect(find.text('ОЯ'), findsNothing);
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
    expect(find.text('ОЯ'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
