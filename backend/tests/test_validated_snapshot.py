import json
import shutil

import pytest
from sqlalchemy import func, select

from src.models import Group, Lesson, ScheduleDocument, WeekCalendar
from src.schedule.validated_snapshot import (
    DEFAULT_SNAPSHOT_DIR,
    SnapshotValidationError,
    import_validated_snapshot,
    validate_snapshot,
)


def test_imports_exact_validated_official_snapshot(db_session):
    result = import_validated_snapshot(db_session)

    assert result["status"] == "ok"
    assert result["counts"] == {
        "documents": 7,
        "groups": 39,
        "lessons": 608,
        "calendar_weeks": 120,
        "exams": 0,
        "unparsed": 16,
    }
    assert db_session.scalar(select(func.count()).select_from(ScheduleDocument)) == 7
    assert db_session.scalar(select(func.count()).select_from(Group)) == 39
    assert db_session.scalar(select(func.count()).select_from(Lesson)) == 608
    assert db_session.scalar(select(func.count()).select_from(WeekCalendar)) == 120


def test_rejects_snapshot_manifest_from_a_nonofficial_source(tmp_path):
    snapshot_dir = tmp_path / "snapshot"
    shutil.copytree(DEFAULT_SNAPSHOT_DIR, snapshot_dir)
    manifest_path = snapshot_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["source_index_url"] = "https://example.com/not-sfedu"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(SnapshotValidationError, match="official SFEDU index"):
        validate_snapshot(snapshot_dir)


def test_rejects_undeclared_files_in_snapshot(tmp_path):
    snapshot_dir = tmp_path / "snapshot"
    shutil.copytree(DEFAULT_SNAPSHOT_DIR, snapshot_dir)
    (snapshot_dir / "unexpected.pdf").write_bytes(b"%PDF-unreviewed")

    with pytest.raises(SnapshotValidationError, match="unexpected files"):
        validate_snapshot(snapshot_dir)


def test_rejects_truncated_pdf_before_touching_database(tmp_path, db_session):
    snapshot_dir = tmp_path / "snapshot"
    shutil.copytree(DEFAULT_SNAPSHOT_DIR, snapshot_dir)
    pdf = snapshot_dir / "14175.pdf"
    pdf.write_bytes(pdf.read_bytes()[:81_659])

    with pytest.raises(SnapshotValidationError, match="integrity mismatch: 14175.pdf"):
        import_validated_snapshot(db_session, snapshot_dir)

    assert db_session.scalar(select(func.count()).select_from(ScheduleDocument)) == 0
    assert db_session.scalar(select(func.count()).select_from(Lesson)) == 0


def test_rolls_back_when_imported_counts_drift_from_reviewed_result(
    tmp_path, db_session
):
    snapshot_dir = tmp_path / "snapshot"
    shutil.copytree(DEFAULT_SNAPSHOT_DIR, snapshot_dir)
    manifest_path = snapshot_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["expected_counts"]["lessons"] += 1
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(SnapshotValidationError, match="reviewed corpus"):
        import_validated_snapshot(db_session, snapshot_dir)

    assert db_session.scalar(select(func.count()).select_from(ScheduleDocument)) == 0
    assert db_session.scalar(select(func.count()).select_from(Lesson)) == 0
