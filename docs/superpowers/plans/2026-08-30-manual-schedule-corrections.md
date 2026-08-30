# Manual Schedule Corrections Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** import the six reviewed 2026/27 schedule PDFs reproducibly, replace the revised first-year master file, apply only source-bound manual lesson corrections, and keep exams empty until an official exam timetable is published.

**Architecture:** Add a fail-closed review bundle containing source hashes, structured lesson corrections, and complete reviewed lesson signatures. The parser runs first and proves its own cell ledger; corrections then transform exact expected lesson states inside the same transaction, after which the full imported document is compared with the reviewed signatures. Both the scheduled importer and the validated-snapshot importer use the same bundle, so a later scheduled run cannot revert manual corrections.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.x, PostgreSQL/SQLite tests, pytest, JSON snapshot assets, existing PDF parser and GitHub Actions workflow.

---

## File map

- Create `backend/src/schedule/reviewed_schedule.py`: strict JSON loading, natural identities, lesson state/signature generation, correction application, source-hash guard, and reviewed-output comparison.
- Modify `backend/src/schedule/importer.py`: accept an optional review bundle, guard fetched hashes, force deterministic re-import for managed documents, apply corrections after ledger proof, and validate reviewed output before commit.
- Modify `backend/src/schedule/validated_snapshot.py`: support manifest version 2 and authenticate the corrections/reviewed-output assets.
- Create `backend/scripts/export_reviewed_schedule.py`: explicit, opt-in writer for reviewed signatures after human PDF comparison.
- Create `backend/tests/test_reviewed_schedule.py`: unit and transactional tests for the review bundle.
- Modify `backend/tests/test_importer.py`: integration tests for scheduled imports, unchanged documents, changed hashes, and rollback.
- Modify `backend/tests/test_validated_snapshot.py`: manifest-v2 integrity, exact-output validation, new counts, and exam exclusion.
- Modify `backend/tests/test_validated_snapshot_workflow.py`: ensure the workflow still imports only the authenticated bundle.
- Create `backend/data/schedule_snapshot/2026-08-30/`: seven PDFs, `corrections.json`, `reviewed_schedule.json`, and manifest v2.
- Modify `backend/tests/test_api_schedule.py` and `backend/tests/test_api_exams.py`: API-level evidence for corrected lessons and zero inferred exams.
- Modify `backend/README.md`: document the reviewed import, stale-hash behavior, and how a future official exam timetable is added.

## Source files fixed by this plan

| Document | Source path | SHA-256 | Action |
|---|---|---|---|
| Bachelor 1 | `/Users/olegrogovenko/Downloads/1 курс.pdf` | `e4532cd0bbe6a3e7a0bd400006a6900689dae04b7cfab58d9e623b4ba4d860fc` | retain reviewed bytes |
| Bachelor 2 | `/Users/olegrogovenko/Downloads/2 курс.pdf` | `fc23269224d9ce84aae67dcccdfe6cb3179ee7b47f02e6c829898ba5dd9328d5` | retain reviewed bytes |
| Bachelor 3 | `/Users/olegrogovenko/Downloads/3 курс.pdf` | `185c61e49950d60ff457e5cce347dab803dc2da1e7021bb636780f48e022446b` | retain reviewed bytes |
| Bachelor 4 | `/Users/olegrogovenko/Downloads/4 курс.pdf` | `311bb1720648d6072265bfcf73b3f0112af335929ecf39ff6fb89b75687e15c4` | retain reviewed bytes |
| Master 1 | `/Users/olegrogovenko/Downloads/1 курс Маг.pdf` | `6ff0e7ec277c22cf99b6c2365e7b2c3771d6d4ad946c07453e1973253a0c41d9` | replace `14159.pdf` |
| Master 2 | `/Users/olegrogovenko/Downloads/2 курс Маг.pdf` | `005fb3145527fd51821823203af05fd3de8841ae5bb4994de7172f062c6afdf8` | retain reviewed bytes |

The existing postgraduate `14174.pdf` remains in the seven-document snapshot but is not part of this six-file correction audit.

### Task 1: Define stable reviewed lesson states

**Files:**
- Create: `backend/src/schedule/reviewed_schedule.py`
- Test: `backend/tests/test_reviewed_schedule.py`

- [ ] **Step 1: Write failing tests for natural identities and complete signatures**

```python
from datetime import date, time

from src.models import EducationLevel, Lesson, LessonKind, WeekType
from src.schedule.reviewed_schedule import GroupIdentity, lesson_state, state_signature


def test_reviewed_signature_contains_every_visible_and_filtering_field(db_session):
    group = Group(
        course=1,
        number=None,
        level=EducationLevel.MASTER,
        program="Корпоративные финансы",
        subgroup_count=1,
    )
    lesson = Lesson(
        group=group,
        weekday=5,
        pair_number=2,
        starts_at=time(9, 50),
        ends_at=time(11, 25),
        subject="Международная экономика",
        lesson_kind=LessonKind.SEMINAR,
        room="209",
        week_type=WeekType.UPPER,
        subgroup=0,
        date_constraint_raw="до 07.10",
        cell_raw="Международная экономика (с) ауд.209",
        cell_key="1:2:3",
        valid_from=date(2026, 9, 1),
        valid_to=date(2026, 10, 7),
        specific_dates=["2026-09-05"],
    )

    state = lesson_state(lesson, p_doc_id="14159")

    assert state.group == GroupIdentity(
        level="master", course=1, number=None, program="Корпоративные финансы"
    )
    assert state_signature(state) == (
        "документ=14159|группа=master/1//Корпоративные финансы|день=5|пара=2|"
        "начало=09:50:00|конец=11:25:00|предмет=Международная экономика|"
        "вид=seminar|препод=|ауд=209|неделя=upper|п/г=0|модуль=|"
        "даты=до 07.10|с=2026-09-01|по=2026-10-07|конкретные=2026-09-05"
    )
```

- [ ] **Step 2: Run the focused test and verify RED**

Run: `cd backend && pytest tests/test_reviewed_schedule.py -q`

Expected: collection fails because `src.schedule.reviewed_schedule` does not exist.

- [ ] **Step 3: Implement immutable JSON-compatible state types**

```python
@dataclass(frozen=True)
class GroupIdentity:
    level: str
    course: int
    number: str | None
    program: str | None


@dataclass(frozen=True)
class ModuleIdentity:
    date_from: date
    date_to: date


@dataclass(frozen=True)
class LessonState:
    p_doc_id: str
    group: GroupIdentity
    weekday: int
    pair_number: int
    starts_at: time
    ends_at: time
    subject: str
    lesson_kind: str | None
    teacher: str | None
    room: str | None
    week_type: str | None
    subgroup: int
    module: ModuleIdentity | None
    date_constraint_raw: str | None
    valid_from: date | None
    valid_to: date | None
    specific_dates: tuple[date, ...]
    cell_raw: str | None


def lesson_state(lesson: Lesson, *, p_doc_id: str) -> LessonState:
    return LessonState(
        p_doc_id=p_doc_id,
        group=GroupIdentity(
            level=lesson.group.level.value,
            course=lesson.group.course,
            number=lesson.group.number,
            program=lesson.group.program,
        ),
        weekday=lesson.weekday,
        pair_number=lesson.pair_number,
        starts_at=lesson.starts_at,
        ends_at=lesson.ends_at,
        subject=lesson.subject,
        lesson_kind=lesson.lesson_kind.value if lesson.lesson_kind else None,
        teacher=lesson.teacher.full_name if lesson.teacher else None,
        room=lesson.room,
        week_type=lesson.week_type.value if lesson.week_type else None,
        subgroup=lesson.subgroup,
        module=(
            ModuleIdentity(lesson.module.date_from, lesson.module.date_to)
            if lesson.module else None
        ),
        date_constraint_raw=lesson.date_constraint_raw,
        valid_from=lesson.valid_from,
        valid_to=lesson.valid_to,
        specific_dates=tuple(
            item if isinstance(item, date) else date.fromisoformat(item)
            for item in lesson.specific_dates
        ),
        cell_raw=lesson.cell_raw,
    )
```

Implement `state_signature()` with the exact field order asserted above. Exclude `cell_raw` from the signature because it is provenance rather than API/filter state; keep it in structured correction evidence.

- [ ] **Step 4: Run the focused tests and verify GREEN**

Run: `cd backend && pytest tests/test_reviewed_schedule.py -q`

Expected: all Task 1 tests pass.

- [ ] **Step 5: Commit Task 1**

```bash
git add backend/src/schedule/reviewed_schedule.py backend/tests/test_reviewed_schedule.py
git commit -m "feat: define reviewed schedule signatures"
```

### Task 2: Load and validate a source-bound correction registry

**Files:**
- Modify: `backend/src/schedule/reviewed_schedule.py`
- Modify: `backend/tests/test_reviewed_schedule.py`

- [ ] **Step 1: Write failing schema and source-guard tests**

```python
def test_registry_rejects_unknown_hash_for_managed_document(tmp_path):
    path = write_registry(
        tmp_path,
        documents=[{
            "p_doc_id": "14159",
            "sha256": "a" * 64,
            "operations": [],
        }],
    )
    registry = load_correction_registry(path)

    with pytest.raises(ReviewValidationError, match="14159.*requires review"):
        registry.guard_source("14159", "b" * 64)


def test_registry_rejects_duplicate_operation_ids(tmp_path):
    operation = {
        "id": "master-room-209",
        "operation": "remove",
        "page": 4,
        "evidence": "reviewed PDF page 4",
        "expected_before": sample_state_json(),
    }
    path = write_registry(
        tmp_path,
        documents=[{
            "p_doc_id": "14159",
            "sha256": "a" * 64,
            "operations": [operation, operation],
        }],
    )

    with pytest.raises(ReviewValidationError, match="duplicate correction id"):
        load_correction_registry(path)
```

Also add parameterized failures for an invalid weekday, pair number, time order, enum value, missing `after`, unexpected `after` on remove, blank evidence, unsafe correction ID, and malformed SHA-256.

- [ ] **Step 2: Run tests and verify RED**

Run: `cd backend && pytest tests/test_reviewed_schedule.py -q`

Expected: failures for missing `load_correction_registry`, `ReviewValidationError`, and guard methods.

- [ ] **Step 3: Implement strict standard-library JSON parsing**

```python
@dataclass(frozen=True)
class CorrectionOperation:
    id: str
    operation: Literal["add", "replace", "remove"]
    page: int
    evidence: str
    expected_before: LessonState | None
    after: LessonState | None


@dataclass(frozen=True)
class DocumentCorrections:
    p_doc_id: str
    sha256: str
    operations: tuple[CorrectionOperation, ...]


@dataclass(frozen=True)
class CorrectionRegistry:
    documents: dict[str, DocumentCorrections]

    def manages(self, p_doc_id: str | int) -> bool:
        return str(p_doc_id) in self.documents

    def guard_source(self, p_doc_id: str | int, sha256: str) -> None:
        document = self.documents.get(str(p_doc_id))
        if document is not None and document.sha256 != sha256:
            raise ReviewValidationError(
                f"document {p_doc_id} changed and requires review"
            )
```

Use explicit key-set checks at every JSON level. Reject unknown keys rather than ignoring spelling errors. Parse ISO dates/times with `date.fromisoformat` and `time.fromisoformat`; validate enum values against `EducationLevel`, `LessonKind`, and `WeekType`.

- [ ] **Step 4: Run tests and verify GREEN**

Run: `cd backend && pytest tests/test_reviewed_schedule.py -q`

Expected: all schema, malformed-input, and source-guard tests pass.

- [ ] **Step 5: Commit Task 2**

```bash
git add backend/src/schedule/reviewed_schedule.py backend/tests/test_reviewed_schedule.py
git commit -m "feat: validate source-bound schedule corrections"
```

### Task 3: Apply corrections transactionally by exact lesson state

**Files:**
- Modify: `backend/src/schedule/reviewed_schedule.py`
- Modify: `backend/tests/test_reviewed_schedule.py`

- [ ] **Step 1: Write failing transactional tests**

```python
def test_replace_requires_exactly_one_expected_lesson(db_session):
    document, lesson = seed_reviewed_lesson(db_session)
    operation = replace_operation(
        expected_before=lesson_state(lesson, p_doc_id=str(document.p_doc_id)),
        after=replace(
            lesson_state(lesson, p_doc_id=str(document.p_doc_id)), room="209"
        ),
    )

    result = apply_document_corrections(
        db_session, document, DocumentCorrections(
            p_doc_id=str(document.p_doc_id),
            sha256=document.sha256,
            operations=(operation,),
        )
    )

    assert result == CorrectionResult(added=0, replaced=1, removed=0)
    assert lesson.room == "209"
    assert lesson.cell_key == "manual:master-room-209"


def test_replace_rolls_back_when_expected_state_is_stale(db_session):
    document, lesson = seed_reviewed_lesson(db_session, room="118")
    operation = replace_operation(
        expected_before=replace(
            lesson_state(lesson, p_doc_id=str(document.p_doc_id)), room="401"
        ),
        after=replace(
            lesson_state(lesson, p_doc_id=str(document.p_doc_id)), room="209"
        ),
    )

    with pytest.raises(ReviewValidationError, match="matched 0 lessons"):
        apply_document_corrections(db_session, document, corrections(operation))

    assert lesson.room == "118"
```

Add tests for add, remove, duplicate slot, two-row ambiguity, missing group, missing module, canonical teacher reuse, and `document_id`/`cell_raw` provenance.

- [ ] **Step 2: Run tests and verify RED**

Run: `cd backend && pytest tests/test_reviewed_schedule.py -q`

Expected: failures because correction application is not implemented.

- [ ] **Step 3: Implement exact matching and mutation**

```python
@dataclass(frozen=True)
class CorrectionResult:
    added: int = 0
    replaced: int = 0
    removed: int = 0


def _matching_lessons(session: Session, document: ScheduleDocument, state: LessonState):
    candidates = session.scalars(
        select(Lesson).where(Lesson.document_id == document.id)
    ).all()
    return [
        lesson for lesson in candidates
        if lesson_state(lesson, p_doc_id=str(document.p_doc_id)) == state
    ]


def apply_document_corrections(
    session: Session,
    document: ScheduleDocument,
    corrections: DocumentCorrections,
) -> CorrectionResult:
    if corrections.sha256 != document.sha256:
        raise ReviewValidationError(
            f"document {document.p_doc_id} changed and requires review"
        )
    result = CorrectionResult()
    for operation in corrections.operations:
        if operation.operation in {"replace", "remove"}:
            matches = _matching_lessons(session, document, operation.expected_before)
            if len(matches) != 1:
                raise ReviewValidationError(
                    f"correction {operation.id} matched {len(matches)} lessons"
                )
            target = matches[0]
            if operation.operation == "remove":
                session.delete(target)
                result = replace(result, removed=result.removed + 1)
            else:
                _write_state(session, document, target, operation.after, operation.id)
                result = replace(result, replaced=result.replaced + 1)
        else:
            target = Lesson(document_id=document.id)
            _write_state(session, document, target, operation.after, operation.id)
            session.add(target)
            result = replace(result, added=result.added + 1)
        session.flush()
    return result
```

`_write_state()` must resolve `Group` by all four identity fields, resolve `Module` by document and exact date range, reuse a canonical `Teacher` row, set every Lesson field, preserve `document_id`, and set `cell_key=f"manual:{operation_id}"` with a validated maximum length.

- [ ] **Step 4: Run tests and verify GREEN**

Run: `cd backend && pytest tests/test_reviewed_schedule.py -q`

Expected: all correction application tests pass on SQLite.

- [ ] **Step 5: Run the same collision cases against PostgreSQL model behavior**

Run: `cd backend && pytest tests/test_models.py tests/test_reviewed_schedule.py -q`

Expected: all tests pass; no migration is generated because existing Lesson columns hold the provenance.

- [ ] **Step 6: Commit Task 3**

```bash
git add backend/src/schedule/reviewed_schedule.py backend/tests/test_reviewed_schedule.py
git commit -m "feat: apply exact manual lesson corrections"
```

### Task 4: Validate complete reviewed document output

**Files:**
- Modify: `backend/src/schedule/reviewed_schedule.py`
- Modify: `backend/tests/test_reviewed_schedule.py`

- [ ] **Step 1: Write failing tests proving counts alone are insufficient**

```python
def test_reviewed_output_rejects_content_drift_with_unchanged_count(db_session):
    document, lesson = seed_reviewed_lesson(db_session, subject="ИКТ")
    expected = reviewed_document_output(db_session, document)
    lesson.subject = "Информационно-коммуникационные технологии"
    db_session.flush()

    with pytest.raises(ReviewValidationError, match="reviewed schedule mismatch"):
        validate_reviewed_document(db_session, document, expected)


def test_reviewed_output_rejects_any_exam_event(db_session):
    document, lesson = seed_reviewed_lesson(db_session)
    db_session.add(ExamEvent(
        group_id=lesson.group_id,
        document_id=document.id,
        subject="Экзамен без официальной даты",
    ))
    db_session.flush()

    with pytest.raises(ReviewValidationError, match="exams must remain empty"):
        reviewed_document_output(db_session, document)
```

- [ ] **Step 2: Run tests and verify RED**

Run: `cd backend && pytest tests/test_reviewed_schedule.py -q`

Expected: failures for missing reviewed-output functions.

- [ ] **Step 3: Implement sorted signatures and focused diffs**

```python
@dataclass(frozen=True)
class ReviewedDocument:
    p_doc_id: str
    sha256: str
    lesson_hash: str
    signatures: tuple[str, ...]


def reviewed_document_output(session: Session, document: ScheduleDocument) -> ReviewedDocument:
    exam_count = session.scalar(
        select(func.count()).select_from(ExamEvent).where(
            ExamEvent.document_id == document.id
        )
    )
    if exam_count:
        raise ReviewValidationError(
            f"document {document.p_doc_id}: exams must remain empty"
        )
    lessons = session.scalars(
        select(Lesson).where(Lesson.document_id == document.id)
    ).all()
    signatures = tuple(sorted(
        state_signature(lesson_state(item, p_doc_id=str(document.p_doc_id)))
        for item in lessons
    ))
    return ReviewedDocument(
        p_doc_id=str(document.p_doc_id),
        sha256=document.sha256,
        lesson_hash=hashlib.sha256("\n".join(signatures).encode()).hexdigest(),
        signatures=signatures,
    )
```

`validate_reviewed_document()` compares source hash, hash-of-signatures, and exact signature tuples. On mismatch, produce a bounded unified diff naming the `p_doc_id`; never rewrite the expected file.

Define the bundle consumed by both import paths in the same module:

```python
@dataclass(frozen=True)
class ReviewBundle:
    corrections: CorrectionRegistry
    reviewed_documents: dict[str, ReviewedDocument]

    def manages(self, p_doc_id: str | int) -> bool:
        return self.corrections.manages(p_doc_id)

    def guard_source(self, p_doc_id: str | int, sha256: str) -> None:
        self.corrections.guard_source(p_doc_id, sha256)

    def apply_and_validate(
        self, session: Session, document: ScheduleDocument
    ) -> CorrectionResult:
        key = str(document.p_doc_id)
        corrections = self.corrections.documents.get(key)
        if corrections is None:
            return CorrectionResult()
        result = apply_document_corrections(session, document, corrections)
        expected = self.reviewed_documents.get(key)
        if expected is None:
            raise ReviewValidationError(f"document {key} has no reviewed output")
        validate_reviewed_document(session, document, expected)
        return result
```

- [ ] **Step 4: Run tests and verify GREEN**

Run: `cd backend && pytest tests/test_reviewed_schedule.py -q`

Expected: exact-content, same-count corruption, source-hash, and exam-exclusion tests pass.

- [ ] **Step 5: Commit Task 4**

```bash
git add backend/src/schedule/reviewed_schedule.py backend/tests/test_reviewed_schedule.py
git commit -m "feat: validate complete reviewed schedule output"
```

### Task 5: Integrate the optional review bundle into the importer core

**Files:**
- Modify: `backend/src/schedule/importer.py:470-618`
- Modify: `backend/tests/test_importer.py`

- [ ] **Step 1: Write failing importer integration tests**

```python
def test_managed_unchanged_document_is_reparsed_and_corrected(db_session, review_bundle):
    fetcher = FakeFetcher()
    first = importer.import_all(db_session, fetcher, review_bundle=review_bundle)
    first_signature = reviewed_signatures(db_session, "14159")

    corrupt_one_managed_lesson(db_session, "14159", room="WRONG")
    db_session.commit()
    second = importer.import_all(db_session, fetcher, review_bundle=review_bundle)

    assert document_report(second, "14159").status == importer.STATUS_REIMPORTED
    assert reviewed_signatures(db_session, "14159") == first_signature


def test_changed_managed_pdf_rolls_back_and_preserves_previous_schedule(
    db_session, review_bundle
):
    importer.import_all(db_session, FakeFetcher(), review_bundle=review_bundle)
    before = reviewed_signatures(db_session, "14159")
    changed = FakeFetcher(overrides={"14159": b"%PDF-1.4\nchanged"})

    report = importer.import_all(db_session, changed, review_bundle=review_bundle)

    assert document_report(report, "14159").status == importer.STATUS_FAILED
    assert reviewed_signatures(db_session, "14159") == before
```

Add an atomic variant that raises and rolls back the entire snapshot.

- [ ] **Step 2: Run tests and verify RED**

Run: `cd backend && pytest tests/test_importer.py -q`

Expected: failures because `review_bundle` is not accepted or loaded.

- [ ] **Step 3: Add the optional import argument and exact ordering**

Change the public signature and both `_import_link` call sites with this exact diff:

```diff
-def import_all(session, fetcher, links=None, *, atomic: bool = False) -> ImportReport:
+def import_all(
+    session,
+    fetcher,
+    links=None,
+    *,
+    atomic: bool = False,
+    review_bundle: ReviewBundle | None = None,
+) -> ImportReport:
@@
-            report.documents.append(_import_link(session, fetcher, link))
+            report.documents.append(
+                _import_link(session, fetcher, link, review_bundle=review_bundle)
+            )
@@
-            report.documents.append(_import_link(session, fetcher, link))
+            report.documents.append(
+                _import_link(session, fetcher, link, review_bundle=review_bundle)
+            )
@@
-def _import_link(session, fetcher, link) -> DocumentReport:
+def _import_link(
+    session, fetcher, link, *, review_bundle: ReviewBundle | None = None
+) -> DocumentReport:
     fetched = fetcher.fetch_document(link.p_doc_id)
+    if review_bundle is not None:
+        review_bundle.guard_source(link.p_doc_id, fetched.sha256)
+    managed = review_bundle is not None and review_bundle.manages(link.p_doc_id)
@@
-    if document is not None and document.sha256 == fetched.sha256:
+    if document is not None and document.sha256 == fetched.sha256 and not managed:
```

Immediately before `if report.status == STATUS_REIMPORTED:`, insert:

```python
    if review_bundle is not None and review_bundle.manages(link.p_doc_id):
        correction_result = review_bundle.apply_and_validate(session, document)
        report.lessons += correction_result.added - correction_result.removed
        session.flush()
```

After parser flush and `report.ledger.prove()`, call corrections and then reviewed validation. Do this before `_snapshot(after)` so `ImportDiff` describes final corrected data. Update `report.lessons` by `added - removed`; replacement leaves the count unchanged.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run: `cd backend && pytest tests/test_importer.py -q`

Expected: managed replay, stale-hash rollback, atomic rollback, and scheduler wiring pass.

- [ ] **Step 5: Run importer mutation guards**

Temporarily change `review_bundle.guard_source(...)` to no-op and verify `test_changed_managed_pdf_rolls_back_and_preserves_previous_schedule` fails. Revert the mutation and rerun the focused tests green.

- [ ] **Step 6: Commit Task 5**

```bash
git add backend/src/schedule/importer.py backend/tests/test_importer.py
git commit -m "feat: enforce reviewed corrections during schedule import"
```

### Task 6: Authenticate manifest-v2 review assets

**Files:**
- Modify: `backend/src/schedule/validated_snapshot.py`
- Modify: `backend/src/schedule/importer.py`
- Modify: `backend/tests/test_validated_snapshot.py`
- Modify: `backend/tests/test_validated_snapshot_workflow.py`
- Modify: `backend/tests/test_scheduler_wiring.py`

- [ ] **Step 1: Write failing manifest-v2 tests**

```python
def test_rejects_modified_corrections_before_touching_database(tmp_path, db_session):
    snapshot_dir = build_v2_snapshot_fixture(tmp_path)
    corrections = snapshot_dir / "corrections.json"
    corrections.write_text(corrections.read_text() + " ", encoding="utf-8")

    with pytest.raises(SnapshotValidationError, match="corrections integrity"):
        import_validated_snapshot(db_session, snapshot_dir)

    assert count_rows(db_session, ScheduleDocument) == 0


def test_rejects_modified_reviewed_output_even_when_counts_match(
    tmp_path, db_session
):
    snapshot_dir = build_v2_snapshot_fixture(tmp_path)
    reviewed = snapshot_dir / "reviewed_schedule.json"
    payload = json.loads(reviewed.read_text())
    payload["documents"]["14159"]["signatures"][0] += "-corrupt"
    rewrite_asset_and_manifest_hash(snapshot_dir, "reviewed_schedule", payload)

    with pytest.raises(SnapshotValidationError, match="reviewed schedule mismatch"):
        import_validated_snapshot(db_session, snapshot_dir)
```

`build_v2_snapshot_fixture()` creates a complete temporary v2 bundle from small test PDFs, corrections, reviewed signatures, and freshly computed asset hashes; Task 6 does not depend on the not-yet-reviewed production snapshot. Also test unknown manifest versions, unsafe asset filenames, undeclared assets, duplicate document IDs, wrong asset SHA, and `expected_counts["exams"] != 0`.

- [ ] **Step 2: Run tests and verify RED**

Run: `cd backend && pytest tests/test_validated_snapshot.py tests/test_validated_snapshot_workflow.py -q`

Expected: failures because manifest v2 and review assets are unsupported.

- [ ] **Step 3: Extend the validated snapshot types and loader**

```python
@dataclass(frozen=True)
class SnapshotAsset:
    path: Path
    content: bytes
    sha256: str


@dataclass(frozen=True)
class ValidatedSnapshot:
    captured_at: str
    expected_counts: dict[str, int]
    documents: tuple[SnapshotDocument, ...]
    review_bundle: ReviewBundle | None
```

Use one `_validated_asset(root, metadata, label)` helper for PDFs, corrections, and reviewed output. Preserve read-only support for legacy manifest v1 until the default snapshot switches in Task 8; v2 requires exact byte count and SHA-256, safe basename-only paths, and exact declared-file equality.

Pass `snapshot.review_bundle` to `import_all(..., atomic=True)`. Compare complete reviewed output before committing, then compare aggregate database counts.

Wire the scheduled importer through the same authenticated default bundle with a local import that avoids a module cycle:

```python
def _default_review_bundle() -> ReviewBundle | None:
    from src.schedule.validated_snapshot import validate_snapshot

    return validate_snapshot().review_bundle


def run_schedule_import(session_factory: Callable = SessionLocal, fetcher=None) -> dict:
    session = session_factory()
    try:
        review_bundle = _default_review_bundle()
        report = import_all(
            session,
            fetcher or Fetcher(),
            review_bundle=review_bundle,
        )
        session.commit()
        return {
            "summary": report.summary(),
            "failed": report.failed,
            "missing": list(report.missing),
        }
    except Exception as exc:
        session.rollback()
        logger.exception("Импорт расписания упал")
        notify_admin(f"Импорт расписания ЮФУ упал: {exc}")
        return {"error": str(exc)}
    finally:
        session.close()
```

Keep the existing logging statement if present. Add a scheduler test that invalid v2 assets produce an error and never call parser-only `import_all()`.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run: `cd backend && pytest tests/test_validated_snapshot.py tests/test_validated_snapshot_workflow.py tests/test_scheduler_wiring.py -q`

Expected: all integrity, rollback, complete-output, and workflow tests pass.

- [ ] **Step 5: Commit Task 6**

```bash
git add backend/src/schedule/validated_snapshot.py backend/src/schedule/importer.py \
  backend/tests/test_validated_snapshot.py backend/tests/test_validated_snapshot_workflow.py \
  backend/tests/test_scheduler_wiring.py
git commit -m "feat: authenticate reviewed schedule bundle"
```

### Task 7: Add a safe parser-baseline and reviewed-output exporter

**Files:**
- Create: `backend/scripts/export_reviewed_schedule.py`
- Create: `backend/tests/test_reviewed_schedule_export.py`

- [ ] **Step 1: Write failing tests for baseline and reviewed modes**

```python
def test_baseline_mode_can_write_only_outside_snapshot(tmp_path):
    output = tmp_path / "parser-baseline.json"
    result = export_main([
        "--snapshot-dir", str(FIXTURE_SNAPSHOT),
        "--output", str(output),
    ])
    assert result == 0
    assert json.loads(output.read_text())["version"] == 1


def test_reviewed_filename_requires_exact_confirmation(tmp_path):
    snapshot = copy_snapshot(tmp_path)
    output = snapshot / "reviewed_schedule.json"

    with pytest.raises(SystemExit, match="rendered-PDF confirmation"):
        export_main([
            "--snapshot-dir", str(snapshot),
            "--output", str(output),
        ])
```

- [ ] **Step 2: Run tests and verify RED**

Run: `cd backend && pytest tests/test_reviewed_schedule_export.py -q`

Expected: collection fails because the exporter does not exist.

- [ ] **Step 3: Implement the two explicit modes**

```python
CONFIRMATION = "I_REVIEWED_EVERY_RENDERED_GROUP"


def export_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--confirm")
    args = parser.parse_args(argv)

    reviewed_target = (
        args.output.resolve()
        == (args.snapshot_dir / "reviewed_schedule.json").resolve()
    )
    if reviewed_target and args.confirm != CONFIRMATION:
        raise SystemExit(
            "refusing reviewed output without rendered-PDF confirmation"
        )
    output = build_reviewed_output(args.snapshot_dir)
    args.output.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return 0
```

The exporter imports into an isolated in-memory database using the supplied correction registry. It never edits PDFs, production data, or `corrections.json`. A parser baseline is written outside the snapshot and is not accepted by manifest validation.

- [ ] **Step 4: Run tests and verify GREEN**

Run: `cd backend && pytest tests/test_reviewed_schedule_export.py -q`

Expected: baseline export works; writing the authoritative reviewed filename without the exact confirmation fails.

- [ ] **Step 5: Commit Task 7**

```bash
git add backend/scripts/export_reviewed_schedule.py backend/tests/test_reviewed_schedule_export.py
git commit -m "test: add explicit reviewed schedule exporter"
```

### Task 8: Audit all rendered PDFs, encode corrections, and publish snapshot v2

**Files:**
- Create: `backend/data/schedule_snapshot/2026-08-30/manifest.json`
- Create: `backend/data/schedule_snapshot/2026-08-30/corrections.json`
- Create after review: `backend/data/schedule_snapshot/2026-08-30/reviewed_schedule.json`
- Create: `backend/data/schedule_snapshot/2026-08-30/14159.pdf`
- Copy: the other six PDFs from `backend/data/schedule_snapshot/2026-08-28/`
- Modify: `backend/src/schedule/validated_snapshot.py` default directory
- Modify: `backend/tests/test_validated_snapshot.py`
- Modify: `backend/tests/test_api_schedule.py`

- [ ] **Step 1: Write a failing test pinning all source hashes and zero exams**

```python
def test_current_review_bundle_is_the_six_supplied_pdfs_plus_postgraduate():
    snapshot = validate_snapshot(DEFAULT_SNAPSHOT_DIR)
    hashes = {item.link.p_doc_id: item.sha256 for item in snapshot.documents}

    assert hashes["14175"] == "e4532cd0bbe6a3e7a0bd400006a6900689dae04b7cfab58d9e623b4ba4d860fc"
    assert hashes["14176"] == "fc23269224d9ce84aae67dcccdfe6cb3179ee7b47f02e6c829898ba5dd9328d5"
    assert hashes["14177"] == "185c61e49950d60ff457e5cce347dab803dc2da1e7021bb636780f48e022446b"
    assert hashes["14178"] == "311bb1720648d6072265bfcf73b3f0112af335929ecf39ff6fb89b75687e15c4"
    assert hashes["14159"] == "6ff0e7ec277c22cf99b6c2365e7b2c3771d6d4ad946c07453e1973253a0c41d9"
    assert hashes["14160"] == "005fb3145527fd51821823203af05fd3de8841ae5bb4994de7172f062c6afdf8"
    assert snapshot.expected_counts["exams"] == 0
```

- [ ] **Step 2: Run the source test and verify RED**

Run: `cd backend && pytest tests/test_validated_snapshot.py::test_current_review_bundle_is_the_six_supplied_pdfs_plus_postgraduate -q`

Expected: failure because default `14159.pdf` still has SHA `cd37c137cd311a25d02211b30e7fe8d2ceb80acda49cab95b76c99097ee97e7e`.

- [ ] **Step 3: Copy immutable PDF bytes into the new snapshot directory**

```bash
mkdir -p backend/data/schedule_snapshot/2026-08-30
cp backend/data/schedule_snapshot/2026-08-28/{14174,14175,14176,14177,14178,14160}.pdf backend/data/schedule_snapshot/2026-08-30/
cp '/Users/olegrogovenko/Downloads/1 курс Маг.pdf' backend/data/schedule_snapshot/2026-08-30/14159.pdf
shasum -a 256 backend/data/schedule_snapshot/2026-08-30/*.pdf
```

Expected: the six supplied-file hashes match the table at the top of this plan; `14174.pdf` retains `5e43a96a3d7031c6cf0f08e9ca2d0e69f40ad27e5c0c9622ffcf4380212df008`.

- [ ] **Step 4: Create the initial managed-document registry**

Create `corrections.json` version 1 with entries for exactly `14175`, `14176`, `14177`, `14178`, `14159`, and `14160`, each pinned to its hash. Start with empty operation arrays. Create a draft manifest v2 containing the seven source-document entries and authenticated corrections metadata but no reviewed-output asset yet. The exporter may read this draft; `validate_snapshot()` must reject it until Step 11 completes the bundle. The postgraduate file is imported but is not managed by this six-file review bundle.

- [ ] **Step 5: Export the parser baseline outside the snapshot**

Run:

```bash
cd backend
python scripts/export_reviewed_schedule.py \
  --snapshot-dir data/schedule_snapshot/2026-08-30 \
  --output /tmp/sfedu-2026-08-30-parser-baseline.json
```

Expected: a deterministic parser-only report with no claim that it has been reviewed. No `reviewed_schedule.json` exists in the snapshot yet.

- [ ] **Step 6: Compare parser output with every rendered group/day block**

Render pages at 180–200 DPI and compare the baseline in this fixed order:

1. `14175` bachelor 1, groups from left to right;
2. `14176` bachelor 2;
3. `14177` bachelor 3, including Saturday MУАМ choices;
4. `14178` bachelor 4, including the separate final group block;
5. `14159` master 1, complete page-by-page comparison because the file changed;
6. `14160` master 2.

For every cell, verify subject, teacher, room, weekday, actual time, week type, subgroup, module window, and specific date constraints. Maintain a review checklist containing every group and every visible day block; completion requires zero unchecked blocks.

- [ ] **Step 7: Write one failing API assertion per demonstrated discrepancy**

Use stable group identity to resolve IDs. The first revised-master check is fixed to the rendered first page:

```python
def test_master_first_course_uses_reviewed_room(client, imported_reviewed_snapshot):
    group_id = master_group_id(
        imported_reviewed_snapshot,
        course=1,
        program="Экономика, управление и право",
    )
    response = client.get(f"/api/schedule?group_id={group_id}")
    assert response.status_code == 200
    matching = [
        lesson for lesson in response.json()["lessons"]
        if lesson["subject"] == "Микроэкономика (продвинутый уровень)"
    ]
    assert matching
    assert {lesson["room"] for lesson in matching} == {"118"}
```

Run each new assertion against the parser-only baseline before adding a correction. Expected: RED only when the demonstrated source discrepancy still exists.

- [ ] **Step 8: Add the narrowest structured correction for each RED assertion**

Append one `replace`, `add`, or `remove` entry. Copy `expected_before` from the baseline, write `after` from the rendered PDF, record the exact page and evidence, and keep the source hash unchanged. Do not add corrections for alignment or text-extraction differences that do not alter API state.

- [ ] **Step 9: Run correction and API tests after every operation**

Run: `cd backend && pytest tests/test_reviewed_schedule.py tests/test_api_schedule.py -q`

Expected: the new source-derived assertion and all fail-closed correction tests pass before moving to the next discrepancy.

- [ ] **Step 10: Write authoritative reviewed output only after the checklist is complete**

Run:

```bash
cd backend
python scripts/export_reviewed_schedule.py \
  --snapshot-dir data/schedule_snapshot/2026-08-30 \
  --output data/schedule_snapshot/2026-08-30/reviewed_schedule.json \
  --confirm I_REVIEWED_EVERY_RENDERED_GROUP
```

Expected: a deterministic reviewed file covering all six managed documents and zero exams.

- [ ] **Step 11: Write manifest v2 and switch the default snapshot**

Set `captured_at` to `2026-08-30`, preserve seven document identities, set `14159.pdf` to 280562 bytes and its new hash, declare the exact byte counts and SHA-256 values of `corrections.json` and `reviewed_schedule.json`, and record the final aggregate database counts. Point `DEFAULT_SNAPSHOT_DIR` to `2026-08-30`.

- [ ] **Step 12: Run manifest, import, and API tests GREEN**

Run:

```bash
cd backend
pytest tests/test_validated_snapshot.py tests/test_reviewed_schedule.py tests/test_api_schedule.py -q
```

Expected: source hashes, asset integrity, exact reviewed signatures, all source-derived corrections, and `exams=0` pass.

- [ ] **Step 13: Prove the correction file is necessary**

If the audit produced operations, temporarily replace operation arrays with empty arrays and verify at least one source-derived API assertion fails. Restore `corrections.json`, verify its SHA in manifest, and rerun the focused suite green. If the audit produced zero operations, pin that fact with `assert sum(len(item.operations) for item in registry.documents.values()) == 0` and keep the source-derived API assertions as proof that replacing `14159.pdf` alone resolves the observed differences.

- [ ] **Step 14: Commit Task 8**

```bash
git add backend/data/schedule_snapshot/2026-08-30 \
  backend/src/schedule/validated_snapshot.py \
  backend/tests/test_validated_snapshot.py backend/tests/test_api_schedule.py
git commit -m "fix: align reviewed schedules with source PDFs"
```

### Task 9: Lock the exam boundary and document operations

**Files:**
- Modify: `backend/tests/test_api_exams.py`
- Modify: `backend/README.md`

- [ ] **Step 1: Add a regression test that curriculum markers do not become exams**

```python
def test_reviewed_semester_snapshot_does_not_infer_exam_events(
    client, imported_reviewed_snapshot
):
    for group in client.get("/api/groups").json():
        response = client.get(f"/api/exams?group_id={group['id']}")
        assert response.status_code == 200
        assert response.json() == []
```

- [ ] **Step 2: Run the exam test GREEN**

Run: `cd backend && pytest tests/test_api_exams.py -q`

Expected: all groups return an empty exam list.

- [ ] **Step 3: Document the operator flow**

Add a `Reviewed schedule corrections` section to `backend/README.md` containing:

```markdown
## Reviewed schedule corrections

The beta schedule is imported from the authenticated snapshot in
`data/schedule_snapshot/2026-08-30`. Manual corrections are not database edits:
they are exact source-hash-bound operations in `corrections.json`.

If SFEDU replaces a managed PDF, the scheduled importer preserves the last
reviewed data and reports `requires review`. Render and review the new PDF,
create a new snapshot revision, update corrections, then regenerate reviewed
output only with the explicit confirmation command documented by the exporter.

Curriculum rows marked `экзамен` are not exam events. Add exams only from a
separate official exam timetable with exact dates and times.
```

- [ ] **Step 4: Run documentation/workflow tests**

Run: `cd backend && pytest tests/test_validated_snapshot_workflow.py tests/test_api_exams.py -q`

Expected: tests pass and the workflow still uses the authenticated snapshot entry point.

- [ ] **Step 5: Commit Task 9**

```bash
git add backend/tests/test_api_exams.py backend/README.md
git commit -m "docs: describe reviewed schedule operations"
```

### Task 10: Full verification and release handoff

**Files:**
- No new production files expected.

- [ ] **Step 1: Run backend formatting and full tests**

Run:

```bash
cd backend
pytest -q
alembic check
```

Expected: all backend tests pass; Alembic reports no pending model changes.

- [ ] **Step 2: Run Flutter static analysis and full tests**

Run:

```bash
cd app
flutter analyze
flutter test
```

Expected: `No issues found` and all Flutter tests pass; no Flutter source change is required for this data-only contract.

- [ ] **Step 3: Import twice into a clean local database**

Run the authenticated snapshot entry point twice against the project database on port 5433. Capture both JSON results.

Expected: identical counts and reviewed hashes after both runs, zero exams, no duplicate lessons, no duplicate teachers, and no connection to PostgreSQL on port 5432.

- [ ] **Step 4: Smoke-check all affected APIs**

Verify `/health` and `/api/groups`, then call `/api/schedule` and `/api/exams` with every concrete group ID returned by `/api/groups`. Compare a sample from every PDF against the committed reviewed signatures.

Expected: all endpoints return 200; schedules match reviewed data; exams are empty.

- [ ] **Step 5: Inspect repository hygiene**

Run:

```bash
git diff --check
git status --short
git log --oneline --decorate -12
```

Expected: only intentional commits, no `.env`, secrets, `app/build`, `.claude`, `CLAUDE.md`, or Graphify artifacts staged or committed.

- [ ] **Step 6: Request production-import approval**

Do not trigger `.github/workflows/backend-validated-snapshot.yml` automatically. Present the exact commit, test counts, snapshot counts, six source hashes, and reviewed correction IDs. Run the production workflow only after the user explicitly approves this specific data import.
