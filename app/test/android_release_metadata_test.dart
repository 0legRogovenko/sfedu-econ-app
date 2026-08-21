import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

void main() {
  test('Android beta identity and version are frozen', () {
    final gradle = File('android/app/build.gradle.kts').readAsStringSync();
    final manifest =
        File('android/app/src/main/AndroidManifest.xml').readAsStringSync();
    final pubspec = File('pubspec.yaml').readAsStringSync();

    expect(gradle, contains('namespace = "ru.olegrogovenko.econapp"'));
    expect(gradle, contains('applicationId = "ru.olegrogovenko.econapp"'));
    expect(manifest, contains('android:label="Эконом ЮФУ"'));
    expect(pubspec, contains('version: 0.1.0-beta.1+1'));
  });
}
