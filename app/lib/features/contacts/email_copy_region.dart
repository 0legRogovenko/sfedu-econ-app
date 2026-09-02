import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

class EmailCopyRegion extends StatelessWidget {
  const EmailCopyRegion({super.key, required this.email, required this.child});

  final String email;
  final Widget child;

  Future<void> _copy(BuildContext context) async {
    await Clipboard.setData(ClipboardData(text: email));
    if (!context.mounted) return;

    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(
        const SnackBar(
          content: Text('Почта скопирована'),
          duration: Duration(seconds: 2),
        ),
      );
  }

  @override
  Widget build(BuildContext context) => GestureDetector(
    behavior: HitTestBehavior.opaque,
    onLongPress: () => _copy(context),
    child: child,
  );
}
