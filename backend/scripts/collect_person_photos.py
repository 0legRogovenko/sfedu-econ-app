"""Collect portrait metadata from saved official pages; never write the database.

Save public personal profile pages with verified TLS and a pause between
requests, recording their official URLs in sources.json, then run:

    python scripts/collect_person_photos.py --pages-dir /path/to/pages --output photos.json

The manifest records source hashes so subsequent matching can be reviewed
without refetching the site. Named staff profiles on faculty pages are valid;
unrelated pictures elsewhere on those pages are never extracted as portraits.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.persons.photos import official_url, parse_photo_page


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pages-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    sources_file = args.pages_dir / "sources.json"
    explicit = json.loads(sources_file.read_text()) if sources_file.exists() else {}
    # A URL list from the collection log needs no special mapping for faculty pages.
    if isinstance(explicit, list):
        explicit = {}
    photos = []
    sources = []
    for path in sorted(args.pages_dir.glob("*.html")):
        url = explicit.get(path.name)
        if url is None and (path.stem.startswith("kafedra-") or path.stem == "o-fakultete"):
            url = f"https://econ.sfedu.ru/{path.stem}/"
        if not url:
            continue
        if official_url(url) is None:
            raise ValueError(f"Not an official HTTPS source: {path.name}")
        raw = path.read_bytes()
        candidates = parse_photo_page(raw.decode("utf-8"), url)
        sources.append({"url": url, "sha256": hashlib.sha256(raw).hexdigest(), "photos": len(candidates)})
        photos.extend(asdict(candidate) for candidate in candidates)
    if not photos:
        raise ValueError("No named official photographs were found; database data was not changed")
    manifest = {
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "sources": sources,
        "photos": photos,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(f"Sources: {len(sources)}; named portrait cards: {len(photos)}; database writes: 0")


if __name__ == "__main__":
    main()
