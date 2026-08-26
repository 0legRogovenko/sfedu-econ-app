"""Слой 4: разбор одной ячейки занятия в набор ParsedLesson.

Форма ячейки: [дата-префикс] предмет (вид) [ФИО...] [аудитория] — и всё это
с опечатками ЮФУ, артефактами извлечения и тремя способами записать одно и то
же. Базовый regex плана берёт 97% ячеек корпуса (1330 из 1383); остальные три
процента разобраны здесь поимённо, потому что каждый из них либо молча портит
данные, либо теряет живое занятие.

Четыре решения, которые выглядят усложнением и таковыми не являются — на
каждое есть падающий тест в tests/test_cells.py:

1. Занятия режутся по КОНЦУ АУДИТОРИИ, а не по '\\n'. В PDF узкая ячейка
   переносит ОДНО занятие на шесть строк ('Кросс-культурный' / 'менеджмент
   (л)/(с)' / 'Костенко Е.П.,' / …). Резать по '\\n' — покрошить одну пару на
   шесть огрызков. Правило «две пары в ячейке через \\n» верно только для docx
   и на PDF ломается.
2. '(л)/(с)' существует — 45 вхождений; ни в плане, ни в разведке его нет.
   Базовый regex такую ячейку МАТЧИТ и молча кладёт '/(с)' в преподавателей.
   Это худший режим отказа: тест зелёный, данные кривые.
3. '(лаб)' существует — 12 вхождений (разведка утверждала, что нет). Значения
   под него в LessonKind нет, поэтому вид едет в kind_raw, а lesson_kind=None.
4. Аудитория жадно тянется до конца строки: 'ауд.Креативное пр-во' — два слова,
   и режущий \\S+ из плана оставил бы от неё 'Креативное'.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import time

from src.models import LessonKind, WeekType
from src.schedule.rooms import normalize_room

# Вид занятия. 'c' — ЛАТИНСКАЯ: опечатка ЮФУ (13498 p10 R9), глазом не видна.
# 'лаб' раньше 'л' — иначе '(лаб)' не соберётся.
_KIND = re.compile(r"\(\s*(лаб|л|с|c)\s*\)(?:\s*/\s*\(\s*(лаб|л|с|c)\s*\))?", re.IGNORECASE)

# Дата-префикс: 'До 17.12', 'С 6.10', '24.12', '08.11,  15.11'.
_DATE_PREFIX = re.compile(
    r"^\s*(До\s*\d\d?\.\d\d|С\s*\d\d?\.\d\d|\d\d?\.\d\d(?:\s*,\s*\d\d?\.\d\d)*)"
)
# Красная помета внутри ячейки: «С 8⁵⁰» PDF извлекает как «С 850». Это
# локальное время начала, не дата и не часть предмета. Точку намеренно не
# принимаем: «С 6.10» в корпусе — дата начала, её разбирает _DATE_PREFIX.
_START_TIME_PREFIX = re.compile(
    r"^\s*С\s*(?:(\d{1,2}):(\d{2})|(\d{1,2})\s*(\d{2}))\b",
    re.IGNORECASE,
)
_MUAM_PREFIX = re.compile(r"^\s*МУАМ\b\s*", re.IGNORECASE)

# Аудитория В КОНЦЕ строки — тянется жадно до конца ('ауд.Креативное пр-во').
_ROOM_TAIL = re.compile(
    r"(?:^|\s|(?<=\.))((?:\bауд|\bа)\.\.?\s*\S.*|Онлайн|онлайн|Moodle|\bГ-\d\S*|\d{3}[А-Яа-я]?)\s*$"
)

# Аудитория как ОГРАНИЧЕННЫЙ токен — только для поиска границы между занятиями.
# Жадный вариант тут не годится: он проглотил бы следующее занятие целиком.
_ROOM_TOKEN = re.compile(
    r"(?:\bауд|\bа)\.\.?\s*"
    r"(?:Креативное\s+пр-во|Креативное|Креат\.пр|Кр\.пр-во|\S+)"
    r"|Онлайн|онлайн|Moodle|\bГ-\d\S*"
)

_WEEK = re.compile(r"\b(Верхняя|Нижняя)\s+неделя\b", re.IGNORECASE)
# В PDF тип недели обычно стоит в начале занятия; иногда перед ним остаётся
# служебное «По выбору:». Якорь защищает инициалы преподавателя «Пуховский В.Н.»
# от ошибочного превращения в верхнюю неделю.
_WEEK_SHORT = re.compile(
    r"^(?P<prefix>По\s+выбору:\s*)?(?P<type>[ВН])\s*\.\s*Н\s*\.\s*",
    re.IGNORECASE,
)
_SUBGROUP = re.compile(r"(\d)\s*п\s*/\s*г", re.IGNORECASE)
# Заглушка «занятий нет»: '…………….', '……..', '.', ',,,,,,'
_PLACEHOLDER = re.compile(r"^[.…,\s·]+$")

REASON_NO_KIND = "нет маркера вида занятия"
REASON_NO_BOUNDARY = "несколько занятий без границ аудиторий — резать наугад нельзя"

_KIND_BY_TOKEN = {"л": LessonKind.LECTURE, "с": LessonKind.SEMINAR}


@dataclass(frozen=True)
class ParsedLesson:
    """Одно занятие. Всё *_raw — как в источнике, нормализацией занимается
    ручной словарь (фаззи-матчинг предметов ЗАПРЕЩЁН: 'Бух. учет и фин. анализ'
    и 'Бух.учет и экон. анализ' — вероятно РАЗНЫЕ дисциплины)."""

    subject: str
    kind_raw: str | None  # 'л' | 'с' | 'лаб' | 'л/с' — как записал ЮФУ
    lesson_kind: LessonKind | None  # None, если значения в модели нет
    teachers: tuple[str, ...]  # () — ФИО нет В ИСТОЧНИКЕ (8.1% ячеек)
    room: str | None  # None — аудитории нет В ИСТОЧНИКЕ (9.3% ячеек)
    date_constraint_raw: str | None  # 'До 17.12' / '08.11, 15.11'
    subgroup: int | None  # только из текстовой метки 'Nп/г'
    week_type: WeekType | None  # None = каждую неделю (ОСНОВНОЙ случай)
    # Уточнение «С 8:50» внутри предметной ячейки. None — брать начало строки.
    starts_at_override: time | None
    cell_raw: str  # исходный текст ячейки целиком, ВСЕГДА


@dataclass(frozen=True)
class CellParse:
    """Результат разбора ячейки.

    reason is None и lessons пуст и is_placeholder — «занятий нет», всё честно.
    reason not None — ячейка идёт в UnparsedCell с этой причиной.
    """

    lessons: tuple[ParsedLesson, ...]
    reason: str | None
    is_placeholder: bool = False


def is_placeholder(text: str) -> bool:
    """'…………….' — непустой текст, означающий «занятий нет»."""
    return bool(text.strip()) and bool(_PLACEHOLDER.match(text.strip()))


def _normalise(text: str) -> str:
    """Схлопывает переносы и пробелы. Перенос строки в ячейке — это ВЁРСТКА,
    а не разделитель занятий (см. пункт 1 в докстринге модуля)."""
    return " ".join(text.split())


def split_lessons(text: str) -> list[str] | None:
    """Режет ячейку на отдельные занятия. None — граница не определяется.

    Занятий столько же, сколько маркеров вида. Граница между соседними — конец
    аудитории первого из них: 'Иностранный язык (с) Онлайн | Русский язык (с)…'.
    Аудитории между маркерами нет (списки курсов по выбору в блоках МУАМ) —
    честный None: разрежешь наугад — студент придёт не на ту пару.
    """
    flat = _normalise(text)
    marks = list(_KIND.finditer(flat))
    if len(marks) <= 1:
        return [flat]

    # В блоке МУАМ факультет перечисляет дисциплины без ФИО и аудиторий:
    # «МУАМ Предмет A (л) Предмет B (л)». Здесь конец каждого маркера вида —
    # однозначная граница, потому что после последнего маркера хвоста нет.
    # Общее правило не расширяем: без явного заголовка тот же текст остаётся
    # неоднозначным (между маркерами могло быть ФИО предыдущей пары).
    muam = _MUAM_PREFIX.match(flat)
    if muam:
        parts: list[str] = []
        start = muam.end()
        for mark in marks:
            subject = flat[start : mark.end()].strip()
            if not subject:
                return None
            parts.append(f"МУАМ — {subject}")
            start = mark.end()
        if not flat[start:].strip():
            return parts
        return None

    parts: list[str] = []
    start = 0
    for current, following in zip(marks, marks[1:]):
        room = None
        for candidate in _ROOM_TOKEN.finditer(flat, current.end()):
            if candidate.end() > following.start():
                break
            room = candidate
        if room is None:
            return None
        parts.append(flat[start : room.end()].strip())
        start = room.end()
    parts.append(flat[start:].strip())
    return parts


def _kind_of(match: re.Match[str]) -> tuple[str, LessonKind | None]:
    def token(value: str) -> str:
        # латинская c → кириллическая с: опечатка ЮФУ, не отдельный вид
        return value.lower().replace("c", "с")

    first = token(match.group(1))
    second = match.group(2)
    raw = f"{first}/{token(second)}" if second else first
    return raw, _KIND_BY_TOKEN.get(raw)


def parse_lesson(text: str, cell_raw: str) -> ParsedLesson | None:
    """Одно занятие из уже нарезанного куска. None — вида занятия нет."""
    flat = _normalise(text)

    week_type = None
    week = _WEEK.search(flat)
    if week:
        week_type = WeekType.UPPER if week.group(1).lower() == "верхняя" else WeekType.LOWER
        flat = (flat[: week.start()] + " " + flat[week.end() :]).strip()

    short_week = _WEEK_SHORT.match(flat)
    if short_week:
        week_type = WeekType.UPPER if short_week.group("type").lower() == "в" else WeekType.LOWER
        prefix = short_week.group("prefix") or ""
        flat = f"{prefix}{flat[short_week.end():]}".strip()

    subgroup = None
    label = _SUBGROUP.search(flat)
    if label:
        subgroup = int(label.group(1))
        flat = (flat[: label.start()] + " " + flat[label.end() :]).strip()

    kind = _KIND.search(flat)
    if kind is None:
        return None
    kind_raw, lesson_kind = _kind_of(kind)

    head, tail = flat[: kind.start()], flat[kind.end() :]

    starts_at_override = None
    start_time = _START_TIME_PREFIX.match(head)
    if start_time:
        hour_text = start_time.group(1) or start_time.group(3)
        minute_text = start_time.group(2) or start_time.group(4)
        hour, minute = int(hour_text), int(minute_text)
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            starts_at_override = time(hour, minute)
            head = head[start_time.end() :]

    date_constraint_raw = None
    date = _DATE_PREFIX.match(head)
    if date:
        date_constraint_raw = date.group(1)
        head = head[date.end() :]

    # ведущая точка/мусор перед названием ('. История России (с) …')
    subject = head.strip().lstrip(".").strip()

    room = None
    tail = tail.strip()
    room_match = _ROOM_TAIL.search(tail)
    if room_match:
        room = normalize_room(room_match.group(1))
        tail = tail[: room_match.start(1)].strip()

    teachers = tuple(part.strip() for part in tail.split(",") if part.strip())

    if not subject:
        return None

    return ParsedLesson(
        subject=subject,
        kind_raw=kind_raw,
        lesson_kind=lesson_kind,
        teachers=teachers,
        room=room,
        date_constraint_raw=date_constraint_raw,
        subgroup=subgroup,
        week_type=week_type,
        starts_at_override=starts_at_override,
        cell_raw=cell_raw,
    )


def parse_cell(text: str) -> CellParse:
    """Разбирает ячейку целиком. Ничего не теряет молча: всё, что не легло в
    ParsedLesson, возвращается с внятной для админа причиной."""
    if is_placeholder(text):
        return CellParse(lessons=(), reason=None, is_placeholder=True)

    parts = split_lessons(text)
    if parts is None:
        return CellParse(lessons=(), reason=REASON_NO_BOUNDARY)

    lessons = []
    for part in parts:
        lesson = parse_lesson(part, cell_raw=text)
        if lesson is None:
            return CellParse(lessons=(), reason=REASON_NO_KIND)
        lessons.append(lesson)

    if not lessons:
        return CellParse(lessons=(), reason=REASON_NO_KIND)
    return CellParse(lessons=tuple(lessons), reason=None)
