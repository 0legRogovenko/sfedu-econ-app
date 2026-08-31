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
    SnapshotValidationError,
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

    assert _export(
        snapshot_dir,
        output,
        "--confirm",
        exporter.CONFIRMATION,
    ) == 0

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

    assert _export(
        snapshot_dir,
        output,
        "--confirm",
        exporter.CONFIRMATION,
    ) == 0

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
