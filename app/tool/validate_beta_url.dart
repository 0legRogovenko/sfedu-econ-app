import 'dart:io';

import 'package:sfedu_econ/core/api_origin.dart';

void main(List<String> arguments) {
  if (arguments.length != 1) {
    stderr.writeln(
      'Использование: dart tool/validate_beta_url.dart <HTTPS origin>',
    );
    exitCode = 64;
    return;
  }

  try {
    final origin = resolveApiBaseUrl(
      configured: arguments.single,
      requireHttps: true,
    );
    stdout.writeln(origin);
  } on ReleaseConfigurationException {
    // Never echo the supplied value: it may contain credentials.
    stderr.writeln('Некорректный API_BASE_URL.');
    exitCode = 2;
  }
}
