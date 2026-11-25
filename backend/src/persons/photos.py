"""Official portraits for the existing directory, without creating people."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Protocol
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from src.persons.names import key_of_full, parse_person, person_key


class DirectoryIdentity(Protocol):
    key: tuple[str, str, str]
    full_name: str

    @property
    def id(self) -> str: ...


@dataclass(frozen=True)
class PhotoCandidate:
    full_name: str
    photo_url: str
    source_url: str


@dataclass
class PhotoMatches:
    matches: dict[str, PhotoCandidate] = field(default_factory=dict)
    missing: list[str] = field(default_factory=list)
    ambiguous: list[str] = field(default_factory=list)


def official_url(value: str, base_url: str = "") -> str | None:
    """Allow public HTTPS university URLs, never credentials or foreign hosts."""
    try:
        value = urljoin(base_url, value.strip())
        url = urlsplit(value)
        host = (url.hostname or "").lower()
        if (
            url.scheme != "https"
            or url.username is not None
            or url.password is not None
            or url.port not in (None, 443)
            or not (host == "sfedu.ru" or host.endswith(".sfedu.ru") or host == "econ-sfedu.ru")
        ):
            return None
    except ValueError:
        return None
    return value


def _photo_url(raw: str, source_url: str) -> str | None:
    value = official_url(raw, source_url) if raw else None
    if value is None:
        return None
    name = PurePosixPath(urlsplit(value).path).name.lower()
    if any(marker in name for marker in ("logo", "no-photo", "nophoto", "placeholder", "no_avatar", "default-avatar")):
        return None
    return value


def _identity(full_name: str) -> tuple[str, ...] | None:
    parsed = parse_person(full_name)
    if parsed is None:
        return None
    surname, given, patronymic = parsed
    return person_key(surname, given, patronymic)[:1] + (
        given.casefold().replace("ё", "е"),
        patronymic.casefold().replace("ё", "е"),
    )


def parse_photo_page(page_html: str, source_url: str) -> list[PhotoCandidate]:
    """Extract a portrait only from a named staff card or named profile image.

    Faculty images are lazy-loaded on divs as well as img elements. Searching
    all page images by proximity would silently associate navigation logos or
    the previous person's portrait with a name, so card boundaries are explicit.
    """
    if official_url(source_url) is None:
        return []
    page = BeautifulSoup(page_html, "html.parser")
    candidates: list[PhotoCandidate] = []

    if "/s7/person/" in urlsplit(source_url).path:
        headings = page.select(".about_employee > h2") or page.select("h1, h2")
        owner = next((identity for heading in headings
                      if (identity := _identity(heading.get_text(" ", strip=True))) is not None), None)
        if owner is None:
            return []
        # A biography may contain photographs of colleagues. Only the owner
        # named by the profile heading can supply a portrait from this page.
        for image in page.select("img[alt]"):
            name = image.get("alt", "").strip()
            if _identity(name) != owner:
                continue
            url = _photo_url(image.get("data-src") or image.get("src", ""), source_url)
            if url and "display:none" not in image.get("style", "").replace(" ", "").lower():
                candidates.append(PhotoCandidate(name, url, source_url))
        return list(dict.fromkeys(candidates))

    def add(name: str, container) -> None:
        name = " ".join(name.split())
        if _identity(name) is None:
            return
        urls = []
        for image in container.select("img, .empl-face[data-src]"):
            if "display:none" in (image.get("style", "").replace(" ", "").lower()):
                continue
            url = _photo_url(image.get("data-src") or image.get("src", ""), source_url)
            if url and url not in urls:
                urls.append(url)
        if len(urls) == 1:
            candidates.append(PhotoCandidate(name, urls[0], source_url))

    for name in page.select(".name-wrap .name"):
        container = name.find_parent(class_="wr-inner")
        if container:
            add(name.get_text(" ", strip=True), container)
    for name in page.select(".empl-name"):
        container = name.find_parent(class_="elem-hover-height")
        if container:
            add(name.get_text(" ", strip=True), container)

    return list(dict.fromkeys(candidates))


def match_photos(people: Iterable[DirectoryIdentity], candidates: Iterable[PhotoCandidate],
                 *, reviewed_aliases: Mapping[str, str] | None = None,
                 reviewed_sources: Mapping[str, str] | None = None) -> PhotoMatches:
    """Only uniquely identified official full names can decorate existing rows."""
    by_key: dict[tuple[str, str, str], list[PhotoCandidate]] = defaultdict(list)
    for candidate in candidates:
        key = key_of_full(candidate.full_name)
        photo_url = _photo_url(candidate.photo_url, candidate.source_url)
        source_url = official_url(candidate.source_url)
        if key and photo_url and source_url:
            by_key[key].append(PhotoCandidate(candidate.full_name, photo_url, source_url))

    report = PhotoMatches()
    for person in people:
        options = by_key.get(person.key, [])
        expected = _identity(person.full_name)
        if expected is None:
            expected = _identity((reviewed_aliases or {}).get(person.id, ""))
            if reviewed_sources is not None:
                reviewed_source = official_url(reviewed_sources.get(person.id, ""))
                options = [candidate for candidate in options if candidate.source_url == reviewed_source]
        identities = {_identity(c.full_name) for c in options}
        if len(identities) > 1:
            report.ambiguous.append(person.id)
        elif options and expected is not None and expected in identities:
            report.matches[person.id] = options[0]
        else:
            report.missing.append(person.id)
    return report
