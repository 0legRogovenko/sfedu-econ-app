class ReleaseConfigurationException implements Exception {
  const ReleaseConfigurationException(this.message);

  final String message;

  @override
  String toString() => message;
}

String resolveApiBaseUrl({
  required String configured,
  required bool requireHttps,
}) {
  final value = configured.trim();
  if (value.isEmpty) {
    if (requireHttps) {
      throw const ReleaseConfigurationException(
        'Для release-сборки задайте HTTPS API_BASE_URL.',
      );
    }
    return 'http://localhost:8000';
  }

  final uri = Uri.tryParse(value);
  if (uri == null || !uri.hasScheme || uri.host.isEmpty) {
    throw const ReleaseConfigurationException('API_BASE_URL не является URL.');
  }
  if (uri.userInfo.isNotEmpty ||
      uri.hasQuery ||
      uri.hasFragment ||
      (uri.path.isNotEmpty && uri.path != '/')) {
    throw const ReleaseConfigurationException(
      'API_BASE_URL должен содержать только origin без пути и параметров.',
    );
  }

  final host = uri.host.toLowerCase();
  const localHosts = {'localhost', '127.0.0.1', '::1', '10.0.2.2'};
  if (requireHttps && uri.scheme.toLowerCase() != 'https') {
    throw const ReleaseConfigurationException(
      'Release-сборка принимает только HTTPS API_BASE_URL.',
    );
  }
  if (requireHttps && localHosts.contains(host)) {
    throw const ReleaseConfigurationException(
      'Release-сборка не может использовать локальный API_BASE_URL.',
    );
  }

  return uri.replace(path: '').toString().replaceFirst(RegExp(r'/$'), '');
}
