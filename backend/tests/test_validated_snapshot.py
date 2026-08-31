import hashlib
import json
import shutil
from types import SimpleNamespace

import pytest
from sqlalchemy import func, select

from src.models import DocType, Group, Lesson, ScheduleDocument, WeekCalendar
from src.schedule.reviewed_schedule import _lesson_hash
from src.schedule.source import INDEX_URL
from src.schedule.validated_snapshot import (
    DEFAULT_SNAPSHOT_DIR,
    SnapshotAsset,
    SnapshotValidationError,
    import_validated_snapshot,
    validate_snapshot,
)


def _asset_metadata(path):
    content = path.read_bytes()
    return {
        "filename": path.name,
        "bytes": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
    }


def _build_v2_snapshot(tmp_path, *, managed=True):
    snapshot_dir = tmp_path / "snapshot-v2"
    snapshot_dir.mkdir()
    pdf = snapshot_dir / "14159.pdf"
    pdf.write_bytes(b"%PDF-reviewed-test\n")
    source_sha = hashlib.sha256(pdf.read_bytes()).hexdigest()
    correction_documents = (
        [{"p_doc_id": "14159", "sha256": source_sha, "operations": []}]
        if managed
        else []
    )
    reviewed_documents = (
        {
            "14159": {
                "sha256": source_sha,
                "lesson_hash": _lesson_hash(()),
                "signatures": [],
            }
        }
        if managed
        else {}
    )
    corrections = snapshot_dir / "corrections.json"
    corrections.write_text(
        json.dumps(
            {"version": 1, "documents": correction_documents},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    reviewed = snapshot_dir / "reviewed_schedule.json"
    reviewed.write_text(
        json.dumps(
            {"version": 1, "documents": reviewed_documents},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    manifest = {
        "version": 2,
        "captured_at": "2026-08-30",
        "source_index_url": INDEX_URL,
        "expected_counts": {
            "documents": 1,
            "groups": 0,
            "lessons": 0,
            "calendar_weeks": 0,
            "exams": 0,
            "unparsed": 0,
        },
        "documents": [
            {
                "p_doc_id": "14159",
                "section": "Осенний семестр",
                "label": "маг.1 курс",
                **_asset_metadata(pdf),
            }
        ],
        "corrections_file": _asset_metadata(corrections),
        "reviewed_schedule_file": _asset_metadata(reviewed),
    }
    (snapshot_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False),
        encoding="utf-8",
    )
    return snapshot_dir


def _manifest(snapshot_dir):
    return json.loads((snapshot_dir / "manifest.json").read_text(encoding="utf-8"))


def _write_manifest(snapshot_dir, manifest):
    (snapshot_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False),
        encoding="utf-8",
    )


def _rewrite_asset_and_manifest_hash(snapshot_dir, manifest_key, payload):
    manifest = _manifest(snapshot_dir)
    path = snapshot_dir / manifest[manifest_key]["filename"]
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    manifest[manifest_key] = _asset_metadata(path)
    _write_manifest(snapshot_dir, manifest)


def _empty_reviewed_import(session, fetcher, *, links, atomic, review_bundle):
    assert atomic is True
    assert review_bundle is not None
    fetched = fetcher.fetch_document("14159")
    document = ScheduleDocument(
        p_doc_id=14159,
        section="Осенний семестр",
        label="маг.1 курс",
        doc_type=DocType.SEMESTER_GRID_MASTER,
        sha256=fetched.sha256,
        source_url=fetched.source_url,
    )
    session.add(document)
    session.flush()
    review_bundle.apply_and_validate(session, document)
    return SimpleNamespace(
        failed=0,
        missing=(),
        documents=[SimpleNamespace(p_doc_id="14159", status="imported")],
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


def test_v1_snapshot_remains_read_only_compatible_and_has_no_review_bundle():
    snapshot = validate_snapshot(DEFAULT_SNAPSHOT_DIR)

    assert snapshot.review_bundle is None
    assert len(snapshot.documents) == 7
    with pytest.raises(TypeError):
        snapshot.expected_counts["lessons"] = 0


def test_validates_v2_assets_once_and_freezes_the_bundle(tmp_path, monkeypatch):
    snapshot_dir = _build_v2_snapshot(tmp_path)
    counts = {"corrections.json": 0, "reviewed_schedule.json": 0}
    original = type(snapshot_dir).read_bytes

    def counted_read(path):
        if path.name in counts:
            counts[path.name] += 1
        return original(path)

    monkeypatch.setattr(type(snapshot_dir), "read_bytes", counted_read)

    snapshot = validate_snapshot(snapshot_dir)

    assert isinstance(snapshot.documents[0].asset, SnapshotAsset)
    assert snapshot.documents[0].asset.content == b"%PDF-reviewed-test\n"
    assert snapshot.review_bundle is not None
    assert snapshot.review_bundle.manages("14159")
    assert counts == {"corrections.json": 1, "reviewed_schedule.json": 1}
    with pytest.raises(TypeError):
        snapshot.expected_counts["lessons"] = 5


@pytest.mark.parametrize("version", [0, 3, "2", True])
def test_rejects_unknown_or_non_integer_manifest_versions(tmp_path, version):
    snapshot_dir = _build_v2_snapshot(tmp_path)
    manifest = _manifest(snapshot_dir)
    manifest["version"] = version
    _write_manifest(snapshot_dir, manifest)

    with pytest.raises(SnapshotValidationError, match="manifest version"):
        validate_snapshot(snapshot_dir)


@pytest.mark.parametrize(
    "version_members",
    ['"version": 2, "version": 1', '"version": 1, "version": 2'],
)
def test_manifest_rejects_duplicate_version_before_selecting_schema(
    tmp_path, version_members
):
    snapshot_dir = _build_v2_snapshot(tmp_path)
    path = snapshot_dir / "manifest.json"
    raw = path.read_text(encoding="utf-8")
    path.write_text(
        raw.replace('"version": 2', version_members, 1),
        encoding="utf-8",
    )

    with pytest.raises(SnapshotValidationError, match="duplicate JSON key version"):
        validate_snapshot(snapshot_dir)


def test_v1_manifest_rejects_nested_duplicate_json_key(tmp_path):
    snapshot_dir = tmp_path / "snapshot-v1"
    shutil.copytree(DEFAULT_SNAPSHOT_DIR, snapshot_dir)
    path = snapshot_dir / "manifest.json"
    raw = json.dumps(_manifest(snapshot_dir), ensure_ascii=False)
    path.write_text(
        raw.replace(
            '"expected_counts": {"documents": 7',
            '"expected_counts": {"documents": 7, "documents": 7',
            1,
        ),
        encoding="utf-8",
    )

    with pytest.raises(SnapshotValidationError, match="duplicate JSON key documents"):
        validate_snapshot(snapshot_dir)


def test_v2_manifest_rejects_nested_duplicate_json_key(tmp_path):
    snapshot_dir = _build_v2_snapshot(tmp_path)
    path = snapshot_dir / "manifest.json"
    raw = path.read_text(encoding="utf-8")
    path.write_text(
        raw.replace(
            '"expected_counts": {"documents": 1',
            '"expected_counts": {"documents": 1, "documents": 1',
            1,
        ),
        encoding="utf-8",
    )

    with pytest.raises(SnapshotValidationError, match="duplicate JSON key documents"):
        validate_snapshot(snapshot_dir)


def test_v2_manifest_rejects_unknown_keys(tmp_path):
    snapshot_dir = _build_v2_snapshot(tmp_path)
    manifest = _manifest(snapshot_dir)
    manifest["extra"] = True
    _write_manifest(snapshot_dir, manifest)

    with pytest.raises(SnapshotValidationError, match="unknown keys: extra"):
        validate_snapshot(snapshot_dir)


@pytest.mark.parametrize("filename", ["../corrections.json", "/tmp/corrections.json", "nested/corrections.json", r"nested\corrections.json"])
def test_v2_rejects_unsafe_asset_filenames(tmp_path, filename):
    snapshot_dir = _build_v2_snapshot(tmp_path)
    manifest = _manifest(snapshot_dir)
    manifest["corrections_file"]["filename"] = filename
    _write_manifest(snapshot_dir, manifest)

    with pytest.raises(SnapshotValidationError, match="unsafe .* filename"):
        validate_snapshot(snapshot_dir)


def test_v2_rejects_undeclared_directories_and_files(tmp_path):
    snapshot_dir = _build_v2_snapshot(tmp_path)
    (snapshot_dir / "unexpected.txt").write_text("unreviewed", encoding="utf-8")

    with pytest.raises(SnapshotValidationError, match="undeclared files"):
        validate_snapshot(snapshot_dir)


def test_v2_rejects_duplicate_and_noncanonical_document_ids(tmp_path):
    snapshot_dir = _build_v2_snapshot(tmp_path)
    manifest = _manifest(snapshot_dir)
    duplicate = dict(manifest["documents"][0])
    manifest["documents"].append(duplicate)
    _write_manifest(snapshot_dir, manifest)

    with pytest.raises(SnapshotValidationError, match="duplicate document id 14159"):
        validate_snapshot(snapshot_dir)

    manifest["documents"] = [duplicate]
    manifest["documents"][0]["p_doc_id"] = "014159"
    _write_manifest(snapshot_dir, manifest)
    with pytest.raises(SnapshotValidationError, match="invalid document id"):
        validate_snapshot(snapshot_dir)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("lessons", -1, "nonnegative integer"),
        ("lessons", True, "nonnegative integer"),
        ("exams", 1, "exams must be exactly 0"),
    ],
)
def test_v2_expected_counts_are_strict_and_exams_stay_empty(
    tmp_path, field, value, message
):
    snapshot_dir = _build_v2_snapshot(tmp_path)
    manifest = _manifest(snapshot_dir)
    manifest["expected_counts"][field] = value
    _write_manifest(snapshot_dir, manifest)

    with pytest.raises(SnapshotValidationError, match=message):
        validate_snapshot(snapshot_dir)


def test_rejects_modified_corrections_before_touching_database(
    tmp_path, db_session, monkeypatch
):
    snapshot_dir = _build_v2_snapshot(tmp_path)
    corrections = snapshot_dir / "corrections.json"
    corrections.write_text(
        corrections.read_text(encoding="utf-8") + " ",
        encoding="utf-8",
    )
    called = False

    def forbidden_import(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("database importer must not run")

    monkeypatch.setattr(
        "src.schedule.validated_snapshot.import_all", forbidden_import
    )

    with pytest.raises(SnapshotValidationError, match="corrections integrity"):
        import_validated_snapshot(db_session, snapshot_dir)

    assert called is False
    assert db_session.scalar(select(func.count()).select_from(ScheduleDocument)) == 0


def test_rejects_same_size_correction_tamper_by_sha256(tmp_path):
    snapshot_dir = _build_v2_snapshot(tmp_path)
    corrections = snapshot_dir / "corrections.json"
    original = corrections.read_bytes()
    tampered = original.replace(b" ", b"\t", 1)
    assert len(tampered) == len(original)
    assert tampered != original
    corrections.write_bytes(tampered)

    with pytest.raises(SnapshotValidationError, match="corrections integrity"):
        validate_snapshot(snapshot_dir)


def test_rejects_modified_reviewed_output_before_touching_database(
    tmp_path, db_session, monkeypatch
):
    snapshot_dir = _build_v2_snapshot(tmp_path)
    reviewed = snapshot_dir / "reviewed_schedule.json"
    reviewed.write_text(
        reviewed.read_text(encoding="utf-8") + " ",
        encoding="utf-8",
    )
    called = False

    def forbidden_import(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("database importer must not run")

    monkeypatch.setattr(
        "src.schedule.validated_snapshot.import_all", forbidden_import
    )

    with pytest.raises(SnapshotValidationError, match="reviewed schedule integrity"):
        import_validated_snapshot(db_session, snapshot_dir)

    assert called is False
    assert db_session.scalar(select(func.count()).select_from(ScheduleDocument)) == 0


def test_rejects_invalid_authenticated_corrections_before_database(
    tmp_path, db_session, monkeypatch
):
    snapshot_dir = _build_v2_snapshot(tmp_path)
    _rewrite_asset_and_manifest_hash(
        snapshot_dir,
        "corrections_file",
        {"version": 1, "documents": "not-a-list"},
    )
    called = False

    def forbidden_import(*args, **kwargs):
        nonlocal called
        called = True

    monkeypatch.setattr(
        "src.schedule.validated_snapshot.import_all", forbidden_import
    )

    with pytest.raises(SnapshotValidationError, match="corrections file is invalid"):
        import_validated_snapshot(db_session, snapshot_dir)

    assert called is False


def test_rejects_rehashed_but_wrong_reviewed_output_and_rolls_back(
    tmp_path, db_session, monkeypatch
):
    snapshot_dir = _build_v2_snapshot(tmp_path)
    reviewed_path = snapshot_dir / "reviewed_schedule.json"
    payload = json.loads(reviewed_path.read_text(encoding="utf-8"))
    signatures = ["corrupted-reviewed-signature"]
    payload["documents"]["14159"]["signatures"] = signatures
    payload["documents"]["14159"]["lesson_hash"] = _lesson_hash(tuple(signatures))
    _rewrite_asset_and_manifest_hash(
        snapshot_dir, "reviewed_schedule_file", payload
    )
    monkeypatch.setattr(
        "src.schedule.validated_snapshot.import_all", _empty_reviewed_import
    )

    with pytest.raises(SnapshotValidationError, match="reviewed schedule mismatch"):
        import_validated_snapshot(db_session, snapshot_dir)

    assert db_session.scalar(select(func.count()).select_from(ScheduleDocument)) == 0


def test_imports_valid_v2_bundle_atomically_before_commit(
    tmp_path, db_session, monkeypatch
):
    snapshot_dir = _build_v2_snapshot(tmp_path)
    monkeypatch.setattr(
        "src.schedule.validated_snapshot.import_all", _empty_reviewed_import
    )

    result = import_validated_snapshot(db_session, snapshot_dir)

    assert result["counts"]["documents"] == 1
    assert db_session.scalar(select(func.count()).select_from(ScheduleDocument)) == 1


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
