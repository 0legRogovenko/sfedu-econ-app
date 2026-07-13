import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sfedu_econ/core/theme.dart';

void main() {
  test('светлая тема: палитра ЮФУ', () {
    final theme = buildLightTheme();
    expect(theme.brightness, Brightness.light);
    expect(theme.colorScheme.primary, AppColors.sfeduRed);
    expect(theme.scaffoldBackgroundColor, AppColors.lightBackground);
  });

  test('тёмная тема: осветлённый акцент', () {
    final theme = buildDarkTheme();
    expect(theme.brightness, Brightness.dark);
    expect(theme.colorScheme.primary, AppColors.sfeduRedDark);
    expect(theme.scaffoldBackgroundColor, AppColors.darkBackground);
    expect(theme.colorScheme.surface, AppColors.darkSurface);
  });

  test('цвета соответствуют спеке', () {
    expect(AppColors.sfeduRed, const Color(0xFFCD3519));
    expect(AppColors.sfeduRedDark, const Color(0xFFFF7A5C));
    expect(AppColors.graphite, const Color(0xFF353E47));
    expect(AppColors.lightBackground, const Color(0xFFF4F4F5));
    expect(AppColors.darkBackground, const Color(0xFF14171B));
    expect(AppColors.darkSurface, const Color(0xFF1F252C));
  });
}
