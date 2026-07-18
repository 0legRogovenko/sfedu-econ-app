"""Расписание сессии → ExamEvent.

Экзамены — отдельная сущность, а не Lesson: у них нет ни дня недели, ни номера
пары, зато есть дата, форма и консультация. 11 файлов из 29 — сессии.

Таблица везде одна и та же по смыслу:

    № группы | Направление / профиль | [Кол-во студентов] | Наименование
    дисциплины | Дата консультации | Дата экзамена

но НЕ по разметке. Колонка «Кол-во студентов» то есть, то нет; на 13744 стр.2
та же таблица разложена на 14 колонок вместо 6 (шапка занимает диапазоны
(2,4), (5,7)…). Поэтому роль колонки берётся из шапки по пересечению
диапазонов, а индексы не значат ничего.

Разобрано по всем 11 файлам; всё, что здесь лечится, взято из них, а не
придумано (см. tests/test_exams.py — там на каждый случай ссылка на файл).
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, time
from enum import Enum

from .grid import Grid
from .rooms import normalize_room


class _Role(str, Enum):
    GROUP = "group"
    DIRECTION = "direction"
    COUNT = "count"
    SUBJECT = "subject"
    CONSULT = "consult"
    EXAM = "exam"


# Порядок важен: признаки не пересекаются, но «дисциплин» есть и в шапке
# предмета, и рядом; сначала — самые узкие.
_ROLE_PATTERNS: tuple[tuple[_Role, re.Pattern[str]], ...] = (
    (_Role.EXAM, re.compile(r"дата\s*экзамена", re.IGNORECASE)),
    (_Role.CONSULT, re.compile(r"дата\s*консультации", re.IGNORECASE)),
    (_Role.GROUP, re.compile(r"№\s*группы", re.IGNORECASE)),
    (_Role.COUNT, re.compile(r"кол-во", re.IGNORECASE)),
    (_Role.SUBJECT, re.compile(r"наименование|дисциплин", re.IGNORECASE)),
    (_Role.DIRECTION, re.compile(r"направлени|профиль", re.IGNORECASE)),
)

_MASTER_PROGRAM = re.compile(r"магистерск\w*\s*программ", re.IGNORECASE)

_DATE = re.compile(r"\b(\d\d?)\.(\d\d?)\.(\d\d)\b")
# Время ЮФУ пишет через точку («09.00-13.30»), тире — и обычное, и длинное.
_TIME_RANGE = re.compile(r"\b(\d\d?)[.:](\d\d)\s*[-–—]\s*(\d\d?)[.:](\d\d)\b")
_TIME_SINGLE = re.compile(r"\b(\d\d?)[.:](\d\d)\b")

# Строка, с которой начинается «где»: аудитория, город, улица, площадка.
# Аудиторией дело не ограничивается: 13747 отправляет группу 3.7 в Таганрог
# («г.Таганрог, ул.Энгельса, 1, Г-215») — там и «ауд.» нет, и корпус другой.
_LOCATION = re.compile(
    r"^(?:ауд|а|г|ул)\s*\.|^(?:онлайн|online|Microsoft\s+Teams|Moodle|Zoom)\b"
    r"|^[А-ЯЁA-Z]-\d",
    re.IGNORECASE,
)

# ФИО: «Фамилия И.О.». Фамилия бывает через дефис («Кривошеева-Медянцева»),
# инициалы — латиницей у англоязычных программ, а точка после последнего
# инициала иногда потеряна («Туманян Ю.Р» в 13767).
_FIO_SRC = (
    r"[А-ЯЁA-Z][а-яёa-z]+(?:-[А-ЯЁA-Z][а-яёa-z]+)?\s+[А-ЯЁA-Z]\.\s*[А-ЯЁA-Z]\.?"
)
_FIO = re.compile(_FIO_SRC)
# Преподаватели идут хвостом ячейки: через запятую («Алехин В.В., Захарова Д.С.»)
# или просто переносом строки («Туманян Ю.Р\nПогосян Н.В.»).
_TEACHERS_TAIL = re.compile(rf"(?:{_FIO_SRC})(?:\s*[,;]?\s*(?:{_FIO_SRC}))*\s*[,.]?\s*$")


@dataclass(frozen=True)
class ExamSlot:
    """Разобранная ячейка даты — консультации или экзамена.

    dates — все даты, найденные в ячейке. Обычно одна, но 14049 ставит
    иностранный язык на две («04.06.26 (уровень А)» / «05.06.26 (уровень В)»),
    и тогда date=None: выбрать одну из двух — соврать половине группы.
    """

    dates: tuple[date, ...]
    time_start: time | None
    time_end: time | None
    kind: str | None
    room: str | None
    raw: str

    @property
    def date(self) -> date | None:
        return self.dates[0] if len(self.dates) == 1 else None


@dataclass(frozen=True)
class ParsedExam:
    """Один экзамен. group_number ИЛИ master_program — ровно одно из двух."""

    group_number: str | None
    master_program: str | None
    direction_raw: str | None
    subject: str
    teachers: tuple[str, ...]
    consultation: ExamSlot | None
    exam: ExamSlot | None
    page: int | None
    cell_raw: str


@dataclass(frozen=True)
class UnparsedFragment:
    page: int | None
    raw_text: str
    reason: str


@dataclass(frozen=True)
class ExamParseResult:
    exams: tuple[ParsedExam, ...]
    unparsed: tuple[UnparsedFragment, ...]
    # Сколько строк с полезной нагрузкой встретилось в источнике. Сходится с
    # len(exams) + len(unparsed) — это и есть проверка «ничего не потеряно».
    subject_rows_seen: int


def parse_exams(grids: Sequence[Grid]) -> ExamParseResult:
    """Разбор всех таблиц одного файла сессии.

    Контекст (группа/программа) тянется carry-forward'ом ЧЕРЕЗ границы таблиц
    и страниц: 13767 стр.2 начинается строкой, у которой пусты и «№ группы»,
    и «Направление» — это продолжение программы с предыдущей страницы.
    """
    exams: list[ParsedExam] = []
    unparsed: list[UnparsedFragment] = []
    seen = 0

    # Шапка запоминается ПО ШИРИНЕ сетки, а не «последняя виденная». Страницы
    # без шапки наследуют её с предыдущей только потому, что геометрия колонок
    # совпадает (разведка §4.1.9) — а совпадает она не всегда: у 14049 стр.2
    # разложена на 15 колонок, стр.1 и стр.3 — на 5. Наследование «последней»
    # разметки уводит на стр.3 все колонки на одну роль влево, строки выглядят
    # пустыми, и страница пропадает целиком и молча.
    layouts: dict[int, list[_Column]] = {}
    group_number: str | None = None
    master_program: str | None = None
    direction_raw: str | None = None

    for grid in grids:
        for row in grid.rows():
            if _is_header(row):
                layouts[grid.n_cols] = _layout_from_header(row)
                continue

            layout = layouts.get(grid.n_cols)
            if layout is None:
                raw = " | ".join(c.text.strip() for c in row if c.text.strip())
                if raw:
                    seen += 1
                    unparsed.append(
                        UnparsedFragment(grid.page, raw, "таблица без шапки сессии")
                    )
                continue

            texts = dict(_by_role(row, layout))
            subject_text = texts.get(_Role.SUBJECT, "")
            consult_text = texts.get(_Role.CONSULT, "")
            exam_text = texts.get(_Role.EXAM, "")

            if not (subject_text.strip() or consult_text.strip() or exam_text.strip()):
                continue  # строка-разделитель

            seen += 1
            cell_raw = " | ".join(t for t in (subject_text, consult_text, exam_text) if t)

            group_text = texts.get(_Role.GROUP, "").strip()
            direction_text = _join_lines(texts.get(_Role.DIRECTION, ""))
            if group_text:
                group_number, master_program, direction_raw = group_text, None, None
            if direction_text:
                if _MASTER_PROGRAM.search(direction_text):
                    # У магистров номера группы не существует: страница
                    # отдаёт программу, «№ группы» пуста.
                    group_number, master_program = None, direction_text
                else:
                    direction_raw = direction_text

            if not subject_text:
                unparsed.append(
                    UnparsedFragment(grid.page, cell_raw, "строка без дисциплины")
                )
                continue
            if not (group_number or master_program):
                unparsed.append(
                    UnparsedFragment(grid.page, cell_raw, "дисциплина без группы и программы")
                )
                continue

            subject, teachers = _split_subject_and_teachers(subject_text)
            consultation = _parse_slot(consult_text) if consult_text.strip() else None
            exam_slot = _parse_slot(exam_text) if exam_text.strip() else None

            if consultation is None and exam_slot is None:
                # Ни одной даты — это не экзамен, а пометка в колонке дисциплины
                # (13744 стр.4: одинокое «ВПК»). Пустить её дальше — положить
                # студенту в список экзаменов запись без даты.
                unparsed.append(
                    UnparsedFragment(
                        grid.page, cell_raw, "дисциплина без дат консультации и экзамена"
                    )
                )
                continue

            ambiguous = [
                name
                for name, slot in (("консультации", consultation), ("экзамена", exam_slot))
                if slot is not None and len(slot.dates) > 1
            ]
            if ambiguous:
                unparsed.append(
                    UnparsedFragment(
                        grid.page,
                        cell_raw,
                        f"несколько дат в ячейке {' и '.join(ambiguous)}",
                    )
                )
                continue

            exams.append(
                ParsedExam(
                    group_number=group_number,
                    master_program=master_program,
                    direction_raw=direction_raw,
                    subject=subject,
                    teachers=teachers,
                    consultation=consultation,
                    exam=exam_slot,
                    page=grid.page,
                    cell_raw=cell_raw,
                )
            )

    return ExamParseResult(tuple(exams), tuple(unparsed), seen)


def row_kinds(grids: Sequence[Grid]) -> dict[tuple[int, int], str]:
    """(индекс Grid, строка) → 'header' | 'payload' | 'blank'.

    Нужно слою импорта: он обязан объяснить судьбу КАЖДОЙ ячейки, а
    parse_exams работает построчно и про ячейки наружу ничего не говорит.
    'payload' — строка с нагрузкой, по ней parse_exams выдал ровно один исход
    (ExamEvent или UnparsedFragment); за этим следит его счётчик
    subject_rows_seen, и tests/test_importer.py сверяет одно с другим — иначе
    эти две функции разъедутся молча.
    """
    kinds: dict[tuple[int, int], str] = {}
    layouts: dict[int, list[_Column]] = {}

    for index, grid in enumerate(grids):
        for row in grid.rows():
            if not row:
                continue
            key = (index, row[0].row)
            if _is_header(row):
                layouts[grid.n_cols] = _layout_from_header(row)
                kinds[key] = "header"
                continue

            layout = layouts.get(grid.n_cols)
            if layout is None:
                kinds[key] = (
                    "payload" if any(cell.text.strip() for cell in row) else "blank"
                )
                continue

            texts = dict(_by_role(row, layout))
            payload = any(
                texts.get(role, "").strip()
                for role in (_Role.SUBJECT, _Role.CONSULT, _Role.EXAM)
            )
            kinds[key] = "payload" if payload else "blank"
    return kinds


def _is_header(row: Sequence) -> bool:
    return any(_ROLE_PATTERNS[0][1].search(_flat(c.text)) for c in row)


@dataclass(frozen=True)
class _Column:
    """Колонка шапки: её роль, диапазон колонок и — для PDF — диапазон по x."""

    role: _Role
    col_start: int
    col_end: int
    x0: float | None
    x1: float | None


def _layout_from_header(row: Sequence) -> list[_Column]:
    layout = []
    for cell in row:
        flat = _flat(cell.text)
        for role, pattern in _ROLE_PATTERNS:
            if pattern.search(flat):
                x0, x1 = (cell.bbox[0], cell.bbox[2]) if cell.bbox else (None, None)
                layout.append(_Column(role, cell.col_start, cell.col_end, x0, x1))
                break
    return layout


def _by_role(row: Sequence, layout: list[_Column]):
    """Ячейки строки, разложенные по ролям колонок из шапки.

    Роль — та, с которой ячейка пересекается сильнее всего, и меряется
    пересечение ПО X, а не по номерам колонок. Номера тут врут: 13768 рисует
    часть строк рамками на ~4 pt левее остальных, из-за чего одна и та же
    физическая колонка получает два набора границ, сетка выходит на 12 колонок
    вместо 6, и ячейка (6,7) пересекает по колонкам и «Кол-во студентов», и
    «Наименование дисциплины» — ровно по одной колонке каждую. Ничья по
    колонкам разваливается в тишине: дата консультации уезжает в предмет,
    а экзамен пропадает. По x ничьей нет — 97% против 3%.
    """
    for cell in row:
        best: _Role | None = None
        best_overlap = 0.0
        for column in layout:
            if cell.bbox and column.x0 is not None:
                overlap = min(cell.bbox[2], column.x1) - max(cell.bbox[0], column.x0)
            else:
                # docx: координат нет, колонки честные — меряем по ним.
                overlap = float(
                    min(cell.col_end, column.col_end)
                    - max(cell.col_start, column.col_start)
                    + 1
                )
            if overlap > best_overlap:
                best, best_overlap = column.role, overlap
        if best is not None:
            yield best, cell.text


def _flat(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _join_lines(text: str) -> str:
    """Строки ячейки в одну.

    PDF переносит длинные слова: «Информационно-\\nкоммуникационные». Строка,
    оборванная дефисом, склеивается без пробела — дефис в этих словах
    настоящий, а не мягкий перенос.
    """
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    out = ""
    for line in lines:
        if not out:
            out = line
        elif out.endswith("-"):
            out += line
        else:
            out += " " + line
    return _flat(out)


def _split_subject_and_teachers(text: str) -> tuple[str, tuple[str, ...]]:
    """Дисциплина и преподаватели лежат в одной ячейке.

    Обычно ФИО — с новой строки, но 13984 пишет «Интернет-маркетинг Володин Р.С.»
    в одну строку, так что «последняя строка = преподаватель» врёт. ФИО ищется
    регэкспом хвостом ячейки; нет ФИО («Иностранный язык») — это дыра источника,
    а не ошибка разбора.
    """
    joined = _join_lines(text).lstrip(". ").strip()
    match = _TEACHERS_TAIL.search(joined)
    if match:
        subject = joined[: match.start()].strip(" ,;.")
        if subject:
            return subject, tuple(_FIO.findall(match.group(0)))
    return joined.strip(" ,;"), ()


def _parse_slot(text: str) -> ExamSlot:
    """Ячейка даты → дата, время, форма, аудитория.

    Форма НЕ ищется по списку слов: ЮФУ пишет её как хочет («устный», «устно»,
    «эссе», «письм.тестирование», «Комп. тестиров-е», «компьютерное
    тестирование+ устный»). Вместо списка — вычитание: убираем дату, время и
    место, форма — это всё, что осталось. Пусто осталось — формы нет (и такие
    ячейки в корпусе есть), а не «угадай».
    """
    lines = [line.strip() for line in text.split("\n") if line.strip()]

    room = None
    start = next((i for i, line in enumerate(lines) if _LOCATION.match(line)), None)
    if start is not None:
        room = normalize_room(_flat(" ".join(lines[start:])))
        lines = lines[:start]

    rest = " ".join(lines)
    dates = tuple(
        date(2000 + int(year), int(month), int(day))
        for day, month, year in _DATE.findall(rest)
    )
    rest = _DATE.sub(" ", rest)

    time_start = time_end = None
    span = _TIME_RANGE.search(rest)
    if span:
        time_start = time(int(span.group(1)), int(span.group(2)))
        time_end = time(int(span.group(3)), int(span.group(4)))
        rest = rest[: span.start()] + " " + rest[span.end() :]
    else:
        point = _TIME_SINGLE.search(rest)
        if point:
            time_start = time(int(point.group(1)), int(point.group(2)))
            rest = rest[: point.start()] + " " + rest[point.end() :]

    kind = _flat(rest).strip(" ,;.")
    return ExamSlot(dates, time_start, time_end, kind or None, room, text)
