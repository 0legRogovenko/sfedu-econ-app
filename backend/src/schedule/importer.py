"""Слой 5: оркестрация импорта. fetch → classify → extract → structure/cells/exams → load.

Модуль ничего не парсит сам — он раскладывает результаты нижних слоёв по БД и
следит за тем, чтобы ни одна ячейка не пропала молча.

Четыре правила, которые здесь важнее кода:

1. **Ledger.** Каждая ячейка каждого разобранного документа попадает ровно в
   одну категорию (пара / экзамен / очередь админа / пустая / заглушка /
   структура). `accounted == total` — это и есть «ничего не потеряно»; тест
   на него главный в плане. Категория «структура» существует не для красоты:
   шапки, дни, время и календарь недель — тоже ячейки, и без отдельной корзины
   инвариант был бы просто неверен.
2. **sha256 — единственный сигнал обновления** (Last-Modified/ETag у файлов
   нет). Изменился → переразбор с ImportDiff «было/стало», а не молчаливая
   перезапись.
3. **Файл исчез со страницы — данные не удаляем.** Сигнал админу; студент не
   должен остаться без расписания из-за того, что ЮФУ переставил ссылку.
4. **Аспирантура не извлекается вообще** (решение №8 плана): 6 файлов, в
   которых нет ни групп, ни сетки. Их ячейки не считаются — их никто не читал.
"""

from __future__ import annotations

import hashlib
import io
import json
import logging
import re
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from datetime import date, datetime, time

import pdfplumber
from sqlalchemy import delete, select

from src.alerts import notify_admin
from src.database import SessionLocal
from src.models import (
    DocType,
    EducationLevel,
    ExamEvent,
    Group,
    ImportDiff,
    Lesson,
    Module,
    ScheduleDocument,
    Teacher,
    UnparsedCell,
    WeekCalendar,
)
from src.schedule import classify as classify_module
from src.schedule import exams as exams_module
from src.schedule.cells import REASON_NO_BOUNDARY, is_placeholder, parse_cell
from src.schedule.date_constraints import resolve_date_constraint
from src.schedule.extract_docx import extract_docx
from src.schedule.extract_pdf import extract_pdf
from src.schedule.fetch import Fetcher
from src.schedule.grid import Grid
from src.schedule.programs import canonical_program
from src.schedule.reviewed_schedule import (
    ReviewBundle,
    ReviewValidationError,
    lesson_state,
    state_signature,
)
from src.schedule.source import parse_index
from src.schedule.structure import (
    PAIR_HALVES,
    GridHeader,
    parse_header,
    parse_rows,
    place_row,
    week_type_from_heading,
)
from src.schedule.weeks import is_week_calendar, parse_week_calendar

logger = logging.getLogger(__name__)

STATUS_IMPORTED = "imported"
STATUS_UNCHANGED = "unchanged"
STATUS_REIMPORTED = "reimported"
STATUS_SKIPPED = "skipped"
STATUS_FAILED = "failed"

CELL_EMPTY = "empty"
CELL_PLACEHOLDER = "placeholder"
CELL_LESSON = "lesson"
CELL_EXAM = "exam"
CELL_UNPARSED = "unparsed"
CELL_STRUCTURAL = "structural"
CELL_SKIPPED = "skipped"

REASON_UNKNOWN_TABLE = "таблица неизвестной схемы"
REASON_NO_GROUP_COLUMN = "ячейка не попала ни в одну колонку группы"
REASON_SLOT_TAKEN = "слот уже занят другой парой этого документа"
REASON_DATE_CONSTRAINT = "датовое ограничение не пересекается с периодом расписания"
REASON_EXAM_ROW = "строка сессии вне разбора"
REASON_NO_WEEKDAY = "занятие без дня недели"
REASON_NO_PAIR = "занятие без времени пары"

# Тип классификатора → тип в модели. Два разных enum'а — исторически: слой
# classify не знает про БД, и это правильно, но маппинг обязан быть явным.
_DOC_TYPE = {
    classify_module.DocType.SEMESTER_GRID_BACHELOR: DocType.SEMESTER_GRID_BACHELOR,
    classify_module.DocType.SEMESTER_GRID_MASTER: DocType.SEMESTER_GRID_MASTER,
    classify_module.DocType.EXAM_SESSION: DocType.EXAM_SESSION,
    classify_module.DocType.POSTGRAD: DocType.POSTGRAD_DATES,
    classify_module.DocType.CURRICULUM: DocType.CURRICULUM_PAGE,
    classify_module.DocType.UNKNOWN: DocType.UNKNOWN,
}

_GRID_TYPES = (DocType.SEMESTER_GRID_BACHELOR, DocType.SEMESTER_GRID_MASTER)

_MONTHS = {
    "января": 1, "февраля": 2, "марта": 3, "апреля": 4, "мая": 5, "июня": 6,
    "июля": 7, "августа": 8, "сентября": 9, "октября": 10, "ноября": 11,
    "декабря": 12,
}
# 'I модуль (1 сентября – 2 ноября)', '2 модуль: 3 ноября – 11 января'.
# Имя модуля ключом НЕ является («2 модуль» встречается дважды с разными
# датами в одном файле) — ключ это диапазон дат, имя только для админа.
_MODULE = re.compile(
    r"([IVX]+|\d)\s*модул\w*\s*[:(]?\s*"
    r"(\d\d?)\s+([а-я]+)\s*[–—-]\s*(\d\d?)\s+([а-я]+)",
    re.IGNORECASE,
)
# Имя модуля без дат: 13822 p10 — заголовок 'II модуль', а даты уехали в шапку
# колонок ('13 апреля-22 июня'), причём у каждой группы свои. Без фолбэка на
# них страница унаследовала бы модуль I и вся ушла бы в очередь как «слот занят».
_MODULE_NAME = re.compile(r"([IVX]+|\d)\s*модул\w*", re.IGNORECASE)
_DATE_RANGE = re.compile(
    r"(\d\d?)\s+([а-я]+)\s*[–—-]\s*(\d\d?)\s+([а-я]+)", re.IGNORECASE
)
# 'I семестр (1 сентября – 15 января)' — подпись СЕМЕСТРА, не модуля (13471 T7,
# 13472 p10). Фолбэк ниже берёт любой диапазон дат, и без этого исключения
# семестр становился безымянным модулем во весь свой срок: модули начинали
# перекрываться, а союз диапазонов растягивал их за срок группы.
# Диапазон должен идти вплотную за словом («семестр (даты)»).
_SEMESTER_RANGE = re.compile(
    r"семестр\w*\s*\(?\s*(?=\d\d?\s+[а-я]+\s*[–—-])", re.IGNORECASE
)
_CURRICULUM_TABLE = re.compile(
    r"перечень\s+предметов|наименование\s+курса", re.IGNORECASE
)
_MASTER_COURSE = re.compile(r"(\d)\s*курс")
_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _cell_key(grid_index: int, cell) -> str:
    """Координата ячейки в документе: "таблица:строка:колонка".

    Ровно тот же ключ, что у Ledger._marks, только строкой — он уходит в
    Lesson.cell_key/UnparsedCell.cell_key и связывает строку БД с породившей
    её ячейкой. Уникален в пределах документа: две ячейки с ОДИНАКОВЫМ текстом
    (близнецы, их в корпусе десятки на файл) различаются только позицией.
    """
    return f"{grid_index}:{cell.row}:{cell.col_start}"


@dataclass
class Ledger:
    """Судьба каждой ячейки документа. Ключ — (номер таблицы, строка, колонка).

    Знаменатель приходит ИЗВНЕ, через account(): это число ячеек, которые отдал
    слой extract. Выводить его из mark() (`total = len(_seen)`) нельзя — тогда
    обе части равенства растут ровно в mark(), по единице в каждую сторону,
    `accounted == total` истинно всегда, а ячейка, до mark() не дошедшая,
    отсутствует в обеих частях и пропадает бесследно. Именно так 847 ячеек
    корпуса уходили в никуда при зелёном тесте.

    Но и одного mark() мало. Метка `mark(cell, PLACEHOLDER)` НАЗНАЧАЕТ категорию —
    она не ДОКАЗЫВАЕТ, что ячейка ей соответствует. Пометь настоящую пару как
    заглушку и не создай её — `accounted == total` всё равно сойдётся, а пара
    исчезнет молча (ровно эта атака и прошла 413/413 зелёными). Поэтому accounted
    считает не помеченные ячейки, а ДОКАЗАННЫЕ: у каждой категории есть предикат,
    который обязан выполниться для ячейки в ней, и prove() сверяет его с
    содержимым ячейки, со строками в БД и с позицией. Непустая ячейка, чью
    категорию доказать не удалось, из accounted выпадает — и инвариант краснеет.

    Предикаты доказываются ПРОИСХОЖДЕНИЕМ, а не множествами текстов. Множество
    «в документе есть строка с таким текстом» четырежды пропускало потерю:
    ячейки-близнецы с одинаковым текстом делили одно доказательство, ячейка на
    две пары доказывалась одной выжившей, мусорная строка с cell_raw == text
    проходила предикат. Поэтому у каждой строки БД есть cell_key — координата
    породившей её ячейки, — а prove() НЕЗАВИСИМО перепарсивает текст ячейки и
    сверяет строки именно ЭТОЙ ячейки с тем, что парсер обязан был из неё дать.

    Предикаты:
      empty       — текст ячейки пуст после strip();
      placeholder — cells.is_placeholder(text) («…….» = «занятий нет»);
      lesson      — перепарс parse_cell(text) даёт пары, и строки Lesson с
                    cell_key ЭТОЙ ячейки совпадают с ними по числу и по
                    сигнатуре (предмет/вид/даты/аудитория/подгруппа); пары,
                    отвергнутые уникальностью слота, обязаны лежать в
                    UnparsedCell с тем же cell_key (см. _lesson_proven);
      unparsed    — в БД есть UnparsedCell с cell_key ЭТОЙ ячейки и её текстом;
      structural  — ячейка помечена структурной ПО ПОЗИЦИИ (шапка / колонки
                    дня-времени / календарь недель), а не голым ярлыком;
      exam        — ячейка в строке-нагрузке сессии (позиция, из row_kinds);
      skipped     — ячейка распознанной пропускаемой таблицы (учебный план).
    Позиционные категории (structural/exam/skipped) доказуемы только через
    mark_structural/mark_exam/mark_skipped: они кладут ключ в _positional из
    доверенного места (геометрия шапки, row_kinds, распознанный учебный план).
    Голый mark(cell, CELL_STRUCTURAL) в _positional не попадёт — и для непустой
    ячейки останется недоказанным.
    """

    counts: Counter = field(default_factory=Counter)
    # key -> (категория, ячейка): храним саму ячейку, чтобы prove() мог свериться
    # с её текстом, а не верить ярлыку на слово.
    _marks: dict[tuple, tuple[str, object]] = field(default_factory=dict)
    # ключи, чья структурность/пропуск/сессия доказаны ПОЗИЦИЕЙ из доверенного
    # места, а не одним лишь вызовом mark().
    _positional: set[tuple] = field(default_factory=set)
    # Контекст для ячеек-продолжений МУАМ: во второй строке PDF заголовок
    # «МУАМ» не повторён, поэтому независимый prove() должен знать канонические
    # предметы, доказанные предыдущей парой той же группы.
    _muam_subjects: dict[tuple, tuple[str, ...]] = field(default_factory=dict)
    _total: int = 0
    _proven: int | None = None

    def account(self, grids) -> None:
        """Принять к учёту ячейки, отданные extract'ом. Знаменатель инварианта."""
        self._total += sum(len(grid.cells) for grid in grids)

    def mark(self, grid_index: int, cell, category: str) -> None:
        """Назначить категорию, доказуемую содержимым/БД: empty, placeholder,
        lesson, unparsed. Структуру/сессию/пропуск через mark() назначать нельзя —
        их доказывает позиция (см. mark_structural/mark_exam/mark_skipped)."""
        self._record(grid_index, cell, category, positional=False)

    def mark_structural(self, grid_index: int, cell) -> None:
        """Ячейка структурна ПО ПОЗИЦИИ: строка шапки, колонка дня/времени или
        календарь недель. Кладём ключ в _positional — это и есть доказательство."""
        self._record(grid_index, cell, CELL_STRUCTURAL, positional=True)

    def mark_exam(self, grid_index: int, cell) -> None:
        """Ячейка в строке-нагрузке сессии (kind == 'payload' из row_kinds)."""
        self._record(grid_index, cell, CELL_EXAM, positional=True)

    def mark_skipped(self, grid_index: int, cell) -> None:
        """Ячейка распознанной пропускаемой таблицы (учебный план)."""
        self._record(grid_index, cell, CELL_SKIPPED, positional=True)

    def mark_muam_lesson(
        self,
        grid_index: int,
        cell,
        subjects: tuple[str, ...],
    ) -> None:
        """Пара из строки-продолжения МУАМ без повторного заголовка."""
        key = (grid_index, cell.row, cell.col_start)
        self._record(grid_index, cell, CELL_LESSON, positional=False)
        self._muam_subjects[key] = subjects

    def _record(self, grid_index: int, cell, category: str, *, positional: bool) -> None:
        key = (grid_index, cell.row, cell.col_start)
        if key in self._marks:
            return  # ячейка может лечь сразу в несколько групп — считаем один раз
        self._marks[key] = (category, cell)
        self.counts[category] += 1
        if positional:
            self._positional.add(key)

    def prove(self, session, document) -> None:
        """Пересчитать accounted как число ДОКАЗАННЫХ ячеек.

        Знаменатель (total) не трогаем — он от extract. Здесь мы проверяем, что
        каждая помеченная ячейка действительно соответствует своей категории.
        Строки БД группируются по cell_key — координате породившей ячейки:
        каждая ячейка доказывается СВОИМИ строками, а не чьими-то похожими.
        Что не доказано — в accounted не попадает.
        """
        lessons_by_key: dict[str | None, list] = {}
        for row in session.scalars(
            select(Lesson).where(Lesson.document_id == document.id)
        ):
            lessons_by_key.setdefault(row.cell_key, []).append(row)
        unparsed_by_key: dict[str | None, list] = {}
        for row in session.scalars(
            select(UnparsedCell).where(UnparsedCell.document_id == document.id)
        ):
            unparsed_by_key.setdefault(row.cell_key, []).append(row)
        self._proven = sum(
            1
            for key, (category, cell) in self._marks.items()
            if self._is_proven(key, category, cell, lessons_by_key, unparsed_by_key)
        )

    def _is_proven(self, key, category, cell, lessons_by_key, unparsed_by_key) -> bool:
        text = cell.text
        if category == CELL_EMPTY:
            return not text.strip()
        if category == CELL_PLACEHOLDER:
            return is_placeholder(text)
        key_str = _cell_key(key[0], cell)
        if category == CELL_LESSON:
            return _lesson_proven(
                cell,
                lessons_by_key.get(key_str, []),
                unparsed_by_key.get(key_str, []),
                muam_subjects=self._muam_subjects.get(key),
            )
        if category == CELL_UNPARSED:
            return any(
                row.raw_text == text for row in unparsed_by_key.get(key_str, [])
            )
        if category in (CELL_STRUCTURAL, CELL_EXAM, CELL_SKIPPED):
            return key in self._positional
        return False

    @property
    def total(self) -> int:
        """Сколько ячеек в документе (по данным extract), а не сколько помечено."""
        return self._total

    @property
    def accounted(self) -> int:
        """Число ДОКАЗАННЫХ ячеек. До prove() (документ не извлекался — доказывать
        нечего) совпадает с числом помеченных; у пустого ledger это честный 0."""
        if self._proven is None:
            return len(self._marks)
        return self._proven

    def __getitem__(self, category: str) -> int:
        return self.counts[category]


def _lesson_proven(
    cell,
    rows,
    unparsed_rows,
    *,
    muam_subjects: tuple[str, ...] | None = None,
) -> bool:
    """Ячейка категории lesson породила РОВНО свои пары — доказано перепарсом.

    Независимо зовём parse_cell(cell.text) и сверяем строки Lesson с cell_key
    этой ячейки против того, что парсер обязан был из неё дать. Ячейка на M пар
    ложится на P колонок групп (лекция на поток: place_row даёт P размещений,
    каждое × M пар), и каждый из P×M исходов — либо строка Lesson, либо отказ
    уникальности слота, ушедший в UnparsedCell с тем же cell_key. Поэтому:

      • перепарс обязан дать пары (не заглушку, не отказ) — иначе ярлык врёт;
      • len(rows) + len(отказов) делится на M нацело и не ноль: пропала одна
        пара из двух — общее число перестаёт делиться либо сигнатуры съезжают;
      • сигнатура каждой строки (предмет/вид/даты/аудитория) встречается не
        чаще, чем P × её кратность в перепарсе: строка «УДАЛЕНО», которой
        парсер не давал, не пройдёт;
      • подгруппа: если у всех пар этой сигнатуры она в тексте явная ('2п/г'),
        строка обязана её нести; None у парсера значит «решает геометрия»,
        и подгруппу размещения мы отсюда проверить не можем — не проверяем.

    Проверяются строки ИМЕННО ЭТОЙ ячейки: близнец с тем же текстом в другой
    клетке сетки имеет другой cell_key и доказывает только себя.
    """
    parsed = (
        _parse_muam_continuation(cell.text, muam_subjects)
        if muam_subjects is not None
        else parse_cell(cell.text)
    )
    if parsed is None:
        return False
    if parsed.reason is not None or parsed.is_placeholder or not parsed.lessons:
        return False
    rejected = sum(1 for row in unparsed_rows if row.raw_text == cell.text)
    outcomes = len(rows) + rejected
    per_placement = len(parsed.lessons)
    if outcomes == 0 or outcomes % per_placement:
        return False
    placements = outcomes // per_placement

    expected = Counter(_parsed_signature(p) for p in parsed.lessons)
    actual = Counter(_row_signature(row) for row in rows)
    if any(
        count > placements * expected.get(sig, 0) for sig, count in actual.items()
    ):
        return False

    explicit_subgroups: dict[tuple, set] = {}
    for lesson in parsed.lessons:
        explicit_subgroups.setdefault(_parsed_signature(lesson), set()).add(
            lesson.subgroup
        )
    for row in rows:
        allowed = explicit_subgroups[_row_signature(row)]
        if None not in allowed and row.subgroup not in allowed:
            return False
    return True


def _parsed_signature(parsed) -> tuple:
    """Сигнатура пары в терминах парсера — та же, что кладёт _add_lesson."""
    return (
        parsed.subject[:200],
        parsed.lesson_kind,
        parsed.date_constraint_raw,
        parsed.room[:50] if parsed.room else None,
    )


def _row_signature(row) -> tuple:
    return (row.subject, row.lesson_kind, row.date_constraint_raw, row.room)


_MAX_IMPORT_DIFF_DETAIL_LINES = 42
_MAX_IMPORT_DIFF_DETAIL_BYTES = 8 * 1024
_IMPORT_DIFF_LINE_ESCAPES = str.maketrans(
    {
        "\r": r"\r",
        "\n": r"\n",
        "\v": r"\v",
        "\f": r"\f",
        "\x1c": r"\u001c",
        "\x1d": r"\u001d",
        "\x1e": r"\u001e",
        "\x85": r"\u0085",
        "\u2028": r"\u2028",
        "\u2029": r"\u2029",
    }
)


@dataclass
class DocumentDiff:
    added: tuple[str, ...]
    removed: tuple[str, ...]

    @property
    def is_empty(self) -> bool:
        return not self.added and not self.removed

    def details(self) -> str:
        total = len(self.removed) + len(self.added)
        if total == 0:
            return ""

        lines: list[str] = []
        bytes_used = 0
        emitted = 0

        def omission_line(omitted: int) -> str:
            return f"… пропущено изменений: {omitted}"

        def append_entry(line: str, *, emitted_after: int) -> bool:
            nonlocal bytes_used
            remaining = total - emitted_after
            reserved = omission_line(remaining) if remaining else None
            line_bytes = len(line.encode("utf-8"))
            candidate_bytes = bytes_used + (1 if lines else 0) + line_bytes
            candidate_lines = len(lines) + 1
            if reserved is not None:
                candidate_bytes += 1 + len(reserved.encode("utf-8"))
                candidate_lines += 1
            if (
                candidate_lines > _MAX_IMPORT_DIFF_DETAIL_LINES
                or candidate_bytes > _MAX_IMPORT_DIFF_DETAIL_BYTES
            ):
                return False
            lines.append(line)
            bytes_used += (1 if len(lines) > 1 else 0) + line_bytes
            return True

        for prefix, items in (("− было: ", self.removed), ("+ стало: ", self.added)):
            for item in items:
                display = item.translate(_IMPORT_DIFF_LINE_ESCAPES)
                if not append_entry(
                    f"{prefix}{display}",
                    emitted_after=emitted + 1,
                ):
                    lines.append(omission_line(total - emitted))
                    return "\n".join(lines)
                emitted += 1
        return "\n".join(lines)


@dataclass
class DocumentReport:
    p_doc_id: str
    section: str
    label: str
    doc_type: DocType
    status: str
    lessons: int = 0
    exams: int = 0
    unparsed: int = 0
    ledger: Ledger = field(default_factory=Ledger)
    diff: DocumentDiff | None = None
    error: str | None = None


@dataclass
class _ImportLinkContext:
    doc_type: DocType = DocType.UNKNOWN


@dataclass
class ImportReport:
    documents: list[DocumentReport] = field(default_factory=list)
    # p_doc_id, которые есть в БД, но исчезли с индексной страницы
    missing: tuple[str, ...] = ()

    @property
    def lessons(self) -> int:
        return sum(d.lessons for d in self.documents)

    @property
    def exams(self) -> int:
        return sum(d.exams for d in self.documents)

    @property
    def unparsed(self) -> int:
        return sum(d.unparsed for d in self.documents)

    @property
    def failed(self) -> int:
        return sum(d.status == STATUS_FAILED for d in self.documents)

    def summary(self) -> str:
        by_status = Counter(d.status for d in self.documents)
        return (
            f"документов {len(self.documents)} ({dict(by_status)}), "
            f"пар {self.lessons}, экзаменов {self.exams}, "
            f"в очереди админа {self.unparsed}, "
            f"исчезло со страницы {len(self.missing)}"
        )


def _canonical_link_document_id(p_doc_id: str | int) -> str:
    if isinstance(p_doc_id, bool):
        raise ReviewValidationError(f"invalid link document id {p_doc_id!r}")
    if isinstance(p_doc_id, int):
        if p_doc_id <= 0:
            raise ReviewValidationError(f"invalid link document id {p_doc_id!r}")
        return str(p_doc_id)
    if isinstance(p_doc_id, str) and re.fullmatch(r"[1-9][0-9]*", p_doc_id):
        return p_doc_id
    raise ReviewValidationError(f"invalid link document id {p_doc_id!r}")


def _preflight_links(links) -> list:
    normalized = []
    seen: set[str] = set()
    for link in links:
        p_doc_id = _canonical_link_document_id(link.p_doc_id)
        if p_doc_id in seen:
            raise ReviewValidationError(
                f"duplicate schedule document id {p_doc_id}"
            )
        seen.add(p_doc_id)
        normalized.append(
            link if link.p_doc_id == p_doc_id else replace(link, p_doc_id=p_doc_id)
        )
    return normalized


def _require_complete_review_input(review_bundle: ReviewBundle, links) -> None:
    linked = {_canonical_link_document_id(link.p_doc_id) for link in links}
    managed = set(review_bundle.corrections.documents)
    missing = sorted(managed - linked, key=int)
    if missing:
        raise ReviewValidationError(
            "managed documents missing from import links: " + ", ".join(missing)
        )


def _require_clean_review_import_session(session) -> None:
    if session.new or session.dirty or session.deleted:
        raise ReviewValidationError(
            "reviewed import requires a clean session boundary"
        )
    if session.in_transaction():
        raise ReviewValidationError(
            "reviewed import requires no active transaction"
        )


def import_all(
    session,
    fetcher,
    links=None,
    *,
    atomic: bool = False,
    review_bundle: ReviewBundle | None = None,
) -> ImportReport:
    """Полный цикл импорта. `fetcher` — Fetcher или его тестовый двойник.

    Суточный live-импорт по умолчанию фиксирует каждый файл отдельно: обрыв
    одного ответа ЮФУ не должен отменять уже скачанные документы. Явный
    ``atomic=True`` предназначен для заранее проверенного локального набора:
    любое исключение выходит вызывающему коду, который откатывает всю пачку.
    ``review_bundle`` опционален: управляемые им документы всегда заново
    разбираются и проходят точную проверку перед snapshot/diff и commit.
    Reviewed-импорт владеет входной границей транзакции: вызывающий код обязан
    передать свежую Session без pending-состояния и без active transaction.
    SQLAlchemy начинает транзакцию даже после простого SELECT, поэтому такую
    read-only транзакцию вызывающий код тоже должен завершить заранее.
    """
    if review_bundle is not None:
        _require_clean_review_import_session(session)
    links = list(links) if links is not None else parse_index(fetcher.fetch_index())
    links = _preflight_links(links)
    if review_bundle is not None:
        _require_complete_review_input(review_bundle, links)
    report = ImportReport()

    known = set(session.scalars(select(ScheduleDocument.p_doc_id)).all())
    seen = {int(link.p_doc_id) for link in links}
    missing = sorted(known - seen)
    if missing:
        report.missing = tuple(str(item) for item in missing)
        # Данные не удаляем: файл мог просто переехать, а студент останется
        # без расписания молча.
        notify_admin(
            "Расписание ЮФУ: файлы исчезли с индексной страницы — "
            f"{', '.join(report.missing)}. Данные сохранены, нужна проверка."
        )

    for link in links:
        if atomic:
            report.documents.append(
                _import_link(
                    session,
                    fetcher,
                    link,
                    review_bundle=review_bundle,
                )
            )
            session.flush()
            continue
        try:
            context = _ImportLinkContext()
            report.documents.append(
                _import_link(
                    session,
                    fetcher,
                    link,
                    review_bundle=review_bundle,
                    _context=context,
                )
            )
            session.commit()
        except Exception as exc:  # noqa: BLE001 — один файл не роняет цикл
            session.rollback()
            logger.exception("Импорт %s упал", link.p_doc_id)
            previous_doc_type = session.scalar(
                select(ScheduleDocument.doc_type).where(
                    ScheduleDocument.p_doc_id == int(link.p_doc_id)
                )
            )
            report.documents.append(
                DocumentReport(
                    p_doc_id=link.p_doc_id,
                    section=link.section,
                    label=link.label,
                    doc_type=previous_doc_type or context.doc_type,
                    status=STATUS_FAILED,
                    error=str(exc),
                )
            )
    return report


def run_schedule_import(
    session_factory: Callable = SessionLocal,
    fetcher=None,
) -> dict:
    """Точка входа для планировщика и CLI. Ошибки — в Telegram, как у новостей."""
    session = session_factory()
    try:
        report = import_all(session, fetcher or Fetcher())
        logger.info("Импорт расписания завершён: %s", report.summary())
        return {
            "summary": report.summary(),
            "failed": report.failed,
            "missing": list(report.missing),
        }
    except Exception as exc:  # noqa: BLE001 — фоновая задача не роняет процесс
        session.rollback()
        logger.exception("Импорт расписания упал")
        notify_admin(f"Импорт расписания ЮФУ упал: {exc}")
        return {"error": str(exc)}
    finally:
        session.close()


def _import_link(
    session,
    fetcher,
    link,
    *,
    review_bundle: ReviewBundle | None = None,
    _context: _ImportLinkContext | None = None,
) -> DocumentReport:
    fetched = fetcher.fetch_document(link.p_doc_id)
    actual_sha256 = hashlib.sha256(fetched.content).hexdigest()
    if fetched.sha256 != actual_sha256:
        raise ReviewValidationError(
            f"document {link.p_doc_id}: fetched content SHA-256 mismatch"
        )
    if review_bundle is not None:
        review_bundle.guard_source(link.p_doc_id, actual_sha256)
    managed = review_bundle is not None and review_bundle.manages(link.p_doc_id)
    doc_type = _DOC_TYPE[_classify(fetched.content)]
    if _context is not None:
        _context.doc_type = doc_type

    document = session.scalar(
        select(ScheduleDocument).where(ScheduleDocument.p_doc_id == int(link.p_doc_id))
    )
    report = DocumentReport(
        p_doc_id=link.p_doc_id,
        section=link.section,
        label=link.label,
        doc_type=doc_type,
        status=STATUS_IMPORTED,
    )

    if document is not None and document.sha256 == actual_sha256 and not managed:
        report.status = STATUS_UNCHANGED
        return report

    before = _snapshot(session, document) if document is not None else ()
    sha_before = document.sha256 if document is not None else None

    if document is None:
        document = ScheduleDocument(
            p_doc_id=int(link.p_doc_id),
            section=link.section,
            label=link.label,
            doc_type=doc_type,
            sha256=actual_sha256,
            source_url=fetched.source_url,
        )
        session.add(document)
        session.flush()
    else:
        _wipe(session, document)
        document.section = link.section
        document.label = link.label
        document.doc_type = doc_type
        document.sha256 = actual_sha256
        document.source_url = fetched.source_url
        document.fetched_at = datetime.now()
        report.status = STATUS_REIMPORTED

    if doc_type in _GRID_TYPES:
        _import_grid_document(session, document, fetched.content, link, report)
    elif doc_type == DocType.EXAM_SESSION:
        _import_exam_document(session, document, fetched.content, link, report)
    else:
        # Аспирантура/учебный план/unknown: не извлекаем вообще. Ledger пуст —
        # и это честно: мы не читали ни одной ячейки, а не «прочли и потеряли».
        report.status = STATUS_SKIPPED

    session.flush()
    # Категория назначена — теперь докажи её. accounted после prove() считает
    # только ячейки, чья категория подтверждена содержимым/БД/позицией.
    report.ledger.prove(session, document)
    # Инвариант «ни одна ячейка не потеряна молча» до сих пор проверялся ТОЛЬКО
    # в тестах: prove() считал accounted/total, но в проде их никто не сравнивал.
    # На новой вёрстке ЮФУ ячейка может потеряться (accounted < total) — тогда
    # студент молча недосчитается пары. Сигналим админу и в лог.
    if report.ledger.accounted < report.ledger.total:
        deficit = report.ledger.total - report.ledger.accounted
        logger.error(
            "Ledger: документ %s (%s) — не учтено %d из %d ячеек",
            link.p_doc_id,
            link.label,
            deficit,
            report.ledger.total,
        )
        notify_admin(
            f"Расписание ЮФУ: в файле {link.p_doc_id} ({link.label}) не учтено "
            f"{deficit} из {report.ledger.total} ячеек — возможна тихая потеря "
            "пар (сменилась вёрстка sfedu.ru?). Нужна проверка."
        )
    if review_bundle is not None and managed:
        # apply_and_validate требует чистую границу и владеет savepoint'ом
        # финальной проверки. prove() обязан видеть parser-only результат,
        # поэтому ручные исправления идут строго после него.
        session.flush()
        correction_result = review_bundle.apply_and_validate(session, document)
        report.lessons += correction_result.added - correction_result.removed
        session.flush()
    if report.status == STATUS_REIMPORTED:
        after = _snapshot(session, document)
        diff = _diff(before, after)
        report.diff = diff
        if not diff.is_empty:
            session.add(
                ImportDiff(
                    document_id=document.id,
                    sha256_before=sha_before or "",
                    sha256_after=actual_sha256,
                    added=len(diff.added),
                    removed=len(diff.removed),
                    details=diff.details(),
                )
            )
            notify_admin(
                f"Расписание ЮФУ: файл {link.p_doc_id} ({link.label}) обновился — "
                f"{len(diff.added)} пар/экзаменов добавлено, {len(diff.removed)} убрано. "
                "Нужна вычитка в админке."
            )
    return report


# ---------------------------------------------------------------- сетка занятий


def _import_grid_document(session, document, content: bytes, link, report) -> None:
    grids, headings = _extract(content)
    report.ledger.account(grids)
    resolver = _GroupResolver(session, link)

    weeks = _load_calendar(session, document, grids, report)
    semester_window = (
        (min(week.date_from for week in weeks), max(week.date_to for week in weeks))
        if weeks
        else (None, None)
    )
    slot_keys: set[tuple] = set()

    header: GridHeader | None = None
    prev_shape: tuple | None = None
    carry_day: int | None = None
    carry_module: Module | None = None
    muam_choices: dict[tuple, tuple[str, ...]] = {}

    for index, grid in enumerate(grids):
        if is_week_calendar(grid):
            _mark_structural_grid(report.ledger, index, grid)
            continue

        heading = headings.get(_heading_key(grid), "")
        found = parse_header(grid)
        first_row: int | None = None
        if found is not None:
            found = _correct_known_group_header(found, link)
            if _is_foreign_bachelor_block(found, link.label):
                # Неизвестный блок другого курса не переносим автоматически:
                # это может быть действительно приложенная чужая таблица.
                # Подтверждённые опечатки исправляются точечно выше.
                _mark_skipped_grid(report.ledger, index, grid)
                header = None
                prev_shape = None
                carry_day = None
                carry_module = None
                continue
            # Тот же блок групп на новой странице — модуль тянем вперёд. Заголовок
            # модуля стоит только на ПЕРВОЙ странице модуля: 13470 — три страницы
            # одних и тех же 6 групп (Пн/Вт, Ср/Чт, Пт/Сб), '(1 сентября – 2
            # ноября)' лишь на первой. Без переноса Ср/Чт/Пт получали module=NULL,
            # шли круглый год и сталкивались с парами других модулей в один слот.
            # Другой блок групп (13471 стр.8 — отдельная группа 3.7 на весь
            # семестр без модуля) СБРАСЫВАЕТ: чужой модуль ей не идёт, иначе её
            # 35 пар пропали бы у студента вне окна модуля.
            if header is None or not _same_group_block(header, found):
                carry_module = None
            header, prev_shape, carry_day = found, _shape(grid), None
            # Строки шапки (0..header_row) — направления, номера групп, 'Время',
            # периоды модулей. parse_rows начинает с header_row+1 и их не видит,
            # поэтому пометить их обязан вызывающий: иначе они не попадут ни в
            # одну категорию и молча выпадут из инварианта.
            _mark_header_rows(report.ledger, index, grid, found.header_row)
        elif header is not None and _shape(grid) == prev_shape:
            # Страница-продолжение: своей шапки нет, геометрия колонок совпадает
            # (13472 p3/p5). Разрыв проходит посреди дня — день тянем с прошлой.
            first_row = 0
        else:
            _skip_table(session, document, report, index, grid)
            continue

        # Модуль объявлен заголовком на ПЕРВОЙ странице блока: 13472 p2 —
        # 'I модуль (1 сентября – 2 ноября)', p3 — продолжение без заголовка.
        # Без carry-forward p3 и p5 остались бы оба без модуля, слились бы в
        # один слот, и половина пар уехала бы в очередь как «слот занят».
        # К тексту вне таблицы добавляем её собственную шапку: 13821 T5/T6 и
        # 13822 p10 объявляют период ТОЛЬКО в шапке колонок ('13 апреля-22
        # июня'), а слово «модуль» либо стоит отдельно, либо отсутствует вовсе.
        heading = f"{heading}\n{_header_text(grid, header, first_row)}"
        carry_module = _module_for(session, document, heading, weeks) or carry_module
        module = carry_module
        page_week = week_type_from_heading(heading)

        slots = parse_rows(grid, header, first_row=first_row, carry_day=carry_day)
        for slot in slots:
            _import_row(
                session, document, report, resolver, grid, index, header,
                slot, module, page_week, slot_keys, muam_choices,
                semester_window,
            )
        carry_day = slots[-1].weekday if slots else carry_day

    _drop_empty_modules(session, document)


def _drop_empty_modules(session, document) -> None:
    """Модуль, на который не легло ни одной пары, — фантом, а не период.

    13497 p11 объявляет '2 модуль: 3 ноября – 15 января', но пары страницы
    уехали в слоты соседних модулей: остаётся строчка в списке модулей, за
    которой для студента пусто. Пары она не фильтрует (на неё никто не
    ссылается) — только мусорит в UI и у админа.
    """
    session.flush()
    modules = session.scalars(
        select(Module).where(Module.document_id == document.id)
    ).all()
    for module in modules:
        used = session.scalar(
            select(Lesson.id).where(Lesson.module_id == module.id).limit(1)
        )
        if used is None:
            session.delete(module)
    session.flush()


def _is_foreign_bachelor_block(header: GridHeader, label: str) -> bool:
    """Блок N.x внутри файла другого курса не становится отдельной группой."""
    if header.level is not EducationLevel.BACHELOR:
        return False
    match = _MASTER_COURSE.search(label)
    if match is None:
        return False
    document_course = int(match.group(1))
    group_courses = {
        int(group.number.split(".")[0])
        for group in header.groups
        if group.number is not None
    }
    return bool(group_courses) and group_courses != {document_course}


def _correct_known_group_header(header: GridHeader, link) -> GridHeader:
    """Исправляет подтверждённую опечатку в конкретном официальном файле.

    14178 целиком подписан «4 курс», а отдельная последняя страница программы
    «Информационные технологии и бизнес-аналитика» помечена как 3.7. Это группа
    4.7: пользователь подтвердил принадлежность, и в блоке есть две реальные
    пары. Общую эвристику «чужой курс → переписать» не вводим — вложенный блок
    действительно может относиться к другому курсу.
    """
    numbers = tuple(group.number for group in header.groups)
    if (
        str(link.p_doc_id) == "14178"
        and link.label.strip().lower() == "4 курс"
        and header.level is EducationLevel.BACHELOR
        and numbers == ("3.7",)
    ):
        return replace(
            header,
            groups=(replace(header.groups[0], number="4.7"),),
            course=4,
        )
    return header


def _muam_slot_key(header, placement, slot, module, *, pair_number=None) -> tuple:
    """Идентичность слота МУАМ без координат PDF, которые меняются по строкам."""
    group = placement.group
    return (
        header.level,
        header.course,
        group.number,
        group.program,
        slot.weekday,
        module.id if module else None,
        slot.pair_number if pair_number is None else pair_number,
    )


def _previous_muam_choices(header, placements, slot, module, choices_by_slot):
    """Канонические предметы МУАМ из непосредственно предыдущей пары.

    Ячейка может покрывать несколько групп. Контекст допустим только когда у
    КАЖДОЙ из них предыдущий слот содержит один и тот же список вариантов —
    иначе неоднозначную строку оставляем в очереди админу.
    """
    if slot.weekday is None or slot.pair_number is None or slot.pair_number <= 1:
        return None
    choices = []
    for placement in placements:
        previous = choices_by_slot.get(
            _muam_slot_key(
                header,
                placement,
                slot,
                module,
                pair_number=slot.pair_number - 1,
            )
        )
        if previous is None:
            return None
        choices.append(previous)
    if not choices or any(value != choices[0] for value in choices[1:]):
        return None
    return choices[0]


def _muam_tokens(subject: str) -> tuple[str, ...]:
    label = subject.removeprefix("МУАМ — ").casefold().replace("ё", "е")
    return tuple(re.findall(r"[0-9a-zа-я]+", label))


def _same_muam_subject(raw: str, canonical: str) -> bool:
    """Равенство с точечным допуском сокращения «Совр.» → «Современные».

    Это не общий fuzzy-match предметов: сравнение разрешено только между
    соседними строками одного блока МУАМ, число и порядок слов обязаны
    совпасть, а сокращённый токен содержит минимум четыре символа.
    """
    raw_tokens = _muam_tokens(raw)
    canonical_tokens = _muam_tokens(canonical)
    if len(raw_tokens) != len(canonical_tokens):
        return False
    return all(
        left == right
        or (
            min(len(left), len(right)) >= 4
            and (left.startswith(right) or right.startswith(left))
        )
        for left, right in zip(raw_tokens, canonical_tokens)
    )


def _parse_muam_continuation(text: str, subjects: tuple[str, ...]):
    """Разбирает строку МУАМ без заголовка и возвращает прежние имена курсов."""
    parsed = parse_cell(f"МУАМ {text}")
    if parsed.reason is not None or len(parsed.lessons) != len(subjects):
        return None
    if any(
        not _same_muam_subject(lesson.subject, subject)
        for lesson, subject in zip(parsed.lessons, subjects)
    ):
        return None
    return replace(
        parsed,
        lessons=tuple(
            replace(lesson, subject=subject, cell_raw=text)
            for lesson, subject in zip(parsed.lessons, subjects)
        ),
    )


def _import_row(
    session, document, report, resolver, grid, index, header,
    slot, module, page_week, slot_keys, muam_choices, semester_window,
) -> None:
    ledger = report.ledger
    for cell in grid.row(slot.row):
        if cell.is_empty:
            ledger.mark(index, cell, CELL_EMPTY)
        elif cell.col_start <= header.time_col:
            ledger.mark_structural(index, cell)  # день и время: доказано позицией

    if slot.is_separator:
        return

    placements = place_row(grid, slot.row, header)
    placed = {id(p.cell): p for p in placements}
    payload = [
        cell
        for cell in grid.row(slot.row)
        if cell.col_start > header.time_col and not cell.is_empty
    ]

    for cell in payload:
        key = _cell_key(index, cell)
        if id(cell) not in placed:
            # Инвариант A6: таких нет ни одной. Если появится — не молча.
            _unparsed(
                session, document, report, grid, cell, REASON_NO_GROUP_COLUMN,
                cell_key=key,
            )
            ledger.mark(index, cell, CELL_UNPARSED)
            continue
        cell_placements = [p for p in placements if p.cell is cell]
        parsed = parse_cell(cell.text)
        continuation_subjects = None
        if parsed.reason == REASON_NO_BOUNDARY:
            continuation_subjects = _previous_muam_choices(
                header,
                cell_placements,
                slot,
                module,
                muam_choices,
            )
            if continuation_subjects is not None:
                parsed = (
                    _parse_muam_continuation(cell.text, continuation_subjects)
                    or parsed
                )
        if parsed.is_placeholder:
            # '…………….' = «занятий нет». Проверяется РАНЬШЕ причин строки:
            # заглушка в строке с кривым временем — всё равно заглушка, а не
            # потерянное занятие, и админу в очереди не нужна.
            ledger.mark(index, cell, CELL_PLACEHOLDER)
            continue

        reason = slot.reason or _slot_gap(slot)
        if reason:
            # время вне сетки пар / день не распознан / времени нет вовсе —
            # угадывать запрещено: '800- 1025' это не «примерно первая пара»
            _unparsed(session, document, report, grid, cell, reason, cell_key=key)
            ledger.mark(index, cell, CELL_UNPARSED)
            continue

        if parsed.reason:
            _unparsed(
                session, document, report, grid, cell, parsed.reason, cell_key=key,
            )
            ledger.mark(index, cell, CELL_UNPARSED)
            continue

        if parsed.lessons and all(
            lesson.subject.startswith("МУАМ — ") for lesson in parsed.lessons
        ):
            current_choices = tuple(lesson.subject for lesson in parsed.lessons)
            for placement in cell_placements:
                muam_choices[
                    _muam_slot_key(header, placement, slot, module)
                ] = current_choices

        made = False
        for placement in cell_placements:
            for lesson in parsed.lessons:
                made |= _add_lesson(
                    session, document, report, resolver, header, placement,
                    slot, lesson, module, page_week, slot_keys, grid, key,
                    semester_window,
                )
        if made and continuation_subjects is not None:
            ledger.mark_muam_lesson(index, cell, continuation_subjects)
        else:
            ledger.mark(index, cell, CELL_LESSON if made else CELL_UNPARSED)


def _add_lesson(
    session, document, report, resolver, header, placement,
    slot, parsed, module, page_week, slot_keys, grid, cell_key, semester_window,
) -> bool:
    group = resolver.resolve(header, placement.group)
    # Текстовая метка '1п/г' побеждает геометрию: она однозначна, а нарезка
    # кусков — догадка по колонкам.
    subgroup = parsed.subgroup if parsed.subgroup is not None else placement.subgroup
    week_type = parsed.week_type or page_week

    base_from = module.date_from if module else None
    base_to = module.date_to if module else None
    if parsed.date_constraint_raw is not None:
        # A prefix has no year, so a lesson without a module uses the imported
        # week calendar as its bounded semester.  Never guess a year.
        base_from = base_from or semester_window[0]
        base_to = base_to or semester_window[1]
    dates = resolve_date_constraint(parsed.date_constraint_raw, base_from, base_to)
    if dates is None:
        _unparsed(
            session,
            document,
            report,
            grid,
            placement.cell,
            REASON_DATE_CONSTRAINT,
            cell_key=cell_key,
        )
        return False

    # Ключ слота = ключ уникального индекса Lesson. Дата и предмет в нём не
    # украшение: 13469 кладёт в одну ячейку 'До 17.12 …' и '24.12 …' (разные
    # даты), 13472 p3 — два параллельных занятия (разные предметы). И то и
    # другое живёт в одном (день, пара) законно.
    key = (
        group.id, slot.weekday, slot.pair_number, week_type, subgroup,
        module.id if module else None, parsed.date_constraint_raw,
        dates.valid_from, dates.valid_to,
        parsed.subject[:200],
    )
    if key in slot_keys:
        # cell_key обязателен: prove() считает отказы слота исходами ИМЕННО
        # этой ячейки — без ключа P×M не сойдётся и честная ячейка покраснеет.
        _unparsed(
            session, document, report, grid, placement.cell, REASON_SLOT_TAKEN,
            cell_key=cell_key,
        )
        return False
    slot_keys.add(key)

    # Границы занятия — реальное окно из ячейки времени (у блока в 3 ак. часа
    # оно шире одной пары); для обычной пары это те же внешние края её половин.
    starts = (
        parsed.starts_at_override
        or slot.starts_at
        or _pair_bounds(slot.pair_number)[0]
    )
    ends = slot.ends_at or _pair_bounds(slot.pair_number)[1]
    session.add(
        Lesson(
            group_id=group.id,
            document_id=document.id,
            module_id=module.id if module else None,
            weekday=slot.weekday,
            pair_number=slot.pair_number,
            starts_at=starts,
            ends_at=ends,
            subject=parsed.subject[:200],
            lesson_kind=parsed.lesson_kind,
            teacher_id=_teacher_id(session, parsed.teachers),
            room=parsed.room[:50] if parsed.room else None,
            week_type=week_type,
            subgroup=subgroup,
            date_constraint_raw=parsed.date_constraint_raw,
            cell_raw=parsed.cell_raw,
            cell_key=cell_key,
            valid_from=dates.valid_from,
            valid_to=dates.valid_to,
            specific_dates=[value.isoformat() for value in dates.specific_dates],
        )
    )
    report.lessons += 1
    return True


def _load_calendar(session, document, grids, report) -> list:
    """Календарь недель — данные, а не формула. Расхождение с ISO-чётностью
    аномалия слоя weeks и едет в очередь админа, но week_type всё равно из файла."""
    weeks: list = []
    for grid in grids:
        if not is_week_calendar(grid):
            continue
        parsed = parse_week_calendar(grid)
        for week in parsed.weeks:
            if any(w.date_from == week.date_from and w.date_to == week.date_to for w in weeks):
                continue
            weeks.append(week)
            session.add(
                WeekCalendar(
                    document_id=document.id,
                    date_from=week.date_from,
                    date_to=week.date_to,
                    week_type=week.week_type,
                )
            )
        for anomaly in parsed.anomalies:
            session.add(
                UnparsedCell(
                    document_id=document.id,
                    page=grid.page,
                    raw_text=anomaly.raw_text,
                    reason=anomaly.reason[:200],
                )
            )
            report.unparsed += 1
    session.flush()
    return weeks


def _module_for(session, document, heading: str, weeks) -> Module | None:
    """Модуль страницы/таблицы по заголовку. None — заголовка нет.

    Год в заголовке не пишут ('I модуль (1 сентября – 2 ноября)') — берём его
    из календаря недель этого же файла. Без календаря датировать модуль нечем,
    и выдумывать год нельзя: осенний семестр пересекает границу года.
    """
    if not weeks:
        return None
    bounds = _module_bounds(heading, weeks)
    if bounds is None:
        return None
    name, date_from, date_to = bounds

    existing = session.scalar(
        select(Module).where(
            Module.document_id == document.id,
            Module.date_from == date_from,
            Module.date_to == date_to,
        )
    )
    if existing is not None:
        return existing
    module = Module(
        document_id=document.id,
        name=name,
        date_from=date_from,
        date_to=date_to,
    )
    session.add(module)
    session.flush()
    return module


def _module_bounds(heading: str, weeks) -> tuple[str | None, date, date] | None:
    """(имя, начало, конец) модуля из заголовка и шапки. None — модуля нет.

    Имя необязательно: 13469 T4 подписан просто «24 ноября – 11 января», слова
    «модуль» там нет. Ключ модуля — даты (решение №5 плана), имя — для админа.
    """
    match = None
    for match in _MODULE.finditer(heading):
        pass  # последний заголовок страницы — тот, под которым идёт таблица
    if match is not None:
        date_from = _resolve_date(int(match.group(2)), match.group(3), weeks)
        date_to = _resolve_date(int(match.group(4)), match.group(5), weeks)
        if date_from and date_to and date_from <= date_to:
            return f"{match.group(1)} модуль", date_from, date_to
        return None

    name = _MODULE_NAME.search(heading)
    # Диапазоны, подписанные словом «семестр», в расчёт не берём: это срок
    # семестра, а не модуля. Останется пусто — модуля у страницы просто нет.
    semester_at = {match.end() for match in _SEMESTER_RANGE.finditer(heading)}
    ranges = [
        (start, end)
        for raw in _DATE_RANGE.finditer(heading)
        if raw.start() not in semester_at
        and (start := _resolve_date(int(raw.group(1)), raw.group(2), weeks))
        and (end := _resolve_date(int(raw.group(3)), raw.group(4), weeks))
        and start <= end
    ]
    if not ranges:
        return None
    # У каждой группы свой конец модуля ('22 июня', '23 июня', '10 июня') —
    # берём объединение: модуль как период страницы, а не как срок группы.
    date_from = min(start for start, _ in ranges)
    date_to = max(end for _, end in ranges)
    if name is None and _covers_whole_semester(date_from, date_to, weeks):
        # 13822 p13: 'весенний семестр 2025-2026 учебный год' и '9 февраля –
        # 26 июня' стоят РАЗНЫМИ строками, поэтому _SEMESTER_RANGE их не
        # связывает — а это срок семестра, и модулем он становился фантомом во
        # весь семестр. Ловим по датам, а не по слову: слово «семестр» стоит и
        # в шапке 13828 ('на весенний семестр … 9 февраля – 07 апреля'), где
        # безымянный модуль настоящий. Отличает их покрытие: модуль — ЧАСТЬ
        # семестра, а то, что накрывает все недели календаря, и есть семестр.
        return None
    return (
        f"{name.group(1)} модуль" if name else None,
        date_from,
        date_to,
    )


def _covers_whole_semester(date_from: date, date_to: date, weeks) -> bool:
    """Диапазон задевает каждую неделю календаря файла — то есть весь семестр.

    Считаем по неделям, а не по краям календаря: подпись семестра обрывается на
    последнем учебном дне ('26 июня' при календаре до 28-го), и сравнение дат
    «в лоб» такой семестр за семестр не признает.

    Нет календаря — судить о «весь семестр» нечем: all([]) вакуумно истинно и
    выбросило бы КАЖДЫЙ безымянный модуль как мнимый семестр. Нечем доказать —
    значит не семестр: модуль сохраняем.
    """
    if not weeks:
        return False
    return all(
        date_from <= week.date_to and date_to >= week.date_from for week in weeks
    )


def _header_text(grid: Grid, header: GridHeader, first_row: int | None) -> str:
    """Текст шапки таблицы. У страницы-продолжения шапки нет — и текста нет."""
    if first_row is not None:
        return ""
    return " ".join(
        cell.text for cell in grid.cells if cell.row <= header.header_row
    )


def _resolve_date(day: int, month_name: str, weeks) -> date | None:
    month = _MONTHS.get(month_name.lower())
    if month is None:
        return None
    years = {w.date_from.year for w in weeks} | {w.date_to.year for w in weeks}
    inside = [
        candidate
        for year in sorted(years)
        if (candidate := _safe_date(year, month, day))
        and any(w.date_from <= candidate <= w.date_to for w in weeks)
    ]
    if inside:
        return inside[0]
    # Дата вне календаря (модуль начинается до первой недели) — берём год по
    # месяцу: сентябрь–декабрь это первый год диапазона, январь–август второй.
    fallback = min(years) if month >= 9 else max(years)
    return _safe_date(fallback, month, day)


def _safe_date(year: int, month: int, day: int) -> date | None:
    try:
        return date(year, month, day)
    except ValueError:
        return None


# -------------------------------------------------------------------- экзамены


def _import_exam_document(session, document, content: bytes, link, report) -> None:
    grids, _ = _extract(content)
    report.ledger.account(grids)
    result = exams_module.parse_exams(grids)
    resolver = _GroupResolver(session, link)

    for exam in result.exams:
        group = resolver.resolve_exam(exam)
        session.add(
            ExamEvent(
                group_id=group.id,
                document_id=document.id,
                subject=exam.subject[:300],
                teacher=", ".join(exam.teachers)[:200] or None,
                consultation_at=_slot_at(exam.consultation),
                exam_at=_slot_at(exam.exam),
                room=(exam.exam.room[:50] if exam.exam and exam.exam.room else None),
                kind=(exam.exam.kind[:50] if exam.exam and exam.exam.kind else None),
                cell_raw=exam.cell_raw,
            )
        )
        report.exams += 1

    for fragment in result.unparsed:
        session.add(
            UnparsedCell(
                document_id=document.id,
                page=fragment.page,
                raw_text=fragment.raw_text,
                reason=fragment.reason[:200],
            )
        )
        report.unparsed += 1

    kinds = exams_module.row_kinds(grids)
    for index, grid in enumerate(grids):
        for cell in grid.cells:
            if cell.is_empty:
                report.ledger.mark(index, cell, CELL_EMPTY)
                continue
            kind = kinds.get((index, cell.row))
            if kind == "payload":
                # Строка с нагрузкой: слой exams выдал по ней либо ExamEvent,
                # либо UnparsedFragment — его собственный инвариант
                # subject_rows_seen == exams + unparsed это гарантирует. Позиция
                # (строка-нагрузка) и есть доказательство категории.
                report.ledger.mark_exam(index, cell)
            elif kind == "header":
                report.ledger.mark_structural(index, cell)
            else:
                # Непустая ячейка в строке без нагрузки: exams её не читает,
                # значит она пропала бы молча. Отправляем админу.
                _unparsed(
                    session, document, report, grid, cell, REASON_EXAM_ROW,
                    cell_key=_cell_key(index, cell),
                )
                report.ledger.mark(index, cell, CELL_UNPARSED)


def _slot_at(slot) -> datetime | None:
    if slot is None or not slot.dates:
        return None
    return datetime.combine(slot.dates[0], slot.time_start or time(0, 0))


# ------------------------------------------------------------------- служебное


class _GroupResolver:
    """Группа по шапке. У магистров номера НЕТ — их идентифицирует программа."""

    def __init__(self, session, link):
        self._session = session
        self._label = link.label
        self._cache: dict[tuple, Group] = {}

    def resolve(self, header: GridHeader, column) -> Group:
        if column.number:
            course = int(column.number.split(".")[0])
            return self._get(course, number=column.number, level=EducationLevel.BACHELOR)
        course = header.course or self._course_from_label()
        return self._get(course, program=column.program, level=EducationLevel.MASTER)

    def resolve_exam(self, exam) -> Group:
        if exam.group_number:
            course = int(exam.group_number.split(".")[0])
            return self._get(
                course, number=exam.group_number, level=EducationLevel.BACHELOR
            )
        return self._get(
            self._course_from_label(),
            program=exam.master_program,
            level=EducationLevel.MASTER,
        )

    def _course_from_label(self) -> int:
        match = _MASTER_COURSE.search(self._label)
        return int(match.group(1)) if match else 0

    def _get(self, course, *, number=None, program=None, level) -> Group:
        # Единственная точка сведения магистерских программ: и путь пар (чистое
        # имя из расписаний), и путь экзаменов (грязное имя в обёртке из сессий)
        # проходят здесь. Канонизируем ДО ключа кэша и запроса — тогда оба
        # написания дают одну группу на (курс, каноническая программа), сливая
        # пары и экзамены независимо от порядка обработки файлов.
        if program is not None:
            program = canonical_program(program)
        key = (course, number, program)
        if key in self._cache:
            return self._cache[key]
        group = self._session.scalar(
            select(Group).where(
                Group.course == course,
                Group.number.is_(None) if number is None else Group.number == number,
                Group.program.is_(None) if program is None else Group.program == program,
            )
        )
        if group is None:
            group = Group(
                course=course,
                number=number,
                program=(program or None) and program[:300],
                level=level,
            )
            self._session.add(group)
            self._session.flush()
        self._cache[key] = group
        return group


def _teacher_id(session, teachers: tuple[str, ...]) -> int | None:
    """Первый преподаватель. Модель держит одного, полный список остаётся
    в cell_raw — второй лектор не теряется, но SQL'ем его не спросишь."""
    if not teachers:
        return None
    name = teachers[0][:200]
    teacher = session.scalar(select(Teacher).where(Teacher.full_name == name))
    if teacher is None:
        teacher = Teacher(full_name=name)
        session.add(teacher)
        session.flush()
    return teacher.id


def _slot_gap(slot) -> str | None:
    """Строка занятий без дня или без пары. parse_rows такую причину не
    формулирует (у неё нет времени вовсе — не «вне сетки», а пусто), а Lesson
    требует и день, и номер пары: положить туда None — молча испортить."""
    if slot.weekday is None:
        return REASON_NO_WEEKDAY
    if slot.pair_number is None:
        return REASON_NO_PAIR
    return None


def _pair_bounds(pair_number: int) -> tuple[time, time]:
    first, second = PAIR_HALVES[pair_number]
    return _as_time(first[0]), _as_time(second[1])


def _as_time(value: int) -> time:
    return time(value // 100, value % 100)


def _unparsed(
    session, document, report, grid, cell, reason: str, *, cell_key: str | None = None,
) -> None:
    """cell_key обязателен для всякой ячейки сетки: он связывает запись очереди
    с породившей ячейкой, и prove() доказывает категорию unparsed именно по
    нему. None допустим только для фрагментов без ячейки (аномалии календаря,
    неразобранные куски сессии) — те не носят категории в Ledger вовсе."""
    session.add(
        UnparsedCell(
            document_id=document.id,
            page=grid.page,
            raw_text=cell.text,
            reason=reason[:200],
            cell_key=cell_key,
        )
    )
    report.unparsed += 1


def _skip_table(session, document, report, index: int, grid: Grid) -> None:
    """Таблица без шапки расписания: учебный план — пропускаем осознанно,
    всё остальное — в очередь админа поячеечно."""
    text = " ".join(cell.text for cell in grid.cells)
    known = bool(_CURRICULUM_TABLE.search(text))
    for cell in grid.cells:
        if cell.is_empty:
            report.ledger.mark(index, cell, CELL_EMPTY)
        elif known:
            report.ledger.mark_skipped(index, cell)
        else:
            _unparsed(
                session, document, report, grid, cell, REASON_UNKNOWN_TABLE,
                cell_key=_cell_key(index, cell),
            )
            report.ledger.mark(index, cell, CELL_UNPARSED)


def _mark_header_rows(ledger: Ledger, index: int, grid: Grid, header_row: int) -> None:
    """Шапка таблицы — тоже ячейки, и они тоже обязаны быть учтены.

    Категория «структура» здесь честная: это не занятия, читать их как занятия
    нечего, но и пропасть они не должны.
    """
    for cell in grid.cells:
        if cell.row <= header_row:
            if cell.is_empty:
                ledger.mark(index, cell, CELL_EMPTY)
            else:
                ledger.mark_structural(index, cell)


def _mark_structural_grid(ledger: Ledger, index: int, grid: Grid) -> None:
    """Вся таблица структурна — так помечается календарь недель целиком."""
    for cell in grid.cells:
        if cell.is_empty:
            ledger.mark(index, cell, CELL_EMPTY)
        else:
            ledger.mark_structural(index, cell)


def _mark_skipped_grid(ledger: Ledger, index: int, grid: Grid) -> None:
    """Осознанно исключённый блок: каждая ячейка остаётся в Ledger."""
    for cell in grid.cells:
        if cell.is_empty:
            ledger.mark(index, cell, CELL_EMPTY)
        else:
            ledger.mark_skipped(index, cell)


def _group_ids(header: GridHeader) -> tuple:
    return tuple((group.number, group.program) for group in header.groups)


def _same_group_block(prev: GridHeader, found: GridHeader) -> bool:
    """Одни и те же группы у двух шапок — значит это один блок расписания,
    разложенный по страницам (13470: Пн/Вт, Ср/Чт, Пт/Сб — одни 6 групп на трёх
    страницах с разной шириной колонок). Сравниваем ИДЕНТИЧНОСТЬ групп (номер/
    программа), а не геометрию: у разных дней число тонких столбцов-границ
    отличается, и _shape по страницам блока не совпадает."""
    return _group_ids(prev) == _group_ids(found)


def _shape(grid: Grid) -> tuple:
    """Геометрия колонок с допуском 1 pt: у 13472 p2/p3 границы совпадают в
    пределах 0.3 pt, «побайтово» из разведки — преувеличение."""
    if grid.col_bounds is None:
        return (grid.n_cols,)
    return (grid.n_cols,) + tuple(round(value) for value in grid.col_bounds)


def _heading_key(grid: Grid):
    return grid.page if grid.page is not None else ("table", grid.table_index)


def _wipe(session, document) -> None:
    """Переразбор: старые данные документа уходят, ScheduleDocument остаётся."""
    for model in (Lesson, ExamEvent, UnparsedCell, Module, WeekCalendar):
        session.execute(delete(model).where(model.document_id == document.id))
    session.flush()


def _snapshot(session, document) -> tuple[str, ...]:
    lessons = session.scalars(
        select(Lesson).where(Lesson.document_id == document.id)
    ).all()
    exams = session.scalars(
        select(ExamEvent).where(ExamEvent.document_id == document.id)
    ).all()
    p_doc_id = str(document.p_doc_id)
    items = [
        state_signature(lesson_state(lesson, p_doc_id=p_doc_id))
        for lesson in lessons
    ] + [_exam_snapshot_signature(exam, p_doc_id=p_doc_id) for exam in exams]
    return tuple(sorted(items))


def _exam_snapshot_signature(exam: ExamEvent, *, p_doc_id: str) -> str:
    group = exam.group
    payload = {
        "document": p_doc_id,
        "group": {
            "level": group.level.value,
            "course": group.course,
            "number": group.number,
            "program": group.program,
        },
        "subject": exam.subject,
        "teacher": exam.teacher,
        "consultation_at": (
            exam.consultation_at.isoformat() if exam.consultation_at else None
        ),
        "exam_at": exam.exam_at.isoformat() if exam.exam_at else None,
        "room": exam.room,
        "kind": exam.kind,
    }
    return "экзамен:" + json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _diff(before: tuple[str, ...], after: tuple[str, ...]) -> DocumentDiff:
    was, now = Counter(before), Counter(after)
    return DocumentDiff(
        added=tuple(sorted((now - was).elements())),
        removed=tuple(sorted((was - now).elements())),
    )


# ------------------------------------------------------- извлечение из байтов


def _classify(content: bytes) -> classify_module.DocType:
    suffix = ".docx" if _is_docx(content) else ".pdf"
    with tempfile.NamedTemporaryFile(suffix=suffix) as handle:
        handle.write(content)
        handle.flush()
        return classify_module.classify(handle.name)


def _is_docx(content: bytes) -> bool:
    return content[:2] == b"PK"


def _extract(content: bytes) -> tuple[list[Grid], dict]:
    """Grid'ы документа и текст ВНЕ таблиц, по странице (PDF) или по таблице (docx).

    Текст вне таблиц нужен двум вещам: 'ВЕРХНЯЯ НЕДЕЛЯ' и 'I модуль (…)' лежат
    именно там, а не в ячейках — Grid их не видит в принципе.
    """
    if _is_docx(content):
        return extract_docx(content), _docx_headings(content)
    return extract_pdf(content), _pdf_page_texts(content)


def _pdf_page_texts(content: bytes) -> dict[int, str]:
    """Текст страницы ВНЕ таблиц — то, что можно считать её заголовком.

    page.extract_text() отдаёт весь текст страницы, ВКЛЮЧАЯ ячейки таблицы. Для
    заголовка это яд: маркер 'Верхняя неделя' внутри ячейки относится к ОДНОЙ
    паре (план §A6 Step 4), а через week_type_from_heading → page_week он красил
    страницу целиком — 45 еженедельных пар 13820 p5 получали upper и исчезали у
    студента на нижней неделе.

    Настоящих маркеров страницы в корпусе четыре (13471 p10/p11 'ВЕРХНЯЯ
    НЕДЕЛЯ', 13472 p14/p15 'НЕДЕЛЯ: ВЕРХНЯЯ') — все они лежат вне таблицы и
    отбор по bbox их сохраняет. Периоды модулей из шапки колонок теряются здесь
    намеренно: их возвращает _header_text() из самой таблицы.
    """
    texts: dict[int, str] = {}
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page in pdf.pages:
            boxes = [table.bbox for table in page.find_tables()]
            outside = page.filter(lambda obj: not _inside_any(obj, boxes))
            texts[page.page_number] = outside.extract_text() or ""
    return texts


def _inside_any(obj, boxes) -> bool:
    """Лежит ли центр объекта внутри хотя бы одной таблицы."""
    x = (obj["x0"] + obj["x1"]) / 2
    y = (obj["top"] + obj["bottom"]) / 2
    return any(x0 <= x <= x1 and top <= y <= bottom for x0, top, x1, bottom in boxes)


def _docx_headings(content: bytes) -> dict:
    """Абзацы перед каждой таблицей: в docx модуль объявлен параграфом между
    таблицами, страниц там нет."""
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        root = ET.fromstring(archive.read("word/document.xml"))
    body = root.find(f"{_W}body")
    headings: dict = {}
    buffer: list[str] = []
    table_index = 0
    for node in body if body is not None else []:
        if node.tag == f"{_W}p":
            buffer.append("".join(t.text or "" for t in node.iter(f"{_W}t")))
        elif node.tag == f"{_W}tbl":
            headings[("table", table_index)] = "\n".join(buffer)
            buffer = []
            table_index += 1
    return headings


if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(level=logging.INFO)
    print(run_schedule_import())
