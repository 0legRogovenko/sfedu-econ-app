# Manual Schedule Corrections Design

**Status:** approved approach, pending final user review of this written specification

**Goal:** make the beta schedule match the six reviewed PDF files exactly while keeping every manual change reproducible, source-bound, testable, and safe across re-imports.

## Confirmed decisions

- The six PDF files supplied on 2026-08-30 are the authoritative inputs for this correction round.
- Five files are byte-for-byte identical to the current validated snapshot: bachelor courses 1–4 and master course 2.
- The master course 1 PDF is a new revision and replaces document `p_doc_id=14159` in the validated snapshot.
- Exam events are not inferred from curriculum tables or session date ranges. They remain absent until SFEDU publishes a separate official exam timetable containing exact dates and times.
- Corrections are stored in Git and applied automatically. Direct edits to the beta database are forbidden because they disappear on the next import and cannot be reviewed.
- The generic PDF parser is not broadly changed in this milestone unless a reviewed discrepancy proves a reusable parsing rule. The default correction mechanism is a narrow source-bound patch.

## Chosen architecture

The importer keeps producing its normal parsed result. Before the transaction is committed, a dedicated correction layer applies a versioned set of `add`, `replace`, and `remove` operations. The layer is fail-closed: it applies a correction only to the exact PDF hash and exact previously reviewed lesson signature for which it was written.

This separates two responsibilities:

- the parser remains a reusable interpretation of SFEDU document layouts;
- the correction set records human-reviewed exceptions where the rendered source and parsed result differ.

The same correction engine is used by the validated-snapshot import and the scheduled importer. A corrected document therefore cannot revert to parser-only data merely because the scheduled job runs again.

## Snapshot revision

The current snapshot is copied to a new dated revision rather than edited in place. The new revision:

- retains the five unchanged PDFs and their existing hashes;
- replaces `14159.pdf` with the supplied master course 1 revision;
- updates `captured_at`, file size, SHA-256, and reviewed output counts;
- declares and authenticates the correction file and reviewed-output file;
- keeps `exams=0`.

Snapshot manifest version 2 adds explicit metadata for:

- `corrections_file` and its SHA-256;
- `reviewed_schedule_file` and its SHA-256;
- the exact source hash to which every correction set belongs.

Unexpected files, missing files, and hash mismatches continue to reject the whole import before the database is touched.

## Correction data format

Corrections live in a structured JSON document. Each document block contains:

- stable correction ID;
- `p_doc_id` and exact source PDF SHA-256;
- source page and a short evidence note for human review;
- operation: `add`, `replace`, or `remove`;
- group identity: education level, course, number or master program;
- an `expected_before` signature for `replace` and `remove`;
- the complete `after` lesson for `add` and `replace`.

Lesson data includes every user-visible or filtering field:

- weekday and pair number;
- actual start and end time;
- subject and lesson kind;
- teacher and room;
- upper/lower week marker;
- subgroup;
- module dates, validity window, and specific dates;
- original source-cell text when available.

Database IDs are never stored in the correction file. Groups, modules, teachers, and documents are resolved by stable natural identities during import.

## Fail-closed application rules

The correction engine enforces these rules inside the import transaction:

1. The current document SHA-256 must exactly match the correction block.
2. A `replace` or `remove` selector must match exactly one imported lesson.
3. The matched row must equal `expected_before` across all reviewed fields.
4. An `add` must not duplicate an existing corrected signature or slot.
5. The referenced group and module must already exist in the imported document.
6. Teacher resolution must reuse the project's canonical teacher identity and must not create a duplicate spelling.
7. Corrected rows keep `document_id` and receive deterministic provenance such as `manual:<correction-id>` plus the source text.
8. Any ambiguity, missing target, stale source hash, uniqueness collision, or unexpected count rolls back the entire import.

If SFEDU replaces a PDF under the same `p_doc_id`, old corrections are not guessed onto the new file. The new hash is placed into a review-required state until the rendered document is checked and a new correction revision is committed.

## Review process

The implementation audit compares the rendered PDFs with parser output group by group and day by day. The audit records only demonstrated discrepancies; it does not rewrite correct lessons for consistency or style.

For each difference:

1. identify the source page, group column, day, and time block;
2. capture the parser's complete existing signature, if any;
3. add the narrowest correction operation;
4. rerun the full import;
5. verify the corrected API result against the rendered page;
6. record the final signature in the reviewed output.

The first-course master revision receives a complete old-versus-new audit because it is the only changed PDF in this round. The five unchanged documents are still checked for previously reported discrepancies but are not replaced merely to regenerate data.

## Reviewed output and regression protection

Counts alone are insufficient: a wrong subject can replace a correct one without changing the number of lessons. The new snapshot therefore contains an authenticated reviewed-output JSON with sorted lesson signatures per group and document.

Each signature covers:

- stable group identity;
- document identity;
- weekday, pair, and exact times;
- subject, teacher, room, week type, and subgroup;
- module range, validity range, and specific dates.

Validation compares the imported result with the full reviewed signatures and prints a focused diff on mismatch. Aggregate manifest counts remain as an additional sanity check.

Tests must demonstrate that validation fails when:

- the source PDF changes by one byte;
- a correction's old signature is stale;
- one lesson is silently omitted from a multi-lesson cell;
- a correction targets two rows;
- an add creates a duplicate slot;
- a teacher spelling would create a duplicate person;
- the final lesson content differs while total counts remain unchanged;
- an exam is inferred without a separate exam-timetable source.

## Import and deployment flow

The release flow is:

1. authenticate the revised snapshot and correction assets;
2. parse all source PDFs into a clean transaction;
3. apply only correction blocks matching their exact source hashes;
4. compare aggregate counts and complete reviewed signatures;
5. commit atomically;
6. run schedule and API smoke checks for every affected group;
7. deploy only after backend and Flutter test suites pass.

The production database is not patched manually. Deployment uses the existing authenticated validated-snapshot workflow so a fresh environment and the beta environment produce the same schedule.

## Explicitly out of scope

- creating placeholder exams from curriculum rows marked `экзамен`;
- guessing consultation, exam date, time, room, or format;
- changing unrelated news, contacts, assistant, or Flutter UI behavior;
- accepting arbitrary admin-entered SQL or database IDs in correction data;
- silently regenerating reviewed signatures after a test failure;
- applying an old correction to a newly published PDF.

## Completion criterion

This milestone is complete when the new snapshot imports atomically, all manual operations are tied to exact reviewed PDF evidence, the API schedule matches the rendered source for every affected group, exams remain empty pending their official timetable, repeated imports are deterministic, and the full backend and Flutter verification suites pass.
