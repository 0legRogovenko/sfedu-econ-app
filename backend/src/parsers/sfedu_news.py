"""Парсер новостей sfedu.ru.

Чистые функции разбора HTML (тестируются на сохранённых фикстурах реальных
страниц — backend/tests/fixtures/) + фетч по сети. Разметка сайта описана
в плане docs/superpowers/plans/2026-07-13-news-feature.md.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://sfedu.ru"
LISTING_URL = f"{BASE_URL}/press-center/mainpage"

_MONTHS = {
    "января": 1,
    "февраля": 2,
    "марта": 3,
    "апреля": 4,
    "мая": 5,
    "июня": 6,
    "июля": 7,
    "августа": 8,
    "сентября": 9,
    "октября": 10,
    "ноября": 11,
    "декабря": 12,
}

_DATE_RE = re.compile(r"(\d{1,2})\s+([а-яё]+)\s+(\d{4})", re.IGNORECASE)


@dataclass
class NewsCandidate:
    url: str
    title: str
    published_at: datetime
    snippet: str | None
    image_url: str | None


def parse_ru_date(text: str) -> datetime:
    """«15 июня 2026 г.» -> datetime(2026, 6, 15). ValueError на мусоре."""
    match = _DATE_RE.search(text.strip().lower())
    if not match:
        raise ValueError(f"Не удалось распознать дату: {text!r}")
    day, month_name, year = match.groups()
    month = _MONTHS.get(month_name)
    if month is None:
        raise ValueError(f"Неизвестный месяц: {month_name!r}")
    return datetime(int(year), month, int(day))


def parse_listing(html: str) -> list[NewsCandidate]:
    """Разбирает страницу-листинг в список кандидатов.

    Каждый div.new внутри .news_list с датой и ссылкой на статью.
    """
    soup = BeautifulSoup(html, "html.parser")
    candidates: list[NewsCandidate] = []
    seen_urls: set[str] = set()

    for block in soup.select("div.new"):
        link = block.find("a", href=True)
        if link is None:
            continue
        href = link["href"]
        if "/press-center/news/" not in href:
            continue
        url = urljoin(BASE_URL, href)
        if url in seen_urls:
            continue

        date_el = block.find(class_="date")
        if date_el is None:
            continue
        try:
            published_at = parse_ru_date(date_el.get_text())
        except ValueError:
            continue

        name_el = block.find(class_="name")
        title = (name_el.get_text() if name_el else link.get_text()).strip()
        if not title:
            continue

        snippet_el = block.find(class_="prev_text")
        snippet = snippet_el.get_text().strip() if snippet_el else None

        img_el = block.find("img", src=True)
        image_url = urljoin(BASE_URL, img_el["src"]) if img_el else None

        seen_urls.add(url)
        candidates.append(
            NewsCandidate(
                url=url,
                title=title,
                published_at=published_at,
                snippet=snippet or None,
                image_url=image_url,
            )
        )

    return candidates


def parse_article(html: str) -> str:
    """Чистый текст статьи: short_description + абзацы через \\n\\n.

    Инлайн-стили и теги отбрасываются. Пустой .content -> "".
    """
    soup = BeautifulSoup(html, "html.parser")
    content = soup.find(class_="content")
    if content is None:
        return ""

    parts: list[str] = []

    short = content.find(class_="short_description")
    if short is not None:
        text = short.get_text(" ", strip=True)
        if text:
            parts.append(text)

    for paragraph in content.find_all("p"):
        text = paragraph.get_text(" ", strip=True)
        if text:
            parts.append(text)

    # схлопываем множественные пробелы внутри абзацев
    parts = [re.sub(r"\s+", " ", p).strip() for p in parts]
    return "\n\n".join(p for p in parts if p)


def _default_fetch(url: str) -> str:
    response = requests.get(
        url,
        timeout=15,
        headers={"User-Agent": "sfedu-econ-app/1.0 (news aggregator)"},
    )
    response.raise_for_status()
    return response.text
