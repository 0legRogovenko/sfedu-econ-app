"""Парсер сотрудников econ-sfedu.ru: деканат и кафедры.

Сайт факультета на Joomla с конструктором SP Page Builder. Люди лежат в
карточках `sppb-carousel-extended-team-*`: имя ссылкой, должность/степень
отдельным блоком. Заведующий кафедрой стоит вне карусели — заголовок
«Заведующий кафедрой» и текстовый блок с ФИО и степенью.

Чистые функции разбора тестируются на сохранённых страницах
(backend/tests/fixtures/econ_staff/): сменится вёрстка — тест упадёт, а не
отдаст молча пустой справочник.
"""

from __future__ import annotations

import base64
import html
import re
from dataclasses import dataclass, field

BASE_URL = "https://econ-sfedu.ru"
DEANERY_URL = f"{BASE_URL}/pages/about-us.html"
DEPARTMENTS_URL = f"{BASE_URL}/pages/kafedry.html"


@dataclass(frozen=True)
class Person:
    name: str
    role: str
    phone: str | None = None
    profile_url: str | None = None


@dataclass
class Department:
    name: str = ""
    head: Person | None = None
    staff: list[Person] = field(default_factory=list)


def _text(fragment: str) -> str:
    """HTML-фрагмент → строка: теги прочь, сущности развернуть, пробелы сжать."""
    plain = re.sub(r"(?s)<[^>]+>", " ", fragment)
    plain = html.unescape(plain)
    # \xa0 (&nbsp;) в этой вёрстке встречается постоянно
    return re.sub(r"\s+", " ", plain.replace("\xa0", " ")).strip()


def _unescape_href(href: str) -> str:
    """Раскодирует ТОЛЬКО `&amp;`.

    Полный html.unescape ломает ссылки: в `?p=...&params=(...)` кусок `&para`
    разбирается как сущность ¶, и ссылка на личную страницу превращается в 404.
    """
    return href.replace("&amp;", "&")


def _looks_like_person(name: str) -> bool:
    """Отсеиваем подписи к фото и заголовки: ФИО — минимум два слова."""
    return len(name.split()) >= 2


# Карточка сотрудника целиком: от начала обёртки до конца её содержимого.
_CARD_RE = re.compile(
    r'<div class="sppb-carousel-extended-team-wrap">(.*?)'
    r'</ul>\s*</div>\s*</div>\s*</div>',
    re.S,
)
_NAME_RE = re.compile(
    r'<div class="sppb-carousel-extended-team-name">(.*?)</div>', re.S
)
_ROLE_RE = re.compile(
    r'<div class="sppb-carousel-extended-team-designation">(.*?)</div>', re.S
)
_HREF_RE = re.compile(r'href="([^"]+)"')
# `tel: +78632184000-13009` — с пробелом после схемы, добавочный через дефис.
_TEL_RE = re.compile(r'href="tel:\s*([^"]+)"')


def _parse_cards(page_html: str) -> list[Person]:
    people: list[Person] = []
    for card in _CARD_RE.findall(page_html):
        name_match = _NAME_RE.search(card)
        if not name_match:
            continue
        name = _text(name_match.group(1))
        if not _looks_like_person(name):
            continue
        role_match = _ROLE_RE.search(card)
        role = _text(role_match.group(1)) if role_match else ""

        tel_match = _TEL_RE.search(card)
        phone = tel_match.group(1).strip() if tel_match else None

        # Ссылка на личную страницу — первая не-tel ссылка карточки.
        profile = None
        for href in _HREF_RE.findall(card):
            if not href.startswith("tel:"):
                profile = _unescape_href(href)
                break

        people.append(
            Person(name=name, role=role, phone=phone, profile_url=profile)
        )
    return people


# ВТОРОЙ МАКЕТ. Часть кафедр свёрстана не каруселью, а блоками
# `sppb-addon-person`. Пока он не поддерживался, такая кафедра молча теряла
# и заведующего, и часть состава.
_PERSON_BLOCK_RE = re.compile(
    r'<div class="sppb-person-information">(.*?)</div>', re.S
)
_PERSON_NAME_RE = re.compile(
    r'<span class="sppb-person-name">(.*?)</span>', re.S
)
_PERSON_ROLE_RE = re.compile(
    r'<span class="sppb-person-designation">(.*?)</span>', re.S
)


def _parse_person_blocks(page_html: str) -> list[Person]:
    people: list[Person] = []
    for block in _PERSON_BLOCK_RE.findall(page_html):
        name_match = _PERSON_NAME_RE.search(block)
        if not name_match:
            continue
        name = _text(name_match.group(1))
        if not _looks_like_person(name):
            continue
        role_match = _PERSON_ROLE_RE.search(block)
        people.append(
            Person(name=name, role=_text(role_match.group(1)) if role_match else "")
        )
    return people


# «Заведующий кафедрой», «и.о. заведующего кафедрой», «заведующая кафедрой».
_HEAD_ROLE_RE = re.compile(r"заведующ\w*\s+кафедрой", re.I)


def _dedupe(people: list[Person]) -> list[Person]:
    """Один человек = одна запись: карусель дублирует карточки для прокрутки."""
    seen: set[str] = set()
    result: list[Person] = []
    for person in people:
        if person.name in seen:
            continue
        seen.add(person.name)
        result.append(person)
    return result


def parse_deanery(page_html: str) -> list[Person]:
    """Сотрудники деканата со страницы «О факультете»."""
    return _dedupe(_parse_cards(page_html))


_TITLE_RE = re.compile(r'<h1[^>]*itemprop="headline"[^>]*>(.*?)</h1>', re.S)
# Блок заведующего: заголовок-маркер, затем ближайший текстовый блок с ФИО.
_HEAD_MARKER_RE = re.compile(
    r'<h4 class="sppb-addon-title">\s*Заведующ\w*\s+кафедрой\s*</h4>', re.S
)
# Тег <a> берём целиком, href достаём отдельно: необязательная группа внутри
# лениво-жадного [^>]*? проскакивает мимо. У части кафедр заведующий подписан
# без ссылки, но если она есть — её нужно сохранить, иначе почту заведующего
# неоткуда взять.
_HEAD_PERSON_RE = re.compile(
    r"(?P<anchor><a[^>]*>)(?P<name>[^<]+)</a>"
    r"\s*<br\s*/?>(?P<degree>.*?)(?:</span>|</strong>|<br)",
    re.S,
)


def _parse_head(page_html: str) -> Person | None:
    marker = _HEAD_MARKER_RE.search(page_html)
    if not marker:
        return None
    # Ищем ФИО после маркера, но недалеко: дальше начинается «О кафедре».
    window = page_html[marker.end() : marker.end() + 4000]
    person = _HEAD_PERSON_RE.search(window)
    if not person:
        return None
    name = _text(person.group("name"))
    if not _looks_like_person(name):
        return None
    degree = _text(person.group("degree")).strip(" ,")
    role = "Заведующий кафедрой"
    if degree:
        role = f"{role}, {degree}"
    href_match = _HREF_RE.search(person.group("anchor"))
    return Person(
        name=name,
        role=role,
        profile_url=_unescape_href(href_match.group(1)) if href_match else None,
    )


def parse_department(page_html: str) -> Department:
    """Страница одной кафедры: название, заведующий, сотрудники."""
    title_match = _TITLE_RE.search(page_html)
    name = _text(title_match.group(1)) if title_match else ""

    # Люди приходят из трёх мест: карусель, блоки person и текстовый блок
    # заведующего. Собираем всех, затем классифицируем по должности — так
    # добавление ещё одного макета не требует новой ветки «а где заведующий».
    everyone = _dedupe(_parse_cards(page_html) + _parse_person_blocks(page_html))

    head = next(
        (p for p in everyone if _HEAD_ROLE_RE.search(p.role)),
        None,
    )
    if head is None:
        # Классический макет: заведующий вне карточек, под заголовком-маркером.
        head = _parse_head(page_html)

    staff = [p for p in everyone if head is None or p.name != head.name]
    return Department(name=name, head=head, staff=staff)


# Почта на sfedu.ru отдана приманкой `hello+<base64>@sfedu-university.com`;
# настоящий адрес страница показывает, декодируя base64 в браузере. Приманка
# нерабочая, поэтому сохранять её нельзя — кнопка письма вела бы в никуда.
_DECOY_MAILTO_RE = re.compile(r"mailto:hello\+([A-Za-z0-9+/=]+)@")
_PLAIN_MAILTO_RE = re.compile(r"mailto:([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})")


def parse_person_email(page_html: str) -> str | None:
    """Почта с личной страницы сотрудника sfedu.ru."""
    decoy = _DECOY_MAILTO_RE.search(page_html)
    if decoy:
        try:
            decoded = base64.b64decode(decoy.group(1), validate=True).decode()
        except (ValueError, UnicodeDecodeError):
            return None
        return decoded if _PLAIN_MAILTO_RE.fullmatch("mailto:" + decoded) else None

    plain = _PLAIN_MAILTO_RE.search(page_html)
    return plain.group(1) if plain else None


_DEPT_LINK_RE = re.compile(
    r'href="(/(?:index\.php\?option=com_content[^"]*catid=16[^"]*'
    r'|component/content/article/[^"]*catid=16[^"]*))"'
)


def parse_department_links(page_html: str) -> list[str]:
    """Ссылки на страницы кафедр со страницы-каталога «Кафедры».

    Один и тот же материал Joomla отдаёт по двум путям (`index.php?...` и
    `/component/content/article/...`), поэтому дедуп идёт по id материала.
    """
    seen_ids: set[str] = set()
    links: list[str] = []
    for href in _DEPT_LINK_RE.findall(page_html):
        href = _unescape_href(href)
        id_match = re.search(r"(?:id=|/)(\d+)[:\-]", href)
        article_id = id_match.group(1) if id_match else href
        if article_id in seen_ids:
            continue
        seen_ids.add(article_id)
        links.append(f"{BASE_URL}{href}")
    return links
