"""Bundle reviewed original SFEDU images for a mobile release, without DB writes.

python scripts/bundle_person_photos.py --people-json /path/to/people.json \
  --snapshot data/person_photos/2026-11-24.json --app-dir ../app
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.persons.photo_bundle import parse_people, render_catalog, validate_image
from src.persons.photos import PhotoCandidate, match_photos, official_url
from src.sfedu_tls import SfeduTLSAdapter
from urllib.parse import urlsplit


def download_group(items, app_dir, cache_dir):
    session = requests.Session()
    session.mount("https://sfedu.ru/", SfeduTLSAdapter())
    session.headers["User-Agent"] = "EconYufuApp/0.1 (official public staff portraits)"
    records, errors = {}, {}
    last_request = 0.0
    for person, candidate in items:
        try:
            cache = cache_dir / hashlib.sha256(candidate.photo_url.encode()).hexdigest()
            if cache.exists():
                data = cache.read_bytes()
            else:
                host = urlsplit(candidate.photo_url).hostname
                delay = 30 if host == "sfedu.ru" else 5
                time.sleep(max(0, last_request + delay - time.monotonic()))
                last_request = time.monotonic()
                with session.get(candidate.photo_url, timeout=(10, 30), stream=True, allow_redirects=False) as response:
                    response.raise_for_status()
                    if response.is_redirect:
                        raise ValueError("Redirect requires source review")
                    chunks, size = [], 0
                    for chunk in response.iter_content(65536):
                        size += len(chunk)
                        if size > 10 * 1024 * 1024:
                            raise ValueError("Photograph exceeds size bound")
                        chunks.append(chunk)
                    data = b"".join(chunks)
                validate_image(data)
                cache.write_bytes(data)
            extension = validate_image(data)
            digest = hashlib.sha256(data).hexdigest()
            asset = f"assets/people/{digest[:24]}.{extension}"
            (app_dir / asset).write_bytes(data)
            records[person.id] = {**asdict(candidate), "directory_name": person.full_name,
                                  "asset": asset, "sha256": digest, "bytes": len(data)}
            print(f"Bundled {person.short_name}", flush=True)
        except (requests.RequestException, ValueError) as exc:
            errors[person.id] = f"{type(exc).__name__}: {exc}"
            print(f"Unavailable: {person.short_name}: {type(exc).__name__}", flush=True)
    session.close()
    return records, errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--people-json", type=Path, required=True)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--app-dir", type=Path, required=True)
    parser.add_argument("--cache-dir", type=Path, required=True)
    parser.add_argument("--reviewed-aliases", type=Path)
    args = parser.parse_args()
    people = parse_people(json.loads(args.people_json.read_text()))
    candidates = [PhotoCandidate(**r) for r in json.loads(args.snapshot.read_text())["photos"]]
    aliases = json.loads(args.reviewed_aliases.read_text()) if args.reviewed_aliases else {}
    matches = match_photos(people, candidates, reviewed_aliases={k: v["full_name"] for k, v in aliases.items()})
    groups = defaultdict(list)
    for person in people:
        candidate = matches.matches.get(person.id)
        if candidate and official_url(candidate.photo_url):
            groups[urlsplit(candidate.photo_url).hostname].append((person, candidate))
    (args.app_dir / "assets/people").mkdir(parents=True, exist_ok=True)
    args.cache_dir.mkdir(parents=True, exist_ok=True)
    records, errors = {}, {}
    with ThreadPoolExecutor(max_workers=2) as executor:
        for result, failures in executor.map(lambda items: download_group(items, args.app_dir, args.cache_dir), groups.values()):
            records.update(result)
            errors.update(failures)
    if not records:
        raise ValueError("No official photographs were downloaded")
    report = {"collected_at": datetime.now(timezone.utc).isoformat(), "people": len(people),
              "reviewed_aliases_sha256": hashlib.sha256(args.reviewed_aliases.read_bytes()).hexdigest() if args.reviewed_aliases else None,
              "portraits": records, "missing": [p.short_name for p in people if p.id not in records],
              "ambiguous": [p.short_name for p in people if p.id in matches.ambiguous], "download_errors": errors}
    (args.app_dir / "assets/people/portraits.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    (args.app_dir / "lib/features/people/portrait_catalog.g.dart").write_text(render_catalog(records))
    print(f"Bundled {len(records)} / {len(people)} profiles; errors {len(errors)}; database writes: 0", flush=True)


if __name__ == "__main__":
    main()
