"""Preview or apply a photo-only update from reviewed official source metadata.

    python -m src.persons.photo_import data/person_photos/2026-11-24.json
    python -m src.persons.photo_import data/person_photos/2026-11-24.json --apply

No contacts, emails, overrides, teachers or timetable rows are written here.
"""

from __future__ import annotations

import argparse
from collections.abc import Iterable
from dataclasses import asdict
import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models import PersonPhoto
from src.persons.directory import build_directory
from src.persons.photos import PhotoCandidate, PhotoMatches, match_photos


def store_photos(db: Session, candidates: Iterable[PhotoCandidate]) -> PhotoMatches:
    report = match_photos(build_directory(db), candidates)
    stored = {photo.person_id: photo for photo in db.scalars(select(PersonPhoto))}
    for person_id, candidate in report.matches.items():
        photo = stored.get(person_id)
        if photo is None:
            db.add(PersonPhoto(person_id=person_id, **asdict(candidate)))
        else:
            photo.full_name = candidate.full_name
            photo.photo_url = candidate.photo_url
            photo.source_url = candidate.source_url
    db.flush()
    return report


def main() -> None:
    from src.database import SessionLocal

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("--apply", action="store_true", help="Commit matched portrait metadata only")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    snapshot = json.loads(args.snapshot.read_text())
    candidates = [PhotoCandidate(**row) for row in snapshot["photos"]]
    if not candidates:
        raise ValueError("Empty portrait snapshot; nothing was changed")
    with SessionLocal() as db:
        people = build_directory(db)
        report = store_photos(db, candidates) if args.apply else match_photos(people, candidates)
        result = {
            "people": len(people),
            "matched": len(report.matches),
            "missing": [p.short_name for p in people if p.id in report.missing],
            "ambiguous": [p.short_name for p in people if p.id in report.ambiguous],
            "applied": args.apply,
        }
        if args.apply:
            db.commit()
        if args.report:
            args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
