import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sfedu_econ/core/api_client.dart';
import 'package:sfedu_econ/core/release_config.dart';
import 'package:sfedu_econ/main.dart';

void main() {
  group('resolveApiBaseUrl', () {
    test('debug without define uses localhost', () {
      expect(
        resolveApiBaseUrl(configured: '', requireHttps: false),
        'http://localhost:8000',
      );
    });

    test('release requires a configured endpoint', () {
      expect(
        () => resolveApiBaseUrl(configured: '', requireHttps: true),
        throwsA(isA<ReleaseConfigurationException>()),
      );
    });

    test('release accepts and normalizes an HTTPS origin', () {
      expect(
        resolveApiBaseUrl(
          configured: ' https://beta.econ.example/ ',
          requireHttps: true,
        ),
        'https://beta.econ.example',
      );
    });

    for (final invalid in [
      'http://beta.econ.example',
      'https://localhost:8000',
      'https://127.0.0.1',
      'https://[::1]',
      'https://10.0.2.2:8000',
      'https://user:pass@beta.econ.example',
      'https://beta.econ.example/api',
      'https://beta.econ.example?debug=1',
      'https://beta.econ.example#fragment',
    ]) {
      test('release rejects $invalid', () {
        expect(
          () => resolveApiBaseUrl(configured: invalid, requireHttps: true),
          throwsA(isA<ReleaseConfigurationException>()),
        );
      });
    }
  });

  test('dioProvider uses the validated config', () {
    final container = ProviderContainer(
      overrides: [
        releaseConfigProvider.overrideWithValue(
          const ReleaseConfig(apiBaseUrl: 'https://beta.econ.example'),
        ),
      ],
    );
    addTearDown(container.dispose);

    final Dio dio = container.read(dioProvider);
    expect(dio.options.baseUrl, 'https://beta.econ.example');
  });

  testWidgets('configuration failure is explicit', (tester) async {
    await tester.pumpWidget(
      const ReleaseConfigurationErrorApp(
        message: 'Для release-сборки задайте HTTPS API_BASE_URL.',
      ),
    );

    expect(find.text('Ошибка конфигурации'), findsOneWidget);
    expect(find.textContaining('HTTPS API_BASE_URL'), findsOneWidget);
  });
}
