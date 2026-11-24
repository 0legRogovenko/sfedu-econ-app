import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

void main() {
  test('iOS deployment target is supported by the release Xcode toolchain', () {
    final project = File(
      'ios/Runner.xcodeproj/project.pbxproj',
    ).readAsStringSync();

    expect(project, isNot(contains('IPHONEOS_DEPLOYMENT_TARGET = 13.0;')));
    expect(
      RegExp(
        r'IPHONEOS_DEPLOYMENT_TARGET = 15\.0;',
      ).allMatches(project),
      hasLength(3),
    );
  });
}
