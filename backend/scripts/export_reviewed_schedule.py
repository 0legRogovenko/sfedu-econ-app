"""Export parser baselines and explicitly confirmed reviewed schedule output."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from sqlalchemy import create_engine, func, select  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

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
    apply_document_corrections,
    reviewed_document_output,
)
from src.schedule.source import download_url  # noqa: E402
from src.schedule.validated_snapshot import (  # noqa: E402
    SnapshotValidationError,
    ValidatedSnapshot,
    validate_snapshot,
)


CONFIRMATION = "I_REVIEWED_EVERY_RENDERED_GROUP"
_REVIEWED_FILENAME = "reviewed_schedule.json"


@dataclass(frozen=True)
class _ResolvedSnapshot:
    root: Path
    lexical_root: Path


@dataclass(frozen=True)
class _OutputTarget:
    path: Path
    authoritative: bool


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


def _build_reviewed_payload(snapshot: ValidatedSnapshot) -> dict:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False)
    session = session_factory()
    try:
        correction_registry = (
            snapshot.review_bundle.corrections
            if snapshot.review_bundle is not None
            else CorrectionRegistry(documents=MappingProxyType({}))
        )
        correction_bundle = (
            _CorrectionApplyingBundle(correction_registry)
            if snapshot.review_bundle is not None
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

        documents = {}
        for document in imported:
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

    snapshot = validate_snapshot(resolved_snapshot.root)
    payload = _build_reviewed_payload(snapshot)
    _atomic_write(output.path, payload)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(export_main())
