import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'api_origin.dart';

export 'api_origin.dart';

const configuredApiBaseUrl = String.fromEnvironment('API_BASE_URL');

class ReleaseConfig {
  const ReleaseConfig({required this.apiBaseUrl});

  final String apiBaseUrl;
}

ReleaseConfig loadReleaseConfig({
  String configured = configuredApiBaseUrl,
  bool requireHttps = kReleaseMode || kProfileMode,
}) {
  return ReleaseConfig(
    apiBaseUrl: resolveApiBaseUrl(
      configured: configured,
      requireHttps: requireHttps,
    ),
  );
}

final releaseConfigProvider = Provider<ReleaseConfig>((ref) {
  return loadReleaseConfig();
});
