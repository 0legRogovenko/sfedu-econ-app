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


LEGACY_SNAPSHOT_DIR = DEFAULT_SNAPSHOT_DIR.parent / "2026-08-28"


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
        "lessons": 612,
        "calendar_weeks": 120,
        "exams": 0,
        "unparsed": 17,
    }
    assert db_session.scalar(select(func.count()).select_from(ScheduleDocument)) == 7
    assert db_session.scalar(select(func.count()).select_from(Group)) == 39
    assert db_session.scalar(select(func.count()).select_from(Lesson)) == 612
    assert db_session.scalar(select(func.count()).select_from(WeekCalendar)) == 120


def test_current_review_bundle_is_the_six_supplied_pdfs_plus_postgraduate():
    snapshot = validate_snapshot(DEFAULT_SNAPSHOT_DIR)

    assert {
        document.link.p_doc_id: document.sha256 for document in snapshot.documents
    } == {
        "14175": "e4532cd0bbe6a3e7a0bd400006a6900689dae04b7cfab58d9e623b4ba4d860fc",
        "14176": "fc23269224d9ce84aae67dcccdfe6cb3179ee7b47f02e6c829898ba5dd9328d5",
        "14177": "185c61e49950d60ff457e5cce347dab803dc2da1e7021bb636780f48e022446b",
        "14178": "311bb1720648d6072265bfcf73b3f0112af335929ecf39ff6fb89b75687e15c4",
        "14159": "6ff0e7ec277c22cf99b6c2365e7b2c3771d6d4ad946c07453e1973253a0c41d9",
        "14160": "005fb3145527fd51821823203af05fd3de8841ae5bb4994de7172f062c6afdf8",
        "14174": "5e43a96a3d7031c6cf0f08e9ca2d0e69f40ad27e5c0c9622ffcf4380212df008",
    }
    assert snapshot.expected_counts["exams"] == 0


def test_current_review_bundle_pins_exact_managed_signatures_and_operations():
    snapshot = validate_snapshot(DEFAULT_SNAPSHOT_DIR)

    assert snapshot.review_bundle is not None
    corrections = snapshot.review_bundle.corrections.documents
    reviewed = snapshot.review_bundle.reviewed_documents
    managed_ids = {"14159", "14160", "14175", "14176", "14177", "14178"}
    assert set(corrections) == managed_ids
    assert set(reviewed) == managed_ids
    assert {
        p_doc_id: (document.lesson_hash, len(document.signatures))
        for p_doc_id, document in reviewed.items()
    } == {
        "14159": (
            "6f4e75e246b7652a0568944a233d4823d073e8893b099cc32c841041263a1708",
            82,
        ),
        "14160": (
            "3fcf71e51d92bd69c37996774e53346c6efed24df89529cb720592ba927a0043",
            71,
        ),
        "14175": (
            "cdf03a26cffe46bb918d4af5ef903ddef6420bc0fa8653829ec714023dd72b9a",
            122,
        ),
        "14176": (
            "27204ec1158dbaf35faca8f0cf98d56bda36fb16cd53986b28602942b1079779",
            102,
        ),
        "14177": (
            "259080a8453c5a86fccdbd7b87bbdf6ed017c6df7142859f8454bb9927615956",
            122,
        ),
        "14178": (
            "e316f0fd759840729a2c6b26513d13ab9f6d6fd2be028055740245b8f7e25db3",
            113,
        ),
    }
    assert {
        p_doc_id: [operation.operation for operation in document.operations]
        for p_doc_id, document in corrections.items()
    } == {
        "14159": ["replace"] * 39,
        "14160": ["replace"] * 15 + ["add"] * 4 + ["replace"] * 2,
        "14175": [],
        "14176": [],
        "14177": [],
        "14178": [],
    }
    assert sum(len(document.operations) for document in corrections.values()) == 60


def test_v1_snapshot_remains_read_only_compatible_and_has_no_review_bundle():
    snapshot = validate_snapshot(LEGACY_SNAPSHOT_DIR)

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


@pytest.mark.parametrize("version", [0, 3, "2", True, 1.0, 2.0])
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
    shutil.copytree(LEGACY_SNAPSHOT_DIR, snapshot_dir)
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


def test_v2_accepts_manifest_document_outside_nonempty_review_bundle(tmp_path):
    snapshot_dir = _build_v2_snapshot(tmp_path)
    second_pdf = snapshot_dir / "14160.pdf"
    second_pdf.write_bytes(b"%PDF-reviewed-test-two\n")
    manifest = _manifest(snapshot_dir)
    manifest["documents"].append(
        {
            "p_doc_id": "14160",
            "section": "Осенний семестр",
            "label": "маг.2 курс",
            **_asset_metadata(second_pdf),
        }
    )
    manifest["expected_counts"]["documents"] = 2
    _write_manifest(snapshot_dir, manifest)

    snapshot = validate_snapshot(snapshot_dir)

    assert {item.link.p_doc_id for item in snapshot.documents} == {"14159", "14160"}
    assert snapshot.review_bundle is not None
    assert set(snapshot.review_bundle.corrections.documents) == {"14159"}
    assert set(snapshot.review_bundle.reviewed_documents) == {"14159"}


def test_v2_rejects_empty_review_bundle(tmp_path):
    snapshot_dir = _build_v2_snapshot(tmp_path, managed=False)

    with pytest.raises(SnapshotValidationError, match="manage at least one document"):
        validate_snapshot(snapshot_dir)


def test_v2_rejects_mismatched_correction_and_reviewed_id_sets(tmp_path):
    snapshot_dir = _build_v2_snapshot(tmp_path)
    _rewrite_asset_and_manifest_hash(
        snapshot_dir,
        "reviewed_schedule_file",
        {"version": 1, "documents": {}},
    )

    with pytest.raises(SnapshotValidationError, match="key sets do not match"):
        validate_snapshot(snapshot_dir)


def test_v2_guards_every_managed_source_hash(tmp_path):
    snapshot_dir = _build_v2_snapshot(tmp_path)
    corrections_path = snapshot_dir / "corrections.json"
    corrections = json.loads(corrections_path.read_text(encoding="utf-8"))
    corrections["documents"][0]["sha256"] = "0" * 64
    _rewrite_asset_and_manifest_hash(
        snapshot_dir,
        "corrections_file",
        corrections,
    )
    reviewed_path = snapshot_dir / "reviewed_schedule.json"
    reviewed = json.loads(reviewed_path.read_text(encoding="utf-8"))
    reviewed["documents"]["14159"]["sha256"] = "0" * 64
    _rewrite_asset_and_manifest_hash(
        snapshot_dir,
        "reviewed_schedule_file",
        reviewed,
    )

    with pytest.raises(SnapshotValidationError, match="changed and requires review"):
        validate_snapshot(snapshot_dir)


def test_v2_rejects_review_bundle_document_missing_from_manifest(tmp_path):
    snapshot_dir = _build_v2_snapshot(tmp_path)
    manifest = _manifest(snapshot_dir)
    source_sha = manifest["documents"][0]["sha256"]
    corrections_path = snapshot_dir / "corrections.json"
    corrections = json.loads(corrections_path.read_text(encoding="utf-8"))
    corrections["documents"].append(
        {"p_doc_id": "14160", "sha256": source_sha, "operations": []}
    )
    _rewrite_asset_and_manifest_hash(
        snapshot_dir,
        "corrections_file",
        corrections,
    )
    reviewed_path = snapshot_dir / "reviewed_schedule.json"
    reviewed = json.loads(reviewed_path.read_text(encoding="utf-8"))
    reviewed["documents"]["14160"] = {
        "sha256": source_sha,
        "lesson_hash": _lesson_hash(()),
        "signatures": [],
    }
    _rewrite_asset_and_manifest_hash(
        snapshot_dir,
        "reviewed_schedule_file",
        reviewed,
    )

    with pytest.raises(SnapshotValidationError, match="undeclared documents: 14160"):
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

    with pytest.raises(SnapshotValidationError, match="undeclared files"):
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
