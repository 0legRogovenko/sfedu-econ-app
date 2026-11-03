import hashlib
import json
import shutil
from pathlib import Path

import pytest
from sqlalchemy import func, select

from scripts import export_reviewed_schedule as exporter
from src.models import EducationLevel, Group
from src.schedule.reviewed_schedule import _lesson_hash
from src.schedule.source import INDEX_URL
from src.schedule.validated_snapshot import (
    DEFAULT_SNAPSHOT_DIR,
    SnapshotValidationError,
    import_validated_snapshot,
    validate_snapshot,
)

FIXTURE_PDF = Path(__file__).parent / "fixtures" / "schedule" / "13829.pdf"
DOCUMENT_ID = "13829"
SOURCE_SHA256 = "253200a64a50073c58f5e126b0b3be342fec538912d173cffe2ed37aba950564"
LESSON_HASH = "7e32e7f8dbbb8332e4ac21739cdd180e78632df727019f2fb1d0cf9f3ac61d05"
EXPECTED_COUNTS = {
    "documents": 1,
    "groups": 2,
    "lessons": 6,
    "calendar_weeks": 20,
    "exams": 0,
    "unparsed": 0,
}
DRAFT_DOCUMENT_IDS = frozenset(
    {"14159", "14160", "14174", "14175", "14176", "14177", "14178"}
)
DRAFT_MANAGED_IDS = DRAFT_DOCUMENT_IDS - {"14174"}


def _asset_metadata(path: Path) -> dict:
    content = path.read_bytes()
    return {
        "filename": path.name,
        "bytes": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
    }


def _document_metadata(pdf: Path) -> dict:
    return {
        "p_doc_id": DOCUMENT_ID,
        "section": "Весенний семестр",
        "label": "маг.2 курс",
        **_asset_metadata(pdf),
    }


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _build_v1_snapshot(tmp_path: Path) -> Path:
    snapshot_dir = tmp_path / "snapshot-v1"
    snapshot_dir.mkdir()
    pdf = snapshot_dir / f"{DOCUMENT_ID}.pdf"
    shutil.copyfile(FIXTURE_PDF, pdf)
    _write_json(
        snapshot_dir / "manifest.json",
        {
            "version": 1,
            "captured_at": "2026-08-31",
            "source_index_url": INDEX_URL,
            "expected_counts": EXPECTED_COUNTS,
            "documents": [_document_metadata(pdf)],
        },
    )
    return snapshot_dir


def _build_v2_snapshot(tmp_path: Path) -> Path:
    snapshot_dir = tmp_path / "snapshot-v2"
    snapshot_dir.mkdir()
    pdf = snapshot_dir / f"{DOCUMENT_ID}.pdf"
    shutil.copyfile(FIXTURE_PDF, pdf)
    corrections = snapshot_dir / "corrections.json"
    _write_json(
        corrections,
        {
            "version": 1,
            "documents": [
                {
                    "p_doc_id": DOCUMENT_ID,
                    "sha256": SOURCE_SHA256,
                    "operations": [],
                }
            ],
        },
    )
    reviewed = snapshot_dir / "reviewed_schedule.json"
    _write_json(
        reviewed,
        {
            "version": 1,
            "documents": {
                DOCUMENT_ID: {
                    "sha256": SOURCE_SHA256,
                    "lesson_hash": _lesson_hash(()),
                    "signatures": [],
                }
            },
        },
    )
    _write_json(
        snapshot_dir / "manifest.json",
        {
            "version": 2,
            "captured_at": "2026-08-31",
            "source_index_url": INDEX_URL,
            "expected_counts": EXPECTED_COUNTS,
            "documents": [_document_metadata(pdf)],
            "corrections_file": _asset_metadata(corrections),
            "reviewed_schedule_file": _asset_metadata(reviewed),
        },
    )
    return snapshot_dir


def _build_draft_v2_snapshot(tmp_path: Path) -> Path:
    source_manifest = json.loads(
        (DEFAULT_SNAPSHOT_DIR / "manifest.json").read_text(encoding="utf-8")
    )
    expected_counts = dict(source_manifest["expected_counts"])
    # Parser-only draft has 608 lessons; the authoritative snapshot reaches 612
    # through the four approved 14160 add operations.
    expected_counts["lessons"] = 608
    snapshot_dir = tmp_path / "snapshot-v2-draft"
    snapshot_dir.mkdir()
    documents = []
    corrections_documents = []
    for source_document in source_manifest["documents"]:
        source = DEFAULT_SNAPSHOT_DIR / source_document["filename"]
        destination = snapshot_dir / source.name
        shutil.copyfile(source, destination)
        document = {
            "p_doc_id": source_document["p_doc_id"],
            "section": source_document["section"],
            "label": source_document["label"],
            **_asset_metadata(destination),
        }
        documents.append(document)
        if document["p_doc_id"] in DRAFT_MANAGED_IDS:
            corrections_documents.append(
                {
                    "p_doc_id": document["p_doc_id"],
                    "sha256": document["sha256"],
                    "operations": [],
                }
            )

    corrections = snapshot_dir / "corrections.json"
    _write_json(
        corrections,
        {"version": 1, "documents": corrections_documents},
    )
    _write_json(
        snapshot_dir / "manifest.json",
        {
            "version": 2,
            "captured_at": source_manifest["captured_at"],
            "source_index_url": source_manifest["source_index_url"],
            "expected_counts": expected_counts,
            "documents": documents,
            "corrections_file": _asset_metadata(corrections),
        },
    )
    return snapshot_dir


def _move_complete_v2_source_to_authoritative_target(
    snapshot_dir: Path,
    source_role: str,
) -> Path:
    manifest_path = snapshot_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    reviewed = snapshot_dir / manifest["reviewed_schedule_file"]["filename"]
    alternate_reviewed = snapshot_dir / "reviewed-output.json"
    reviewed.rename(alternate_reviewed)
    manifest["reviewed_schedule_file"] = _asset_metadata(alternate_reviewed)

    if source_role == "pdf":
        source = snapshot_dir / manifest["documents"][0]["filename"]
        source.rename(snapshot_dir / "reviewed_schedule.json")
        manifest["documents"][0].update(
            _asset_metadata(snapshot_dir / "reviewed_schedule.json")
        )
    else:
        source = snapshot_dir / manifest["corrections_file"]["filename"]
        source.rename(snapshot_dir / "reviewed_schedule.json")
        manifest["corrections_file"] = _asset_metadata(
            snapshot_dir / "reviewed_schedule.json"
        )
    _write_json(manifest_path, manifest)
    return snapshot_dir / "reviewed_schedule.json"


def _export(snapshot_dir: Path, output: Path, *extra: str) -> int:
    return exporter.export_main(
        ["--snapshot-dir", str(snapshot_dir), "--output", str(output), *extra]
    )


def test_baseline_outside_snapshot_writes_version_one(tmp_path):
    snapshot_dir = _build_v1_snapshot(tmp_path)
    output = tmp_path / "parser-baseline.json"

    assert _export(snapshot_dir, output) == 0

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["version"] == 1
    assert set(payload["documents"]) == {DOCUMENT_ID}
    assert output.read_bytes().endswith(b"\n")


def test_draft_v2_baseline_imports_all_documents_and_exports_only_managed_ids(
    tmp_path,
    monkeypatch,
):
    snapshot_dir = _build_draft_v2_snapshot(tmp_path)
    output = tmp_path / "draft-parser-baseline.json"
    source_before = {
        path.name: path.read_bytes()
        for path in snapshot_dir.iterdir()
        if path.is_file()
    }
    imported_ids = []
    real_import_all = exporter.import_all

    def recording_import_all(session, fetcher, links=None, **kwargs):
        imported_ids.extend(link.p_doc_id for link in links)
        return real_import_all(session, fetcher, links=links, **kwargs)

    monkeypatch.setattr(exporter, "import_all", recording_import_all)

    with pytest.raises(
        SnapshotValidationError,
        match="missing keys: reviewed_schedule_file",
    ):
        validate_snapshot(snapshot_dir)

    assert _export(snapshot_dir, output) == 0

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert set(imported_ids) == DRAFT_DOCUMENT_IDS
    assert len(imported_ids) == 7
    assert set(payload["documents"]) == DRAFT_MANAGED_IDS
    assert len(payload["documents"]) == 6
    assert {
        path.name: path.read_bytes()
        for path in snapshot_dir.iterdir()
        if path.is_file()
    } == source_before


def test_confirmed_export_bootstraps_and_finalizes_seven_pdf_six_reviewed_v2(
    tmp_path,
    db_session,
):
    snapshot_dir = _build_draft_v2_snapshot(tmp_path)
    output = snapshot_dir / "reviewed_schedule.json"
    source_before = {
        path.name: path.read_bytes()
        for path in snapshot_dir.iterdir()
        if path.is_file()
    }

    with pytest.raises(
        SnapshotValidationError,
        match="missing keys: reviewed_schedule_file",
    ):
        validate_snapshot(snapshot_dir)

    assert (
        _export(
            snapshot_dir,
            output,
            "--confirm",
            exporter.CONFIRMATION,
        )
        == 0
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert set(payload["documents"]) == DRAFT_MANAGED_IDS
    assert {
        path.name: path.read_bytes()
        for path in snapshot_dir.iterdir()
        if path.is_file() and path.name != output.name
    } == source_before
    with pytest.raises(
        SnapshotValidationError,
        match="missing keys: reviewed_schedule_file",
    ):
        validate_snapshot(snapshot_dir)

    manifest_path = snapshot_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["reviewed_schedule_file"] = _asset_metadata(output)
    _write_json(manifest_path, manifest)

    validated = validate_snapshot(snapshot_dir)
    assert {item.link.p_doc_id for item in validated.documents} == DRAFT_DOCUMENT_IDS
    assert len(validated.documents) == 7
    assert validated.review_bundle is not None
    correction_ids = set(validated.review_bundle.corrections.documents)
    reviewed_ids = set(validated.review_bundle.reviewed_documents)
    assert correction_ids == reviewed_ids == DRAFT_MANAGED_IDS
    assert correction_ids
    source_hashes = {item["p_doc_id"]: item["sha256"] for item in manifest["documents"]}
    for p_doc_id in correction_ids:
        validated.review_bundle.guard_source(p_doc_id, source_hashes[p_doc_id])

    result = import_validated_snapshot(db_session, snapshot_dir)
    assert result["counts"] == manifest["expected_counts"]
    assert {item["p_doc_id"] for item in result["documents"]} == DRAFT_DOCUMENT_IDS
    assert len(result["documents"]) == 7


@pytest.mark.parametrize("filename", ["undeclared.txt", "reviewed_schedule.json"])
def test_draft_v2_baseline_rejects_every_undeclared_file(tmp_path, filename):
    snapshot_dir = _build_draft_v2_snapshot(tmp_path)
    (snapshot_dir / filename).write_bytes(b"untrusted")

    with pytest.raises(SnapshotValidationError, match="undeclared files"):
        _export(snapshot_dir, tmp_path / "baseline.json")


def test_draft_v2_cannot_declare_authoritative_output_as_a_source_asset(tmp_path):
    snapshot_dir = _build_draft_v2_snapshot(tmp_path)
    corrections = snapshot_dir / "corrections.json"
    reserved = snapshot_dir / "reviewed_schedule.json"
    corrections.rename(reserved)
    manifest_path = snapshot_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["corrections_file"] = _asset_metadata(reserved)
    _write_json(manifest_path, manifest)
    original = reserved.read_bytes()

    with pytest.raises(SnapshotValidationError, match="reserved output filename"):
        _export(
            snapshot_dir,
            reserved,
            "--confirm",
            exporter.CONFIRMATION,
        )

    assert reserved.read_bytes() == original


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("empty", "manage at least one document"),
        ("wrong-source-hash", "changed and requires review"),
    ],
)
def test_draft_v2_requires_nonempty_source_hash_bound_registry(
    tmp_path,
    mutation,
    message,
):
    snapshot_dir = _build_draft_v2_snapshot(tmp_path)
    corrections_path = snapshot_dir / "corrections.json"
    corrections = json.loads(corrections_path.read_text(encoding="utf-8"))
    if mutation == "empty":
        corrections["documents"] = []
    else:
        corrections["documents"][0]["sha256"] = "0" * 64
    _write_json(corrections_path, corrections)
    manifest_path = snapshot_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["corrections_file"] = _asset_metadata(corrections_path)
    _write_json(manifest_path, manifest)
    output = tmp_path / "baseline.json"

    with pytest.raises(SnapshotValidationError, match=message):
        _export(snapshot_dir, output)

    assert not output.exists()


@pytest.mark.parametrize("confirmation", [None, "wrong-value"])
def test_exact_reviewed_filename_requires_exact_confirmation(
    tmp_path,
    confirmation,
):
    snapshot_dir = _build_v1_snapshot(tmp_path)
    output = snapshot_dir / "reviewed_schedule.json"
    extra = [] if confirmation is None else ["--confirm", confirmation]

    with pytest.raises(SystemExit, match="rendered-PDF confirmation"):
        _export(snapshot_dir, output, *extra)

    assert not output.exists()


def test_exact_confirmation_permits_authoritative_target(tmp_path):
    snapshot_dir = _build_v1_snapshot(tmp_path)
    output = snapshot_dir / "reviewed_schedule.json"

    assert (
        _export(
            snapshot_dir,
            output,
            "--confirm",
            exporter.CONFIRMATION,
        )
        == 0
    )

    assert json.loads(output.read_text(encoding="utf-8"))["version"] == 1


def test_v1_authoritative_target_cannot_overwrite_declared_pdf(tmp_path):
    snapshot_dir = _build_v1_snapshot(tmp_path)
    manifest_path = snapshot_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    pdf = snapshot_dir / manifest["documents"][0]["filename"]
    output = snapshot_dir / "reviewed_schedule.json"
    pdf.rename(output)
    manifest["documents"][0].update(_asset_metadata(output))
    _write_json(manifest_path, manifest)
    original = output.read_bytes()

    with pytest.raises(SnapshotValidationError, match="declared source asset"):
        _export(
            snapshot_dir,
            output,
            "--confirm",
            exporter.CONFIRMATION,
        )

    assert output.read_bytes() == original


@pytest.mark.parametrize("source_role", ["pdf", "corrections"])
def test_complete_v2_authoritative_target_cannot_overwrite_source_role(
    tmp_path,
    source_role,
):
    snapshot_dir = _build_v2_snapshot(tmp_path)
    output = _move_complete_v2_source_to_authoritative_target(
        snapshot_dir,
        source_role,
    )
    original = output.read_bytes()

    with pytest.raises(
        SnapshotValidationError,
        match="explicitly declared reviewed output",
    ):
        _export(
            snapshot_dir,
            output,
            "--confirm",
            exporter.CONFIRMATION,
        )

    assert output.read_bytes() == original


def test_complete_v2_declared_reviewed_target_remains_permitted(tmp_path):
    snapshot_dir = _build_v2_snapshot(tmp_path)
    output = snapshot_dir / "reviewed_schedule.json"

    assert (
        _export(
            snapshot_dir,
            output,
            "--confirm",
            exporter.CONFIRMATION,
        )
        == 0
    )

    assert json.loads(output.read_text(encoding="utf-8"))["version"] == 1


@pytest.mark.parametrize(
    "relative_output",
    ["other.json", "nested/output.json", "nested/../other.json"],
)
def test_every_other_path_inside_snapshot_is_rejected(tmp_path, relative_output):
    snapshot_dir = _build_v1_snapshot(tmp_path)
    (snapshot_dir / "nested").mkdir()
    output = snapshot_dir / relative_output

    with pytest.raises(SystemExit, match="inside the snapshot directory"):
        _export(
            snapshot_dir,
            output,
            "--confirm",
            exporter.CONFIRMATION,
        )

    assert not (snapshot_dir / "other.json").exists()
    assert not (snapshot_dir / "nested" / "output.json").exists()


def test_symlink_alias_cannot_bypass_snapshot_boundary(tmp_path):
    snapshot_dir = _build_v1_snapshot(tmp_path)
    alias = tmp_path / "snapshot-alias"
    alias.symlink_to(snapshot_dir, target_is_directory=True)

    with pytest.raises(SystemExit, match="inside the snapshot directory"):
        _export(
            snapshot_dir,
            alias / "other.json",
            "--confirm",
            exporter.CONFIRMATION,
        )
    with pytest.raises(SystemExit, match="rendered-PDF confirmation"):
        _export(snapshot_dir, alias / "reviewed_schedule.json")


def test_ambiguous_output_symlink_is_rejected(tmp_path):
    snapshot_dir = _build_v1_snapshot(tmp_path)
    target = tmp_path / "real-output.json"
    output = tmp_path / "output-link.json"
    output.symlink_to(target)

    with pytest.raises(SystemExit, match="ambiguous output path"):
        _export(snapshot_dir, output)

    assert not target.exists()
    assert output.is_symlink()


def test_export_uses_isolated_database_and_applies_authenticated_registry(
    tmp_path,
    db_session,
    monkeypatch,
):
    snapshot_dir = _build_v2_snapshot(tmp_path)
    output = tmp_path / "reviewed-baseline.json"
    sentinel = Group(
        course=9,
        number="9.99",
        program="do-not-touch",
        level=EducationLevel.BACHELOR,
    )
    db_session.add(sentinel)
    db_session.commit()

    def forbidden_session_local():
        raise AssertionError("SessionLocal must not be used by the exporter")

    from src.schedule import validated_snapshot

    monkeypatch.setattr(validated_snapshot, "SessionLocal", forbidden_session_local)
    calls = []
    real_apply = exporter.apply_document_corrections

    def recording_apply(session, document, corrections):
        calls.append(str(document.p_doc_id))
        return real_apply(session, document, corrections)

    monkeypatch.setattr(exporter, "apply_document_corrections", recording_apply)

    assert _export(snapshot_dir, output) == 0

    assert calls == [DOCUMENT_ID]
    assert db_session.scalar(select(func.count()).select_from(Group)) == 1
    assert db_session.scalar(select(Group.program)) == "do-not-touch"


def test_atomic_failure_leaves_destination_unchanged_and_no_temp_file(
    tmp_path,
    monkeypatch,
):
    snapshot_dir = _build_v1_snapshot(tmp_path)
    output = tmp_path / "parser-baseline.json"
    original = b"existing-reviewed-output\n"
    output.write_bytes(original)
    before_names = {path.name for path in tmp_path.iterdir()}

    def fail_replace(source, destination):
        raise OSError("simulated replace failure")

    monkeypatch.setattr(exporter.os, "replace", fail_replace)

    with pytest.raises(OSError, match="simulated replace failure"):
        _export(snapshot_dir, output)

    assert output.read_bytes() == original
    assert {path.name for path in tmp_path.iterdir()} == before_names


def test_fixture_output_is_complete_and_deterministic(tmp_path):
    snapshot_dir = _build_v1_snapshot(tmp_path)
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"

    assert _export(snapshot_dir, first) == 0
    assert _export(snapshot_dir, second) == 0

    assert first.read_bytes() == second.read_bytes()
    payload = json.loads(first.read_text(encoding="utf-8"))
    document = payload["documents"][DOCUMENT_ID]
    assert document["sha256"] == SOURCE_SHA256
    assert document["lesson_hash"] == LESSON_HASH
    assert len(document["signatures"]) == EXPECTED_COUNTS["lessons"]
    assert document["signatures"] == sorted(document["signatures"])
    assert all(f"документ={DOCUMENT_ID}" in item for item in document["signatures"])


def test_baseline_export_never_changes_snapshot_assets(tmp_path):
    snapshot_dir = _build_v1_snapshot(tmp_path)
    output = tmp_path / "parser-baseline.json"
    before = {
        path.relative_to(snapshot_dir): path.read_bytes()
        for path in snapshot_dir.rglob("*")
        if path.is_file()
    }

    assert _export(snapshot_dir, output) == 0

    after = {
        path.relative_to(snapshot_dir): path.read_bytes()
        for path in snapshot_dir.rglob("*")
        if path.is_file()
    }
    assert after == before


def test_generated_output_is_untrusted_until_manifest_authenticates_it(tmp_path):
    snapshot_dir = _build_v2_snapshot(tmp_path)
    output = snapshot_dir / "reviewed_schedule.json"
    manifest_path = snapshot_dir / "manifest.json"
    manifest_before = manifest_path.read_bytes()
    corrections_before = (snapshot_dir / "corrections.json").read_bytes()
    pdf_before = (snapshot_dir / f"{DOCUMENT_ID}.pdf").read_bytes()

    assert (
        _export(
            snapshot_dir,
            output,
            "--confirm",
            exporter.CONFIRMATION,
        )
        == 0
    )

    assert manifest_path.read_bytes() == manifest_before
    assert (snapshot_dir / "corrections.json").read_bytes() == corrections_before
    assert (snapshot_dir / f"{DOCUMENT_ID}.pdf").read_bytes() == pdf_before
    with pytest.raises(SnapshotValidationError, match="integrity mismatch"):
        validate_snapshot(snapshot_dir)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["reviewed_schedule_file"] = _asset_metadata(output)
    _write_json(manifest_path, manifest)
    validated = validate_snapshot(snapshot_dir)
    assert validated.review_bundle is not None
    assert (
        validated.review_bundle.reviewed_documents[DOCUMENT_ID].lesson_hash
        == LESSON_HASH
    )
