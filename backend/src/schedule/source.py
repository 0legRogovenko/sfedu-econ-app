"""Индексная страница расписания: разделы, (label, p_doc_id), URL для скачивания.

Страница отдаётся в cp1251. Список файлов лежит в скрытом <span id="Dcont_">,
откуда его на клиенте перекладывает JS в пустой #Dcont — парсить надо #Dcont_.

Разметка описана в разведке (docs/superpowers/research/2026-07-17-schedule-recon.md,
п.1.3), тесты — на сохранённой копии страницы (tests/fixtures/schedule/index.html).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from bs4 import BeautifulSoup, NavigableString, Tag

BASE_URL = "https://sfedu.ru"

# Экономфак = p_es_id 10000000000000, очная форма = p_tf_id 1.
# Очно-заочная и заочная у экономфака пустые — качать нечего.
INDEX_URL = (
    f"{BASE_URL}/www/stat_pages22.show"
    "?p=STD/rasp/D&params=(p_es_id=>10000000000000,p_tf_id=>1)"
)

_DOC_ID_RE = re.compile(r"p_doc_id=(\d+)")


@dataclass(frozen=True)
class ScheduleLink:
    """Файл расписания, как он подписан на индексной странице.

    `label` и `section` — это данные сайта, а не тип документа: «4 курс» в
    «Летней сессии» оказался расписанием экзаменов. Тип определяет classify
    по содержимому файла.
    """

    section: str
    label: str
    p_doc_id: str

    @property
    def download_url(self) -> str:
        return download_url(self.p_doc_id)


def download_url(p_doc_id: str | int) -> str:
    """URL файла через /www/.

    Ссылки на самой странице ведут в /pls/rsu/, который запрещён robots.txt.
    Тот же файл отдаётся по /www/ и robots-разрешён — ходить только сюда.
    """
    return f"{BASE_URL}/www/sched_files.f_download?p_doc_id={p_doc_id}"


def parse_index(html: str) -> list[ScheduleLink]:
    """Разбирает индексную страницу в список файлов.

    Разделов больше, чем кажется: кроме «Осеннего»/«Весеннего семестра» есть
    сессии. Заголовок раздела — голый текст в <div> без класса и без тега-
    заголовка, поэтому наивный парсер склеивал все ссылки в один раздел.
    """
    soup = BeautifulSoup(html, "html.parser")
    container = soup.find(id="Dcont_")
    if container is None:
        return []

    links: list[ScheduleLink] = []
    for div in container.find_all("div"):
        # Секция — самый внутренний div: снаружи есть обёртка со стилем,
        # которая содержит úже все формы разом.
        if div.find("div") is not None:
            continue
        section = _section_name(div)
        if not section:
            continue
        for anchor in div.find_all("a", href=_DOC_ID_RE):
            match = _DOC_ID_RE.search(anchor["href"])
            if match is None:  # pragma: no cover - фильтр find_all уже проверил
                continue
            links.append(
                ScheduleLink(
                    section=section,
                    label=_label_of(anchor),
                    p_doc_id=match.group(1),
                )
            )
    return links


def _section_name(div: Tag) -> str:
    """Имя раздела — первый непустой текстовый узел прямо в <div>, до <BR>."""
    for child in div.children:
        if isinstance(child, NavigableString):
            text = _clean(str(child))
            if text:
                return text
    return ""


def _label_of(anchor: Tag) -> str:
    """Подпись файла — текст рядом со ссылкой, без «скачать» и &nbsp;-отступов."""
    parent = anchor.parent
    if isinstance(parent, Tag):
        own_text = "".join(parent.find_all(string=True, recursive=False))
        label = _clean(own_text)
        if label:
            return label
    return ""


def _clean(text: str) -> str:
    return text.replace("\xa0", " ").strip()
