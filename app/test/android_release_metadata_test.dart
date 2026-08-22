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

  test('release never falls back to debug signing', () {
    final gradle = File('android/app/build.gradle.kts').readAsStringSync();
    final gitignore = File('../.gitignore').readAsStringSync();

    expect(gradle, isNot(contains('signingConfigs.getByName("debug")')));
    expect(gradle, contains('key.properties'));
    expect(
      gradle,
      contains('Release signing requires android/key.properties'),
    );
    expect(gitignore, contains('app/android/key.properties'));
    expect(gitignore, contains('*.jks'));
    expect(gitignore, contains('*.keystore'));
  });
}
