import 'dart:io' show Platform;

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// Палитра из дизайн-спеки (раздел 5.3): цвета сайта ЮФУ.
abstract final class AppColors {
  static const sfeduRed = Color(0xFFCD3519); // красный ЮФУ
  static const sfeduRedDark = Color(0xFFFF7A5C); // осветлённый для тёмной темы
  static const graphite = Color(0xFF353E47); // графит шапки sfedu.ru
  static const lightBackground = Color(0xFFF4F4F5);
  static const lightSurface = Color(0xFFFFFFFF);
  static const lightText = Color(0xFF1C1E21);
  static const darkBackground = Color(0xFF14171B);
  static const darkSurface = Color(0xFF1F252C);
  static const darkText = Color(0xFFECEDEE);
}

/// В `flutter test` HTTP-запросы всегда блокируются (TestWidgetsFlutterBinding
/// возвращает 400 на любой сетевой запрос), а Golos Text не забандлен как
/// ассет. google_fonts (8.x) в этом случае не просто откатывается на
/// fallback-шрифт: неудачная фоновая загрузка шрифта — это future, которую
/// пакет сам не awaits (`.then()` без onError), поэтому её ошибка всегда
/// всплывает как необработанная — независимо от того, ждём мы её в тесте
/// или нет. Единственный надёжный способ не ловить эту ошибку — не запускать
/// загрузку вовсе. Флаг FLUTTER_TEST — тот же публичный сигнал, которым
/// google_fonts помечает свои собственные тестовые сообщения об ошибках
/// (см. google_fonts/src/file_io.dart, isTest), поэтому используем его же.
final bool _isFlutterTest = Platform.environment.containsKey('FLUTTER_TEST');

TextTheme _textTheme(TextTheme base) =>
    _isFlutterTest ? base : GoogleFonts.golosTextTextTheme(base);

ThemeData buildLightTheme() {
  final scheme = ColorScheme.fromSeed(
    seedColor: AppColors.sfeduRed,
    brightness: Brightness.light,
  ).copyWith(
    primary: AppColors.sfeduRed,
    surface: AppColors.lightSurface,
    onSurface: AppColors.lightText,
  );
  final base = ThemeData(brightness: Brightness.light, colorScheme: scheme);
  return base.copyWith(
    scaffoldBackgroundColor: AppColors.lightBackground,
    textTheme: _textTheme(base.textTheme),
    appBarTheme: const AppBarTheme(
      backgroundColor: AppColors.lightSurface,
      foregroundColor: AppColors.lightText,
    ),
  );
}

ThemeData buildDarkTheme() {
  final scheme = ColorScheme.fromSeed(
    seedColor: AppColors.sfeduRedDark,
    brightness: Brightness.dark,
  ).copyWith(
    primary: AppColors.sfeduRedDark,
    surface: AppColors.darkSurface,
    onSurface: AppColors.darkText,
  );
  final base = ThemeData(brightness: Brightness.dark, colorScheme: scheme);
  return base.copyWith(
    scaffoldBackgroundColor: AppColors.darkBackground,
    textTheme: _textTheme(base.textTheme),
    appBarTheme: const AppBarTheme(
      backgroundColor: AppColors.darkSurface,
      foregroundColor: AppColors.darkText,
    ),
  );
}
