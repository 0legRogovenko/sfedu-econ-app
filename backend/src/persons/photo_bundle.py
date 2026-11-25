"""Source-backed mobile portraits. No database or production writes."""

from __future__ import annotations

import base64
from collections.abc import Iterable
from dataclasses import dataclass
import hashlib
from io import BytesIO
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

from PIL import Image, UnidentifiedImageError

from src.persons.extract import find_names
from src.persons.names import person_key
from src.persons.photos import PhotoCandidate, official_url


def official_profile_photos(candidates: Iterable[PhotoCandidate]) -> list[PhotoCandidate]:
    """Allow reviewed personal pages only; faculty listing cards are excluded."""
    result = []
    for candidate in candidates:
        source = official_url(candidate.source_url)
        photo = official_url(candidate.photo_url, source or "")
        if source and photo:
            url = urlsplit(source)
            if (url.hostname == "sfedu.ru"
                    and re.fullmatch(r"/s7/person/(?:ru/)?[\w.-]+/?", url.path)
                    and urlsplit(photo).hostname in {"sfedu.ru", "econ.sfedu.ru"}):
                result.append(candidate)
    return result


def prune_unused_portraits(app_dir: Path, records: dict[str, dict]) -> None:
    """Remove only unchanged, content-addressed files produced by this bundler."""
    retained = {record["asset"] for record in records.values()}
    for path in (app_dir / "assets/people").iterdir():
        if path.is_symlink() or not path.is_file():
            continue
        if not re.fullmatch(r"[0-9a-f]{24}\.(?:jpg|png|webp)", path.name):
            continue
        if path.relative_to(app_dir).as_posix() in retained:
            continue
        if hashlib.sha256(path.read_bytes()).hexdigest().startswith(path.stem):
            path.unlink()


@dataclass(frozen=True)
class BundlePerson:
    id: str
    key: tuple[str, str, str]
    full_name: str
    short_name: str


def parse_people(rows: list[dict]) -> list[BundlePerson]:
    people = []
    seen = set()
    for row in rows:
        person_id = row["id"]
        try:
            key = tuple(base64.urlsafe_b64decode(person_id + "=" * (-len(person_id) % 4)).decode().split("\x1f"))
        except (ValueError, UnicodeDecodeError) as exc:
            raise ValueError("Invalid directory identity") from exc
        names = find_names(row["short_name"])
        if len(key) != 3 or len(names) != 1 or person_key(*names[0]) != key or person_id in seen:
            raise ValueError(f"Directory identity mismatch: {row['short_name']}")
        people.append(BundlePerson(person_id, key, row["full_name"], row["short_name"]))
        seen.add(person_id)
    return people


def validate_image(data: bytes) -> str:
    if not data or len(data) > 10 * 1024 * 1024:
        raise ValueError("Image is empty or exceeds 10 MiB")
    try:
        with Image.open(BytesIO(data)) as image:
            extension = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}.get(image.format)
            if extension is None or image.width * image.height > 40_000_000:
                raise ValueError("Unsupported image format or dimensions")
            image.verify()
        with Image.open(BytesIO(data)) as image:
            image.load()
    except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError) as exc:
        raise ValueError("Invalid photograph bytes") from exc
    return extension


def render_catalog(records: dict[str, dict]) -> str:
    def literal(value: str) -> str:
        return json.dumps(value, ensure_ascii=False).replace("$", r"\$")

    lines = ["// Generated from assets/people/portraits.json; do not edit by hand.",
             "part of 'portrait_catalog.dart';", "",
             "const _bundledPortraits = <String, ({String fullName, String assetPath})>{"]
    for person_id, record in sorted(records.items()):
        lines.append(f"  {literal(person_id)}: (fullName: {literal(record['directory_name'])}, assetPath: {literal(record['asset'])}),")
    return "\n".join([*lines, "};", ""])
