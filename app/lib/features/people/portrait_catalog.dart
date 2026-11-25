part 'portrait_catalog.g.dart';

String _normalizedName(String name) => name
    .trim()
    .toLowerCase()
    .replaceAll('ё', 'е')
    .replaceAll(RegExp(r'\s+'), ' ');

/// Identity and name must still match the reviewed directory snapshot.
String? portraitAssetFor(String personId, String fullName) {
  final portrait = _bundledPortraits[personId];
  if (portrait == null ||
      _normalizedName(portrait.fullName) != _normalizedName(fullName)) {
    return null;
  }
  return portrait.assetPath;
}
