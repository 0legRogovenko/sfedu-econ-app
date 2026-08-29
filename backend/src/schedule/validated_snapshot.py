"""Explicit emergency import of a reviewed official SFEDU schedule snapshot.

The daily importer remains live and fail-closed.  This module is only for a
manual beta recovery when the official index is available but file responses
are truncated upstream.  Every local PDF is checked against the committed
size and SHA-256 before the database transaction starts.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.database import SessionLocal
from src.models import (
    ExamEvent,
    Group,
    Lesson,
    ScheduleDocument,
    UnparsedCell,
    WeekCalendar,
)
from src.schedule.fetch import FetchedDocument
from src.schedule.importer import import_all
from src.schedule.source import INDEX_URL, ScheduleLink, download_url

DEFAULT_SNAPSHOT_DIR = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "schedule_snapshot"
    / "2026-08-28"
)


class SnapshotValidationError(RuntimeError):
    """The committed files, manifest, or imported result are inconsistent."""


@dataclass(frozen=True)
class SnapshotDocument:
    link: ScheduleLink
    path: Path
    content: bytes
    sha256: str


@dataclass(frozen=True)
class ValidatedSnapshot:
    captured_at: str
    expected_counts: dict[str, int]
    documents: tuple[SnapshotDocument, ...]


class _SnapshotFetcher:
    def __init__(self, documents: tuple[SnapshotDocument, ...]) -> None:
        self._documents = {document.link.p_doc_id: document for document in documents}

    def fetch_document(self, p_doc_id: str | int) -> FetchedDocument:
        key = str(p_doc_id)
        try:
            document = self._documents[key]
        except KeyError as error:  # pragma: no cover - links come from the same manifest
            raise SnapshotValidationError(f"document {key} is absent from snapshot") from error
        return FetchedDocument(
            p_doc_id=key,
            content=document.content,
            sha256=document.sha256,
            source_url=download_url(key),
        )


def validate_snapshot(
    snapshot_dir: Path = DEFAULT_SNAPSHOT_DIR,
) -> ValidatedSnapshot:
    """Read and authenticate all snapshot assets without touching the database."""
    root = snapshot_dir.resolve()
    manifest_path = root / "manifest.json"
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SnapshotValidationError("snapshot manifest is missing or invalid") from error

    if payload.get("version") != 1:
        raise SnapshotValidationError("unsupported snapshot manifest version")
    if payload.get("source_index_url") != INDEX_URL:
        raise SnapshotValidationError("snapshot is not tied to the official SFEDU index")

    expected_counts = payload.get("expected_counts")
    if not isinstance(expected_counts, dict) or not expected_counts:
        raise SnapshotValidationError("snapshot expected_counts are missing")

    raw_documents = payload.get("documents")
    if not isinstance(raw_documents, list) or not raw_documents:
        raise SnapshotValidationError("snapshot document list is empty")

    documents: list[SnapshotDocument] = []
    seen_ids: set[str] = set()
    for raw in raw_documents:
        try:
            p_doc_id = str(raw["p_doc_id"])
            filename = str(raw["filename"])
            expected_size = int(raw["bytes"])
            expected_sha256 = str(raw["sha256"])
            section = str(raw["section"])
            label = str(raw["label"])
        except (KeyError, TypeError, ValueError) as error:
            raise SnapshotValidationError("snapshot document metadata is invalid") from error

        if not p_doc_id.isascii() or not p_doc_id.isdigit() or p_doc_id in seen_ids:
            raise SnapshotValidationError(f"invalid or duplicate document id: {p_doc_id}")
        seen_ids.add(p_doc_id)

        path = root / filename
        if path.name != filename or path.parent.resolve() != root:
            raise SnapshotValidationError(f"unsafe snapshot filename: {filename}")
        try:
            content = path.read_bytes()
        except OSError as error:
            raise SnapshotValidationError(f"snapshot file is missing: {filename}") from error

        actual_sha256 = hashlib.sha256(content).hexdigest()
        if len(content) != expected_size or actual_sha256 != expected_sha256:
            raise SnapshotValidationError(
                f"snapshot integrity mismatch: {filename}"
            )
        if not content.startswith(b"%PDF-"):
            raise SnapshotValidationError(f"snapshot file is not a PDF: {filename}")

        documents.append(
            SnapshotDocument(
                link=ScheduleLink(section=section, label=label, p_doc_id=p_doc_id),
                path=path,
                content=content,
                sha256=actual_sha256,
            )
        )

    declared_files = {"manifest.json", *(document.path.name for document in documents)}
    actual_files = {path.name for path in root.iterdir() if path.is_file()}
    if actual_files != declared_files:
        unexpected = sorted(actual_files - declared_files)
        raise SnapshotValidationError(
            "snapshot contains unexpected files: " + ", ".join(unexpected)
        )

    return ValidatedSnapshot(
        captured_at=str(payload.get("captured_at", "")),
        expected_counts={str(key): int(value) for key, value in expected_counts.items()},
        documents=tuple(documents),
    )


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


def import_validated_snapshot(
    session: Session,
    snapshot_dir: Path = DEFAULT_SNAPSHOT_DIR,
) -> dict[str, Any]:
    """Import all authenticated files atomically and enforce exact corpus counts."""
    snapshot = validate_snapshot(snapshot_dir)
    links = [document.link for document in snapshot.documents]
    fetcher = _SnapshotFetcher(snapshot.documents)

    try:
        report = import_all(session, fetcher, links=links, atomic=True)
        counts = _database_counts(session)
        if report.failed or report.missing or counts != snapshot.expected_counts:
            raise SnapshotValidationError(
                "imported snapshot does not match the reviewed corpus: "
                f"expected {snapshot.expected_counts}, got {counts}"
            )
        session.commit()
    except Exception:
        session.rollback()
        raise

    return {
        "status": "ok",
        "captured_at": snapshot.captured_at,
        "counts": counts,
        "documents": [
            {"p_doc_id": document.p_doc_id, "status": document.status}
            for document in report.documents
        ],
    }


def main() -> None:
    session = SessionLocal()
    try:
        result = import_validated_snapshot(session)
    finally:
        session.close()
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":  # pragma: no cover
    main()
