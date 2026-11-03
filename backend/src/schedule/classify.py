"""Определение типа документа расписания ПО СОДЕРЖИМОМУ.

Ни подпись на сайте, ни раздел типом не являются: 13984 подписан «4 курс» в
разделе «Летняя сессия», а внутри — расписание экзаменационной сессии. Поверить
подписи — значит уложить экзамены в Lesson.

Признаки и порядок их проверки взяты из разведки по 29 реальным файлам
(docs/superpowers/research/2026-07-17-schedule-recon.md).
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
import zipfile
from enum import Enum
from pathlib import Path

import pdfplumber

_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


class DocType(str, Enum):
    SEMESTER_GRID_BACHELOR = "semester_grid_bachelor"
    SEMESTER_GRID_MASTER = "semester_grid_master"
    EXAM_SESSION = "exam_session"
    POSTGRAD = "postgrad"
    CURRICULUM = "curriculum"
    UNKNOWN = "unknown"


# Пробелы всюду \s*, а не \s+: в 13984.docx шапка склеена в «Датаэкзамена»
# (текст разбит на runs), а в PDF слова колонок расходятся по разным строкам.
_EXAM = re.compile(r"экзаменационн\w*\s*сесси|дата\s*экзамена", re.IGNORECASE)
_POSTGRAD = re.compile(r"научная\s*специальность", re.IGNORECASE)
_GROUP = re.compile(r"группа\s*\d+\.\d+", re.IGNORECASE)
_MASTER = re.compile(r"магистерск\w*\s*программ", re.IGNORECASE)
_CURRICULUM = re.compile(r"перечень\s*предметов", re.IGNORECASE)


def classify_text(text: str) -> DocType:
    """Тип документа по его тексту.

    Порядок проверок — это и есть правило разрешения конфликтов, признаки
    пересекаются:
      * 14092 — сессия магистров: в ней есть «Магистерская программа», поэтому
        сессия проверяется раньше сеток;
      * у 13820/13830 первые страницы — учебный план, а сетка идёт дальше,
        поэтому «ПЕРЕЧЕНЬ ПРЕДМЕТОВ» — последний признак, а не первый.
    """
    flat = re.sub(r"\s+", " ", text)
    if _EXAM.search(flat):
        return DocType.EXAM_SESSION
    if _POSTGRAD.search(flat):
        return DocType.POSTGRAD
    if _GROUP.search(flat):
        return DocType.SEMESTER_GRID_BACHELOR
    if _MASTER.search(flat):
        return DocType.SEMESTER_GRID_MASTER
    if _CURRICULUM.search(flat):
        return DocType.CURRICULUM
    return DocType.UNKNOWN


def classify(path: str | Path) -> DocType:
    """Тип документа по файлу (.docx или .pdf)."""
    return classify_text(document_text(path))


def document_text(path: str | Path) -> str:
    """Весь текст документа — для классификации, не для разбора сетки.

    Читаем целиком: у весенних файлов признак сетки появляется только на 5-й
    странице, за учебным планом. Порванный текст (повёрнутые дни, ячейки в одну
    строку) классификатору не мешает — ему нужны только ключевые фразы.
    """
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".docx":
        return _docx_text(path)
    if suffix == ".pdf":
        return _pdf_text(path)
    raise ValueError(f"неподдерживаемый формат: {path.name}")


def _docx_text(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        root = ET.fromstring(archive.read("word/document.xml"))
    paragraphs = (
        "".join(node.text or "" for node in para.iter(_W + "t"))
        for para in root.iter(_W + "p")
    )
    return "\n".join(paragraphs)


def _pdf_text(path: Path) -> str:
    with pdfplumber.open(path) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)
