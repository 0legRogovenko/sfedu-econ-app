# Teacher Email Copy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Copy a teacher email from either contact surface with a long press and show a visible success message without changing the existing tap-to-email behavior.

**Architecture:** Add one focused `EmailCopyRegion` widget that owns only clipboard writing and success feedback. The contacts list and person card keep their existing `mailto:` handlers and wrap their existing email controls with this shared long-press region.

**Tech Stack:** Flutter 3.44.6, Material widgets, `Clipboard` from `flutter/services.dart`, Flutter widget tests.

---

## File structure

- Create `app/lib/features/contacts/email_copy_region.dart`: shared long-press clipboard behavior and `SnackBar` feedback.
- Modify `app/lib/features/contacts/contacts_screen.dart`: apply the shared behavior to the email icon in the directory list.
- Modify `app/lib/features/people/person_screen.dart`: apply the shared behavior to the visible email button in the person card.
- Modify `app/test/contacts_screen_test.dart`: regression test for list-icon copying.
- Modify `app/test/people_screens_test.dart`: regression test for person-card copying.

### Task 1: Copy email from the contacts list

**Files:**
- Create: `app/lib/features/contacts/email_copy_region.dart`
- Modify: `app/lib/features/contacts/contacts_screen.dart`
- Test: `app/test/contacts_screen_test.dart`

- [ ] **Step 1: Write the failing widget test**

Add `flutter/services.dart` to `contacts_screen_test.dart` and add this test:

```dart
testWidgets('долгое нажатие на иконку копирует email', (tester) async {
  String? copiedText;
  final messenger =
      TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger;
  messenger.setMockMethodCallHandler(SystemChannels.platform, (call) async {
    if (call.method == 'Clipboard.setData') {
      copiedText = (call.arguments as Map<Object?, Object?>)['text'] as String?;
    }
    return null;
  });
  addTearDown(
    () => messenger.setMockMethodCallHandler(SystemChannels.platform, null),
  );

  await tester.pumpWidget(await _app([
    _person(email: 'volchik@sfedu.ru'),
  ]));
  await _openContacts(tester);

  await tester.longPress(find.byIcon(Icons.email_outlined));
  await tester.pump();

  expect(copiedText, 'volchik@sfedu.ru');
  expect(find.text('Почта скопирована'), findsOneWidget);
});
```

- [ ] **Step 2: Run the test and verify RED**

Run:

```bash
cd app
flutter test test/contacts_screen_test.dart \
  --plain-name 'долгое нажатие на иконку копирует email'
```

Expected: FAIL because no `Clipboard.setData` call occurs and the success text is absent.

- [ ] **Step 3: Add the minimal shared clipboard widget**

Create `app/lib/features/contacts/email_copy_region.dart`:

```dart
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

class EmailCopyRegion extends StatelessWidget {
  const EmailCopyRegion({
    super.key,
    required this.email,
    required this.child,
  });

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
```

- [ ] **Step 4: Apply it to the list email icon**

Import `email_copy_region.dart` in `contacts_screen.dart` and replace the email trailing control with:

```dart
trailing: person.email != null
    ? EmailCopyRegion(
        email: person.email!,
        child: IconButton(
          icon: const Icon(
            Icons.email_outlined,
            semanticLabel: 'Написать письмо',
          ),
          onPressed: () => _email(context),
        ),
      )
    : (person.hasSchedule ? const Icon(Icons.chevron_right) : null),
```

Do not retain `IconButton.tooltip`: its touch long-press recognizer would compete with email copying. The icon semantic label preserves the accessibility label.

- [ ] **Step 5: Run the list tests and verify GREEN**

Run:

```bash
cd app
flutter test test/contacts_screen_test.dart
```

Expected: all tests in the file PASS, including clipboard content and the success `SnackBar`.

- [ ] **Step 6: Commit Task 1**

```bash
git add app/lib/features/contacts/email_copy_region.dart \
  app/lib/features/contacts/contacts_screen.dart \
  app/test/contacts_screen_test.dart
git commit -m "feat: copy contact email on long press"
```

### Task 2: Copy email from the person card

**Files:**
- Modify: `app/lib/features/people/person_screen.dart`
- Test: `app/test/people_screens_test.dart`

- [ ] **Step 1: Write the failing person-card test**

Add `flutter/services.dart` to `people_screens_test.dart`. Inside the existing `карточка человека` group, add:

```dart
testWidgets('долгое нажатие на адрес копирует email', (tester) async {
  String? copiedText;
  final messenger =
      TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger;
  messenger.setMockMethodCallHandler(SystemChannels.platform, (call) async {
    if (call.method == 'Clipboard.setData') {
      copiedText = (call.arguments as Map<Object?, Object?>)['text'] as String?;
    }
    return null;
  });
  addTearDown(
    () => messenger.setMockMethodCallHandler(SystemChannels.platform, null),
  );

  const personWithEmail = Person(
    id: 'p-email',
    shortName: 'Вольчик В.В.',
    fullName: 'Вольчик Вячеслав Витальевич',
    sections: ['Экономическая теория'],
    roles: ['доцент'],
    email: 'volchik@sfedu.ru',
    hasSchedule: false,
    lessonCount: 0,
    examCount: 0,
  );
  final container = ProviderContainer();
  addTearDown(container.dispose);
  await _pump(tester, container, const PersonScreen(person: personWithEmail));

  await tester.longPress(find.text('volchik@sfedu.ru'));
  await tester.pump();

  expect(copiedText, 'volchik@sfedu.ru');
  expect(find.text('Почта скопирована'), findsOneWidget);
});
```

- [ ] **Step 2: Run the test and verify RED**

Run:

```bash
cd app
flutter test test/people_screens_test.dart \
  --plain-name 'долгое нажатие на адрес копирует email'
```

Expected: FAIL because the card button has no long-press clipboard behavior.

- [ ] **Step 3: Apply the shared region to the person card**

Import `../contacts/email_copy_region.dart` in `person_screen.dart` and wrap the existing button:

```dart
if (person.email != null)
  EmailCopyRegion(
    email: person.email!,
    child: OutlinedButton.icon(
      onPressed: () => _email(context),
      icon: const Icon(Icons.email_outlined),
      label: Text(person.email!),
    ),
  ),
```

- [ ] **Step 4: Run the person tests and verify GREEN**

Run:

```bash
cd app
flutter test test/people_screens_test.dart
```

Expected: all tests in the file PASS, including exact clipboard content and visible confirmation.

- [ ] **Step 5: Commit Task 2**

```bash
git add app/lib/features/people/person_screen.dart \
  app/test/people_screens_test.dart
git commit -m "feat: copy person email from profile"
```

### Task 3: Full Flutter verification

**Files:**
- Verify only; no production files should change.

- [ ] **Step 1: Run both focused suites together**

```bash
cd app
flutter test test/contacts_screen_test.dart test/people_screens_test.dart
```

Expected: all focused widget tests PASS.

- [ ] **Step 2: Run the complete Flutter test suite**

```bash
cd app
flutter test
```

Expected: `All tests passed!` with zero failures.

- [ ] **Step 3: Run static analysis**

```bash
cd app
flutter analyze
```

Expected: `No issues found!`.

- [ ] **Step 4: Verify the final diff**

```bash
git diff --check origin/main...HEAD
git status --short
```

Expected: no whitespace errors; only the design/plan and email-copy implementation files are tracked changes. Existing untracked `app/build` and `artifacts/` are not staged.
