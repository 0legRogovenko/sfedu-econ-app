import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

void main() {
  test('Android beta identity and version are frozen', () {
    final gradle = File('android/app/build.gradle.kts').readAsStringSync();
    final manifest = File(
      'android/app/src/main/AndroidManifest.xml',
    ).readAsStringSync();
    final pubspec = File('pubspec.yaml').readAsStringSync();

    expect(gradle, contains('namespace = "ru.olegrogovenko.econapp"'));
    expect(gradle, contains('applicationId = "ru.olegrogovenko.econapp"'));
    expect(manifest, contains('android:label="Эконом ЮФУ"'));
    expect(pubspec, contains('version: 0.1.0-beta.1+1'));
  });

  test('MainActivity follows the release namespace', () {
    final activity = File(
      'android/app/src/main/kotlin/ru/olegrogovenko/econapp/MainActivity.kt',
    );
    final staleActivity = File(
      'android/app/src/main/kotlin/ru/sfedu/econ/sfedu_econ/MainActivity.kt',
    );

    expect(activity.existsSync(), isTrue);
    expect(
      activity.readAsStringSync(),
      contains('package ru.olegrogovenko.econapp'),
    );
    expect(staleActivity.existsSync(), isFalse);
  });

  test('release never falls back to debug signing', () {
    final gradle = File('android/app/build.gradle.kts').readAsStringSync();
    final gitignore = File('../.gitignore').readAsStringSync();

    expect(gradle, isNot(contains('signingConfigs.getByName("debug")')));
    expect(gradle, contains('key.properties'));
    expect(gradle, contains('Release signing requires android/key.properties'));
    expect(gitignore, contains('app/android/key.properties'));
    expect(gitignore, contains('*.jks'));
    expect(gitignore, contains('*.keystore'));
  });

  test('Android beta workflow builds a signed private artifact', () {
    final workflow = File(
      '../.github/workflows/android-beta.yml',
    ).readAsStringSync();

    expect(workflow, contains('workflow_dispatch:'));
    expect(workflow, contains("'beta-v*'"));
    expect(workflow, contains('contents: read'));
    expect(workflow, contains('actions/setup-java@v4'));
    expect(workflow, contains("java-version: '17'"));
    expect(workflow, contains('flutter-version: 3.44.6'));
    expect(workflow, contains(r'vars.BETA_API_BASE_URL'));
    expect(workflow, contains('dart tool/validate_beta_url.dart'));
    expect(workflow, contains('ANDROID_KEYSTORE_BASE64'));
    expect(workflow, contains('ANDROID_KEYSTORE_PASSWORD'));
    expect(workflow, contains('ANDROID_KEY_ALIAS'));
    expect(workflow, contains('ANDROID_KEY_PASSWORD'));
    expect(workflow, contains('flutter analyze'));
    expect(workflow, contains('flutter test'));
    expect(workflow, contains('flutter build apk --release'));
    expect(workflow, contains('sha256sum'));
    expect(workflow, contains('beta-manifest.txt'));
    expect(workflow, contains('actions/upload-artifact@v4'));
    expect(workflow, isNot(contains('action-gh-release')));
    expect(workflow, isNot(contains('gh release')));
  });

  test('beta release and focus-group handoff are documented', () {
    final appReadme = File('README.md').readAsStringSync();
    final testing = File('../BETA_TESTING.md').readAsStringSync();

    expect(appReadme, contains('flutter build apk --release'));
    expect(appReadme, contains('API_BASE_URL'));
    expect(appReadme, contains('key.properties'));
    expect(appReadme, contains('ANDROID_KEYSTORE_BASE64'));
    expect(testing, contains('актуальное расписание'));
    expect(testing, contains('SHA-256'));
    expect(testing, contains('неизвестных источников'));
    expect(testing, contains('Официальное расписание ЮФУ'));
    expect(testing.toLowerCase(), contains('офлайн'));
    expect(testing, contains('Сообщить об ошибке'));
  });
}
