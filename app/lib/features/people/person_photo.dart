import 'package:flutter/material.dart';

import 'person.dart';

/// A rectangular official portrait; missing or failed images never block a profile.
class PersonPhoto extends StatelessWidget {
  const PersonPhoto({super.key, required this.person});

  final Person person;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    // Take the initials after the surname, including compound surnames.
    final initials = person.shortName
        .trim()
        .split(RegExp(r'\s+'))
        .last
        .replaceAll(RegExp(r'[^А-ЯЁA-Z]', caseSensitive: false), '')
        .toUpperCase();
    final fallback = Center(
      child: Text(
        initials.length <= 2 && initials.isNotEmpty ? initials : '—',
        style: theme.textTheme.displaySmall?.copyWith(
          color: theme.colorScheme.onSurfaceVariant,
        ),
      ),
    );
    final url = person.photoUrl;
    final hasPhoto = url != null && Uri.tryParse(url)?.scheme == 'https';

    return Align(
      alignment: Alignment.centerLeft,
      child: SizedBox(
        key: const Key('person-photo-frame'),
        width: 180,
        child: AspectRatio(
          aspectRatio: 3 / 4,
          child: ClipRRect(
            borderRadius: BorderRadius.circular(12),
            child: ColoredBox(
              color: theme.colorScheme.surfaceContainerHighest,
              child: hasPhoto
                  ? Image.network(
                      url,
                      fit: BoxFit.contain,
                      cacheWidth: 540,
                      semanticLabel: 'Фотография: ${person.fullName}',
                      frameBuilder: (context, child, frame, loaded) =>
                          frame == null ? fallback : child,
                      errorBuilder: (context, error, stackTrace) => fallback,
                    )
                  : fallback,
            ),
          ),
        ),
      ),
    );
  }
}
