"""Сотрудники экономического факультета из официального реестра ЮФУ.

Основной сайт факультета иногда падает ещё до Joomla с PHP Fatal error.
Университетский реестр остаётся доступен и содержит ФИО, должность, ссылку на
профиль и логин. Корпоративная почта строится только из опубликованного логина:
никакого угадывания адресов по фамилии.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass

STAFF_URL = (
    "https://sfedu.ru/www/stat_pages22.show?p=ELs%2Fsotr%2FD&x=ELS%2F10000000000000"
)


@dataclass(frozen=True)
class StaffPerson:
    name: str
    role: str
    email: str | None
    profile_url: str | None


_ROW_RE = re.compile(r"<tr\b[^>]*>(.*?)</tr>", re.I | re.S)
_CELL_RE = re.compile(r"<td\b(?P<attrs>[^>]*)>(?P<body>.*?)</td>", re.I | re.S)
_HREF_RE = re.compile(r'href=["\']([^"\']+)["\']', re.I)
_TAG_RE = re.compile(r"<[^>]+>", re.S)
_LOGIN_RE = re.compile(r"[A-Za-z0-9._-]+")


def _text(fragment: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(_TAG_RE.sub(" ", fragment))).strip()


def _profile_url(body: str) -> str | None:
    match = _HREF_RE.search(body)
    if not match:
        return None
    href = html.unescape(match.group(1)).strip()
    if href.startswith("//"):
        return "https:" + href
    if href.startswith("/"):
        return "https://sfedu.ru" + href
    return href if href.startswith("https://sfedu.ru/") else None


def parse_staff_page(page_html: str) -> list[StaffPerson]:
    """Разбирает строки таблицы; телефон намеренно не входит в модель."""
    people: list[StaffPerson] = []
    seen: set[str] = set()

    for row_html in _ROW_RE.findall(page_html):
        cells = list(_CELL_RE.finditer(row_html))
        if len(cells) < 4 or "login" not in cells[-1].group("attrs").lower():
            continue

        name = _text(cells[0].group("body"))
        role = _text(cells[1].group("body"))
        login = _text(cells[-1].group("body"))
        if len(name.split()) < 3 or name in seen:
            continue
        seen.add(name)

        email = f"{login}@sfedu.ru" if _LOGIN_RE.fullmatch(login) else None
        people.append(
            StaffPerson(
                name=name,
                role=role,
                email=email,
                profile_url=_profile_url(cells[0].group("body")),
            )
        )

    return people
