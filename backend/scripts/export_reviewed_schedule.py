"""Export parser baselines and explicitly confirmed reviewed schedule output."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from sqlalchemy import create_engine, func, select  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from src.schedule import validated_snapshot as snapshot_validation  # noqa: E402
from src.database import Base  # noqa: E402
from src.models import (  # noqa: E402
    ExamEvent,
    Group,
    Lesson,
    ScheduleDocument,
    UnparsedCell,
    WeekCalendar,
)
from src.schedule.fetch import FetchedDocument  # noqa: E402
from src.schedule.importer import import_all  # noqa: E402
from src.schedule.reviewed_schedule import (  # noqa: E402
    CorrectionRegistry,
    CorrectionResult,
    ReviewValidationError,
    apply_document_corrections,
    parse_correction_registry,
    reviewed_document_output,
)
from src.schedule.source import INDEX_URL, ScheduleLink, download_url  # noqa: E402
from src.schedule.validated_snapshot import (  # noqa: E402
    SnapshotDocument,
    SnapshotValidationError,
    ValidatedSnapshot,
    validate_snapshot,
)


CONFIRMATION = "I_REVIEWED_EVERY_RENDERED_GROUP"
_REVIEWED_FILENAME = "reviewed_schedule.json"
_DRAFT_V2_ROOT_KEYS = frozenset(
    {
        "version",
        "captured_at",
        "source_index_url",
        "expected_counts",
        "documents",
        "corrections_file",
    }
)


@dataclass(frozen=True)
class _ResolvedSnapshot:
    root: Path
    lexical_root: Path


@dataclass(frozen=True)
class _OutputTarget:
    path: Path
    authoritative: bool


@dataclass(frozen=True)
class _ExportSnapshot:
    snapshot: ValidatedSnapshot
    corrections: CorrectionRegistry | None


class _AuthenticatedSnapshotFetcher:
    def __init__(self, snapshot: ValidatedSnapshot) -> None:
        self._documents = {
            document.link.p_doc_id: document for document in snapshot.documents
        }

    def fetch_document(self, p_doc_id: str | int) -> FetchedDocument:
        key = str(p_doc_id)
        document = self._documents[key]
        return FetchedDocument(
            p_doc_id=key,
            content=document.content,
            sha256=document.sha256,
            source_url=download_url(key),
        )


@dataclass(frozen=True)
class _CorrectionApplyingBundle:
    """Importer adapter that applies authenticated corrections during export."""

    corrections: CorrectionRegistry

    def manages(self, p_doc_id: str | int) -> bool:
        return self.corrections.manages(p_doc_id)

    def guard_source(self, p_doc_id: str | int, sha256: str) -> None:
        self.corrections.guard_source(p_doc_id, sha256)

    def apply_and_validate(
        self,
        session: Session,
        document: ScheduleDocument,
    ) -> CorrectionResult:
        corrections = self.corrections.documents[str(document.p_doc_id)]
        return apply_document_corrections(session, document, corrections)


def _absolute_lexical(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path.expanduser())))


def _resolve_snapshot(path: Path) -> _ResolvedSnapshot:
    lexical = _absolute_lexical(path)
    try:
        root = lexical.resolve(strict=True)
    except (OSError, RuntimeError) as error:
        raise SystemExit("ambiguous snapshot path") from error
    if not root.is_dir():
        raise SystemExit("snapshot path must resolve to a directory")
    return _ResolvedSnapshot(root=root, lexical_root=lexical)


def _is_inside(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def _resolve_output(path: Path, snapshot: _ResolvedSnapshot) -> _OutputTarget:
    lexical = _absolute_lexical(path)
    try:
        if lexical.is_symlink():
            raise SystemExit("ambiguous output path: final symlinks are not allowed")
        parent = lexical.parent.resolve(strict=True)
    except SystemExit:
        raise
    except (OSError, RuntimeError) as error:
        raise SystemExit("ambiguous output path") from error
    if not parent.is_dir():
        raise SystemExit("ambiguous output path: parent is not a directory")

    resolved = parent / lexical.name
    try:
        if resolved.exists() and not resolved.is_file():
            raise SystemExit("ambiguous output path: target is not a regular file")
    except OSError as error:
        raise SystemExit("ambiguous output path") from error

    authoritative_path = snapshot.root / _REVIEWED_FILENAME
    authoritative = resolved == authoritative_path
    inside = _is_inside(resolved, snapshot.root) or _is_inside(
        lexical,
        snapshot.lexical_root,
    )
    if inside and not authoritative:
        raise SystemExit(
            "refusing output path inside the snapshot directory; only "
            f"{_REVIEWED_FILENAME} is allowed"
        )
    return _OutputTarget(path=resolved, authoritative=authoritative)


def _validate_draft_v2(
    root: Path,
    payload: dict,
    *,
    allow_existing_reviewed: bool,
) -> _ExportSnapshot:
    """Authenticate the one incomplete manifest shape used to bootstrap v2."""
    snapshot_validation._check_exact_keys(
        payload,
        allowed=_DRAFT_V2_ROOT_KEYS,
        context="draft manifest v2",
    )
    if payload["version"] != 2 or isinstance(payload["version"], bool):
        raise SnapshotValidationError("unsupported draft manifest version")
    captured_at = snapshot_validation._strict_string(
        payload["captured_at"],
        context="captured_at",
    )
    source_index_url = snapshot_validation._strict_string(
        payload["source_index_url"],
        context="source_index_url",
    )
    if source_index_url != INDEX_URL:
        raise SnapshotValidationError(
            "snapshot is not tied to the official SFEDU index"
        )
    expected_counts = snapshot_validation._validate_expected_counts(
        payload["expected_counts"]
    )

    raw_documents = payload["documents"]
    if not isinstance(raw_documents, list) or not raw_documents:
        raise SnapshotValidationError("snapshot document list is empty")
    documents: list[SnapshotDocument] = []
    document_hashes: dict[str, str] = {}
    declared_names = {"manifest.json"}
    for index, raw in enumerate(raw_documents):
        if not isinstance(raw, dict):
            raise SnapshotValidationError(
                f"snapshot document {index} metadata must be an object"
            )
        snapshot_validation._check_exact_keys(
            raw,
            allowed=snapshot_validation._V2_DOCUMENT_KEYS,
            context=f"snapshot document {index}",
        )
        p_doc_id = snapshot_validation._canonical_document_id(raw["p_doc_id"])
        if p_doc_id in document_hashes:
            raise SnapshotValidationError(f"duplicate document id {p_doc_id}")
        section = snapshot_validation._strict_string(
            raw["section"],
            context=f"document {p_doc_id} section",
        )
        label = snapshot_validation._strict_string(
            raw["label"],
            context=f"document {p_doc_id} label",
        )
        asset = snapshot_validation._validated_asset(
            root,
            {key: raw[key] for key in snapshot_validation._ASSET_KEYS},
            label=f"document {p_doc_id}",
        )
        if not asset.content.startswith(b"%PDF-"):
            raise SnapshotValidationError(
                f"snapshot file is not a PDF: {asset.path.name}"
            )
        if asset.path.name in declared_names:
            raise SnapshotValidationError(
                f"duplicate declared filename: {asset.path.name}"
            )
        declared_names.add(asset.path.name)
        document_hashes[p_doc_id] = asset.sha256
        documents.append(
            SnapshotDocument(
                link=ScheduleLink(
                    section=section,
                    label=label,
                    p_doc_id=p_doc_id,
                ),
                asset=asset,
            )
        )

    if expected_counts["documents"] != len(documents):
        raise SnapshotValidationError(
            "expected_counts.documents does not match declared documents"
        )
    corrections_asset = snapshot_validation._validated_asset(
        root,
        payload["corrections_file"],
        label="corrections",
    )
    if corrections_asset.path.name in declared_names:
        raise SnapshotValidationError(
            f"duplicate declared filename: {corrections_asset.path.name}"
        )
    declared_names.add(corrections_asset.path.name)
    if _REVIEWED_FILENAME in declared_names:
        raise SnapshotValidationError(
            f"draft source asset uses reserved output filename: {_REVIEWED_FILENAME}"
        )

    actual_names = {path.name for path in root.iterdir()}
    allowed_extras = {_REVIEWED_FILENAME} if allow_existing_reviewed else set()
    extras = sorted(actual_names - declared_names - allowed_extras)
    missing = sorted(declared_names - actual_names)
    if extras or missing:
        raise SnapshotValidationError(
            "draft snapshot contains undeclared files: "
            + ", ".join(extras or missing)
        )

    try:
        corrections = parse_correction_registry(corrections_asset.content)
        if not corrections.documents:
            raise ReviewValidationError(
                "draft correction registry must manage at least one document"
            )
        unknown = sorted(
            set(corrections.documents) - document_hashes.keys(),
            key=int,
        )
        if unknown:
            raise ReviewValidationError(
                "correction registry references undeclared documents: "
                + ", ".join(unknown)
            )
        for p_doc_id in corrections.documents:
            corrections.guard_source(p_doc_id, document_hashes[p_doc_id])
    except ReviewValidationError as error:
        raise SnapshotValidationError(
            f"draft corrections file is invalid: {error}"
        ) from error

    return _ExportSnapshot(
        snapshot=ValidatedSnapshot(
            captured_at=captured_at,
            expected_counts=expected_counts,
            documents=tuple(documents),
            review_bundle=None,
        ),
        corrections=corrections,
    )


def _load_export_snapshot(
    root: Path,
    *,
    allow_existing_reviewed: bool,
) -> _ExportSnapshot:
    payload, version = snapshot_validation._manifest_payload(root / "manifest.json")
    if version == 2 and payload.keys() == _DRAFT_V2_ROOT_KEYS:
        return _validate_draft_v2(
            root,
            payload,
            allow_existing_reviewed=allow_existing_reviewed,
        )

    snapshot = validate_snapshot(root)
    corrections = (
        snapshot.review_bundle.corrections
        if snapshot.review_bundle is not None
        else None
    )
    return _ExportSnapshot(snapshot=snapshot, corrections=corrections)


def _database_counts(session: Session) -> dict[str, int]:
    return {
        "documents": int(
            session.scalar(select(func.count()).select_from(ScheduleDocument)) or 0
        ),
        "groups": int(session.scalar(select(func.count()).select_from(Group)) or 0),
        "lessons": int(session.scalar(select(func.count()).select_from(Lesson)) or 0),
        "calendar_weeks": int(
            session.scalar(select(func.count()).select_from(WeekCalendar)) or 0
        ),
        "exams": int(session.scalar(select(func.count()).select_from(ExamEvent)) or 0),
        "unparsed": int(
            session.scalar(select(func.count()).select_from(UnparsedCell)) or 0
        ),
    }


def _build_reviewed_payload(export_snapshot: _ExportSnapshot) -> dict:
    snapshot = export_snapshot.snapshot
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False)
    session = session_factory()
    try:
        correction_bundle = (
            _CorrectionApplyingBundle(export_snapshot.corrections)
            if export_snapshot.corrections is not None
            else None
        )
        report = import_all(
            session,
            _AuthenticatedSnapshotFetcher(snapshot),
            links=[document.link for document in snapshot.documents],
            atomic=True,
            review_bundle=correction_bundle,
        )
        session.flush()
        counts = _database_counts(session)
        if report.failed or report.missing or counts != dict(snapshot.expected_counts):
            raise SnapshotValidationError(
                "imported snapshot does not match the reviewed corpus: "
                f"expected {dict(snapshot.expected_counts)}, got {counts}"
            )

        imported = session.scalars(
            select(ScheduleDocument).order_by(ScheduleDocument.p_doc_id)
        ).all()
        expected_ids = {document.link.p_doc_id for document in snapshot.documents}
        actual_ids = {str(document.p_doc_id) for document in imported}
        if actual_ids != expected_ids:
            raise SnapshotValidationError(
                "imported schedule documents do not match the snapshot"
            )

        output_ids = (
            set(export_snapshot.corrections.documents)
            if export_snapshot.corrections is not None
            else expected_ids
        )
        documents = {}
        for document in imported:
            if str(document.p_doc_id) not in output_ids:
                continue
            reviewed = reviewed_document_output(session, document)
            documents[reviewed.p_doc_id] = {
                "sha256": reviewed.sha256,
                "lesson_hash": reviewed.lesson_hash,
                "signatures": list(reviewed.signatures),
            }
        return {"version": 1, "documents": documents}
    finally:
        session.rollback()
        session.close()
        engine.dispose()


def _atomic_write(path: Path, payload: dict) -> None:
    content = (
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def export_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Export a deterministic reviewed schedule candidate.",
    )
    parser.add_argument("--snapshot-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--confirm")
    args = parser.parse_args(argv)

    resolved_snapshot = _resolve_snapshot(args.snapshot_dir)
    output = _resolve_output(args.output, resolved_snapshot)
    if output.authoritative and args.confirm != CONFIRMATION:
        raise SystemExit(
            "authoritative reviewed_schedule.json requires rendered-PDF "
            f"confirmation: --confirm {CONFIRMATION}"
        )

    snapshot = _load_export_snapshot(
        resolved_snapshot.root,
        allow_existing_reviewed=output.authoritative,
    )
    payload = _build_reviewed_payload(snapshot)
    _atomic_write(output.path, payload)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(export_main())
