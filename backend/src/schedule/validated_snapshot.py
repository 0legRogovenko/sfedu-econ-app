"""Explicit emergency import of a reviewed official SFEDU schedule snapshot.

The daily importer remains live and fail-closed.  This module is only for a
manual beta recovery when the official index is available but file responses
are truncated upstream.  Every local PDF is checked against the committed
size and SHA-256 before the database transaction starts.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
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
from src.schedule.reviewed_schedule import (
    ReviewBundle,
    ReviewValidationError,
    parse_correction_registry,
    parse_reviewed_documents,
)
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
class SnapshotAsset:
    path: Path
    content: bytes
    sha256: str


@dataclass(frozen=True)
class SnapshotDocument:
    link: ScheduleLink
    asset: SnapshotAsset

    @property
    def path(self) -> Path:
        return self.asset.path

    @property
    def content(self) -> bytes:
        return self.asset.content

    @property
    def sha256(self) -> str:
        return self.asset.sha256


@dataclass(frozen=True)
class ValidatedSnapshot:
    captured_at: str
    expected_counts: Mapping[str, int]
    documents: tuple[SnapshotDocument, ...]
    review_bundle: ReviewBundle | None


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


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_V2_ROOT_KEYS = frozenset(
    {
        "version",
        "captured_at",
        "source_index_url",
        "expected_counts",
        "documents",
        "corrections_file",
        "reviewed_schedule_file",
    }
)
_V2_DOCUMENT_KEYS = frozenset(
    {"p_doc_id", "section", "label", "filename", "bytes", "sha256"}
)
_ASSET_KEYS = frozenset({"filename", "bytes", "sha256"})
_EXPECTED_COUNT_KEYS = frozenset(
    {"documents", "groups", "lessons", "calendar_weeks", "exams", "unparsed"}
)


def _duplicate_json_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise SnapshotValidationError(f"duplicate JSON key {key}")
        result[key] = value
    return result


def _manifest_payload(manifest_path: Path) -> tuple[dict, int]:
    try:
        content = manifest_path.read_bytes()
        payload = json.loads(
            content.decode("utf-8"),
            object_pairs_hook=_duplicate_json_object,
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise SnapshotValidationError(
            "snapshot manifest is missing or invalid"
        ) from error
    if not isinstance(payload, dict):
        raise SnapshotValidationError("snapshot manifest is missing or invalid")
    version = payload.get("version")
    if isinstance(version, bool) or not isinstance(version, int):
        raise SnapshotValidationError("unsupported snapshot manifest version")
    if version == 1:
        return payload, 1
    if version != 2:
        raise SnapshotValidationError("unsupported snapshot manifest version")
    return payload, 2


def _check_exact_keys(value: dict, *, allowed: frozenset[str], context: str) -> None:
    missing = sorted(allowed - value.keys())
    unknown = sorted(value.keys() - allowed)
    if missing:
        raise SnapshotValidationError(
            f"{context}: missing keys: {', '.join(missing)}"
        )
    if unknown:
        raise SnapshotValidationError(
            f"{context}: unknown keys: {', '.join(unknown)}"
        )


def _strict_string(value, *, context: str) -> str:
    if not isinstance(value, str):
        raise SnapshotValidationError(f"{context} must be a string")
    return value


def _canonical_document_id(value) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[1-9][0-9]*", value) is None:
        raise SnapshotValidationError(f"invalid document id: {value!r}")
    return value


def _nonnegative_integer(value, *, context: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise SnapshotValidationError(f"{context} must be a nonnegative integer")
    return value


def _sha256(value, *, context: str) -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise SnapshotValidationError(f"{context} has invalid SHA-256")
    return value


def _validated_asset(root: Path, metadata, *, label: str) -> SnapshotAsset:
    if not isinstance(metadata, dict):
        raise SnapshotValidationError(f"{label} metadata must be an object")
    _check_exact_keys(metadata, allowed=_ASSET_KEYS, context=f"{label} metadata")
    filename = _strict_string(metadata["filename"], context=f"{label} filename")
    if (
        not filename
        or filename in {".", ".."}
        or "/" in filename
        or "\\" in filename
        or Path(filename).is_absolute()
        or Path(filename).name != filename
    ):
        raise SnapshotValidationError(f"unsafe {label} filename: {filename}")
    expected_size = _nonnegative_integer(
        metadata["bytes"],
        context=f"{label} bytes",
    )
    expected_sha256 = _sha256(
        metadata["sha256"],
        context=f"{label} metadata",
    )
    path = root / filename
    resolved = path.resolve()
    if resolved.parent != root:
        raise SnapshotValidationError(f"unsafe {label} filename: {filename}")
    try:
        content = resolved.read_bytes()
    except OSError as error:
        raise SnapshotValidationError(f"{label} file is missing: {filename}") from error
    actual_sha256 = hashlib.sha256(content).hexdigest()
    if len(content) != expected_size or actual_sha256 != expected_sha256:
        raise SnapshotValidationError(f"{label} integrity mismatch: {filename}")
    return SnapshotAsset(
        path=resolved,
        content=content,
        sha256=actual_sha256,
    )


def _validate_v1_snapshot(root: Path, payload: dict) -> ValidatedSnapshot:
    """Keep the committed legacy manifest readable until Task 8 switches it."""
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
            raise SnapshotValidationError(
                "snapshot document metadata is invalid"
            ) from error

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
            raise SnapshotValidationError(f"snapshot integrity mismatch: {filename}")
        if not content.startswith(b"%PDF-"):
            raise SnapshotValidationError(f"snapshot file is not a PDF: {filename}")

        documents.append(
            SnapshotDocument(
                link=ScheduleLink(section=section, label=label, p_doc_id=p_doc_id),
                asset=SnapshotAsset(
                    path=path,
                    content=content,
                    sha256=actual_sha256,
                ),
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
        expected_counts=MappingProxyType(
            {str(key): int(value) for key, value in expected_counts.items()}
        ),
        documents=tuple(documents),
        review_bundle=None,
    )


def _validate_expected_counts(value) -> Mapping[str, int]:
    if not isinstance(value, dict):
        raise SnapshotValidationError("expected_counts must be an object")
    _check_exact_keys(
        value,
        allowed=_EXPECTED_COUNT_KEYS,
        context="expected_counts",
    )
    counts = {
        key: _nonnegative_integer(value[key], context=f"expected_counts.{key}")
        for key in sorted(_EXPECTED_COUNT_KEYS)
    }
    if counts["exams"] != 0:
        raise SnapshotValidationError("expected_counts.exams must be exactly 0")
    return MappingProxyType(counts)


def _validate_v2_snapshot(root: Path, payload: dict) -> ValidatedSnapshot:
    _check_exact_keys(payload, allowed=_V2_ROOT_KEYS, context="manifest v2")
    if payload["version"] != 2 or isinstance(payload["version"], bool):
        raise SnapshotValidationError("unsupported snapshot manifest version")
    captured_at = _strict_string(payload["captured_at"], context="captured_at")
    source_index_url = _strict_string(
        payload["source_index_url"],
        context="source_index_url",
    )
    if source_index_url != INDEX_URL:
        raise SnapshotValidationError("snapshot is not tied to the official SFEDU index")
    expected_counts = _validate_expected_counts(payload["expected_counts"])

    raw_documents = payload["documents"]
    if not isinstance(raw_documents, list) or not raw_documents:
        raise SnapshotValidationError("snapshot document list is empty")
    documents: list[SnapshotDocument] = []
    seen_ids: set[str] = set()
    declared_names = {"manifest.json"}
    document_hashes: dict[str, str] = {}
    for index, raw in enumerate(raw_documents):
        if not isinstance(raw, dict):
            raise SnapshotValidationError(
                f"snapshot document {index} metadata must be an object"
            )
        _check_exact_keys(
            raw,
            allowed=_V2_DOCUMENT_KEYS,
            context=f"snapshot document {index}",
        )
        p_doc_id = _canonical_document_id(raw["p_doc_id"])
        if p_doc_id in seen_ids:
            raise SnapshotValidationError(f"duplicate document id {p_doc_id}")
        seen_ids.add(p_doc_id)
        section = _strict_string(raw["section"], context=f"document {p_doc_id} section")
        label = _strict_string(raw["label"], context=f"document {p_doc_id} label")
        asset = _validated_asset(
            root,
            {key: raw[key] for key in _ASSET_KEYS},
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
                link=ScheduleLink(section=section, label=label, p_doc_id=p_doc_id),
                asset=asset,
            )
        )

    corrections_asset = _validated_asset(
        root,
        payload["corrections_file"],
        label="corrections",
    )
    reviewed_asset = _validated_asset(
        root,
        payload["reviewed_schedule_file"],
        label="reviewed schedule",
    )
    for asset in (corrections_asset, reviewed_asset):
        if asset.path.name in declared_names:
            raise SnapshotValidationError(
                f"duplicate declared filename: {asset.path.name}"
            )
        declared_names.add(asset.path.name)

    actual_names = {path.name for path in root.iterdir()}
    if actual_names != declared_names:
        extras = sorted(actual_names - declared_names)
        missing = sorted(declared_names - actual_names)
        details = extras or missing
        raise SnapshotValidationError(
            "snapshot contains undeclared files: " + ", ".join(details)
        )

    try:
        corrections = parse_correction_registry(corrections_asset.content)
    except ReviewValidationError as error:
        raise SnapshotValidationError(
            f"corrections file is invalid: {error}"
        ) from error
    try:
        reviewed_documents = parse_reviewed_documents(reviewed_asset.content)
    except ReviewValidationError as error:
        raise SnapshotValidationError(
            f"reviewed schedule file is invalid: {error}"
        ) from error
    try:
        review_bundle = ReviewBundle(
            corrections=corrections,
            reviewed_documents=reviewed_documents,
        )
        unknown = sorted(
            set(review_bundle.corrections.documents) - document_hashes.keys(),
            key=int,
        )
        if unknown:
            raise ReviewValidationError(
                "review bundle references undeclared documents: " + ", ".join(unknown)
            )
        missing = sorted(
            document_hashes.keys() - set(review_bundle.corrections.documents),
            key=int,
        )
        if missing:
            raise ReviewValidationError(
                "review bundle omits declared documents: " + ", ".join(missing)
            )
        for p_doc_id in review_bundle.corrections.documents:
            review_bundle.guard_source(p_doc_id, document_hashes[p_doc_id])
    except ReviewValidationError as error:
        raise SnapshotValidationError(f"review bundle is invalid: {error}") from error

    return ValidatedSnapshot(
        captured_at=captured_at,
        expected_counts=expected_counts,
        documents=tuple(documents),
        review_bundle=review_bundle,
    )


def validate_snapshot(
    snapshot_dir: Path = DEFAULT_SNAPSHOT_DIR,
) -> ValidatedSnapshot:
    """Read and authenticate all snapshot assets without touching the database."""
    root = snapshot_dir.resolve()
    manifest_path = root / "manifest.json"
    payload, version = _manifest_payload(manifest_path)
    if version == 1:
        return _validate_v1_snapshot(root, payload)
    return _validate_v2_snapshot(root, payload)


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
        report = import_all(
            session,
            fetcher,
            links=links,
            atomic=True,
            review_bundle=snapshot.review_bundle,
        )
        counts = _database_counts(session)
        if report.failed or report.missing or counts != snapshot.expected_counts:
            raise SnapshotValidationError(
                "imported snapshot does not match the reviewed corpus: "
                f"expected {snapshot.expected_counts}, got {counts}"
            )
        session.commit()
    except ReviewValidationError as error:
        session.rollback()
        raise SnapshotValidationError(str(error)) from error
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
