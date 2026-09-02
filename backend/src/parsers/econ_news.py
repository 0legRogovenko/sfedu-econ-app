"""Новости экономического факультета из официального sitemap Joomla.

Главная ``econ-sfedu.ru`` периодически падает ещё до Joomla (PHP fatal в
``index.php``), тогда как статический ``sitemap.xml`` остаётся доступен. Поэтому
ссылки обнаруживаем по sitemap, а полное содержимое уточняем со страницы
материала. Если одна статья временно недоступна, в ленту всё равно попадает
официальная ссылка с читаемым заголовком из slug и датой изменения sitemap.
"""

from __future__ import annotations

import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import parse_qs, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from src.parsers import sfedu_news

BASE_URL = "https://econ-sfedu.ru"
SITEMAP_URL = f"{BASE_URL}/sitemap.xml"
MAX_ARTICLES = 12
FETCH_ATTEMPTS = 3

_ARTICLE = re.compile(r"/component/content/article/(\d+)-([^/?#]+)\.html$")
_TRANSLIT = (
    ("shch", "щ"),
    ("yo", "ё"),
    ("jo", "ё"),
    ("zh", "ж"),
    ("kh", "х"),
    ("ts", "ц"),
    ("ch", "ч"),
    ("sh", "ш"),
    ("yu", "ю"),
    ("ya", "я"),
)
_ENGLISH_MARKERS = frozenset(
    {"the", "of", "will", "host", "another", "meeting", "technologies", "for", "life"}
)
_SPELLING = {
    "специалному": "специальному",
    "федералные": "федеральные",
    "социалные": "социальные",
    "лготы": "льготы",
    "освоит": "освоить",
    "факултета": "факультета",
    "глобалного": "глобального",
    "ден": "день",
    "преподавател": "преподаватель",
    "победител": "победитель",
    "обладател": "обладатель",
}
_UPPER_WORDS = {
    "эконома": "Эконома",
    "юфу": "ЮФУ",
    "пмеф": "ПМЭФ",
    "бпла": "БПЛА",
}
_SINGLE_TRANSLIT = str.maketrans(
    {
        "a": "а",
        "b": "б",
        "v": "в",
        "g": "г",
        "d": "д",
        "e": "е",
        "z": "з",
        "i": "и",
        "j": "й",
        "k": "к",
        "l": "л",
        "m": "м",
        "n": "н",
        "o": "о",
        "p": "п",
        "r": "р",
        "s": "с",
        "t": "т",
        "u": "у",
        "f": "ф",
        "h": "х",
        "y": "ы",
        "c": "к",
        "q": "к",
        "w": "в",
        "x": "кс",
    }
)


@dataclass(frozen=True)
class NewsCandidate:
    url: str
    article_id: int
    title: str
    published_at: datetime


@dataclass(frozen=True)
class ParsedArticle:
    title: str
    body: str
    published_at: datetime
    image_url: str | None


def _slug_title(slug: str) -> str:
    words = slug.lower().split("-")
    if len(_ENGLISH_MARKERS.intersection(words)) >= 2:
        return " ".join(words).capitalize()

    text = " ".join(words)
    for latin, cyrillic in _TRANSLIT:
        text = text.replace(latin, cyrillic)
    text = text.translate(_SINGLE_TRANSLIT)
    # В Joomla-slug факультет пишет «ekonom», где начальная e означает «э».
    text = re.sub(r"\bеконом", "эконом", text)
    words = re.sub(r"\s+", " ", text).strip().split()
    words = [_SPELLING.get(word, _UPPER_WORDS.get(word, word)) for word in words]
    text = " ".join(words)
    text = re.sub(r"\bЭконома ЮФУ участники\b", "Эконома ЮФУ — участники", text)
    return text[:1].upper() + text[1:]


def _utc_naive(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def parse_sitemap(xml: str, limit: int = MAX_ARTICLES) -> list[NewsCandidate]:
    """Берёт только категорию Joomla 15 — основную ленту новостей."""
    root = ET.fromstring(xml)
    candidates: list[NewsCandidate] = []
    for item in root.findall("{*}url"):
        loc = item.findtext("{*}loc") or ""
        parsed_url = urlparse(loc)
        match = _ARTICLE.match(parsed_url.path)
        category = parse_qs(parsed_url.query).get("catid", [""])[0]
        if match is None or category.split(":", 1)[0] != "15":
            continue
        lastmod = item.findtext("{*}lastmod")
        if not lastmod:
            continue
        article_id, slug = match.groups()
        candidates.append(
            NewsCandidate(
                url=loc,
                article_id=int(article_id),
                title=_slug_title(slug),
                published_at=_utc_naive(lastmod),
            )
        )
    candidates.sort(key=lambda candidate: candidate.article_id, reverse=True)
    return candidates[:limit]


def parse_article(html: str, candidate: NewsCandidate) -> ParsedArticle | None:
    """Разбирает Joomla-материал; None означает серверную заглушку/фатал."""
    if "Fatal error" in html or "Undefined constant" in html:
        return None
    soup = BeautifulSoup(html, "html.parser")
    title_el = soup.select_one('[itemprop="headline"]') or soup.find("h1")
    body_el = soup.select_one('[itemprop="articleBody"]')
    if title_el is None or body_el is None:
        return None

    title = re.sub(r"\s+", " ", title_el.get_text(" ", strip=True)).strip()
    paragraphs = [
        re.sub(r"\s+", " ", paragraph.get_text(" ", strip=True)).strip()
        for paragraph in body_el.find_all("p")
    ]
    body = "\n\n".join(part for part in paragraphs if part)
    if not title or not body:
        return None

    published_at = candidate.published_at
    time_el = soup.find("time")
    if time_el is not None:
        raw = time_el.get("datetime")
        try:
            published_at = (
                _utc_naive(raw)
                if raw
                else sfedu_news.parse_ru_date(time_el.get_text(" ", strip=True))
            )
        except ValueError:
            pass

    image_el = body_el.find("img", src=True) or soup.select_one(
        'img[itemprop="image"][src]'
    )
    image_url = urljoin(BASE_URL, image_el["src"]) if image_el else None
    return ParsedArticle(
        title=title[:500],
        body=body,
        published_at=published_at,
        image_url=image_url,
    )


def default_fetch(url: str) -> str:
    """econ-sfedu.ru не задаёт Crawl-delay; запросы всё равно последовательны."""
    session = sfedu_news._make_session()
    for attempt in range(FETCH_ATTEMPTS):
        try:
            response = session.get(url, timeout=15)
            response.raise_for_status()
            return response.text
        except requests.RequestException:
            if attempt == FETCH_ATTEMPTS - 1:
                raise
            time.sleep(0.5 * (2**attempt))
    raise AssertionError("unreachable")
