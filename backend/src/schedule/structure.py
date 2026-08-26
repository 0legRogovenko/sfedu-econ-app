"""Слой 3: скелет расписания — шапка, дни, время → номер пары, привязка к группе.

Работает только с Grid и не знает, docx там был или PDF.

Четыре правила, каждое из которых куплено разбором корпуса и противоречит
«очевидному» — на каждое есть падающий тест в tests/test_structure.py:

1. Строка групп ищется ПО СОДЕРЖИМОМУ ('Группа N.M'), а не по индексу. План
   говорит «шапка в R1» — это факт про docx; в PDF она уезжает в R2…R6
   (13470 p2 → R6), потому что названия направлений размазаны по R0–R3.
2. Колонка времени ищется ПО СОДЕРЖИМОМУ, а не «колонка 1». У магистров день
   лежит в 0–5, время в 6, занятия в 7 (13830 p14). Жёсткая единица разложила
   бы 35% корпуса по пустым местам.
3. День опознаётся по МУЛЬТИМНОЖЕСТВУ букв. В PDF имя дня повёрнуто на 90°, и
   порядок символов не просто обратный, а случайный ('РД А СЕ' = СРЕДА).
4. Время → пара при точном совпадении с сеткой (половинами '800-845 850-935'
   или слитно '800-935') ЛИБО когда это блок в 3+ ак. часа ('800- 1025',
   'полторы пары'). Блок — легитимное занятие в несколько пар подряд (языки по
   вторникам, вечерние окна магистров): номер пары берём по началу, границы
   отдаём реальные. Одинокие половины, окна, съехавшие на полпары мимо границы,
   и склейку всей колонки времени по-прежнему НЕ угадываем — они в UnparsedCell.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from datetime import time

from src.models import EducationLevel, WeekType
from src.schedule.grid import Cell, Grid

WEEKDAYS = ("ПОНЕДЕЛЬНИК", "ВТОРНИК", "СРЕДА", "ЧЕТВЕРГ", "ПЯТНИЦА", "СУББОТА")

# Сетка пар ЮФУ: половины каждой пары. Пара 7 — вечерняя, у магистров она
# рабочая (160 ячеек), хотя в плане перечислены только шесть.
PAIR_HALVES: dict[int, tuple[tuple[int, int], tuple[int, int]]] = {
    1: ((800, 845), (850, 935)),
    2: ((950, 1035), (1040, 1125)),
    3: ((1155, 1240), (1245, 1330)),
    4: ((1345, 1430), (1435, 1520)),
    5: ((1550, 1635), (1640, 1725)),
    6: ((1735, 1820), (1825, 1910)),
    7: ((1915, 2000), (2005, 2050)),
}

_SLOT = re.compile(r"\b(\d{3,4})\s*-+\s*(\d{3,4})\b")

# Начало первой половины каждой пары в минутах от полуночи — «сетка» для
# привязки блока по времени начала.
PAIR_STARTS: dict[int, int] = {
    pair: (halves[0][0] // 100) * 60 + halves[0][0] % 100
    for pair, halves in PAIR_HALVES.items()
}
# Блок в 3 ак. часа — минимум 135 минут (3 × 45). Короче — это одна пара или её
# половина, съехавшая мимо границы: угадывать нельзя. Длиннее 240 минут —
# склейка всей колонки времени в одну строку ('800-1725'), тоже не занятие.
_BLOCK_MIN_SPAN = 135
_BLOCK_MAX_SPAN = 240
_GROUP = re.compile(r"Группа\s*(\d+\.\d+)", re.IGNORECASE)
_MASTER_PROGRAM = re.compile(r"Магистерск\w*\s*программ\w*\s*«(.+?)»", re.IGNORECASE)
# 13471 p8: '«ИНФОРМАЦИОННЫЕ ТЕХНОЛОГИИ И БИЗНЕС-АНАЛИТИКА» 3.7' — номер группы
# вшит в заголовок программы, строки 'Группа N.M' на странице нет.
_TITLE_WITH_GROUP = re.compile(r"«(.+?)»\s*(\d+\.\d+)")
_COURSE = re.compile(r"(\d)\s*курс", re.IGNORECASE)
_FORM = re.compile(r"Очная\s*форма", re.IGNORECASE)
_WEEK_HEADING = re.compile(r"(ВЕРХНЯЯ|НИЖНЯЯ)\s*НЕДЕЛЯ|НЕДЕЛЯ\s*:\s*(ВЕРХНЯЯ|НИЖНЯЯ)", re.IGNORECASE)

REASON_TIME_OFF_GRID = "время вне сетки пар"
REASON_DAY_UNKNOWN = "день недели не распознан"

_DAY_LETTERS = {day: Counter(day) for day in WEEKDAYS}
_TIME_HEADER_LETTERS = Counter("ВРЕМЯ")


def _is_time_header(text: str) -> bool:
    """True для обычного «Время» и повёрнутого PDF-текста «я м е р В»."""
    letters = Counter(re.sub(r"[^А-ЯЁа-яё]", "", text).upper())
    return letters == _TIME_HEADER_LETTERS


def decode_weekday(text: str) -> int | None:
    """Номер дня, 0 = понедельник. None — не день недели.

    Опознание по мультимножеству букв, а не по строке: в PDF имя дня повёрнуто,
    и pdfplumber отдаёт буквы вперемешку ('РД А СЕ', 'Л Е Д Е Н К И Н ОЬ П').
    Наборы букв шести дней различаются однозначно, так что ложных срабатываний
    это не даёт, а порядку символов верить нельзя.
    """
    letters = Counter(re.sub(r"[^А-ЯЁа-яё]", "", text).upper())
    if not letters:
        return None
    for index, day in enumerate(WEEKDAYS):
        if _DAY_LETTERS[day] == letters:
            return index
    return None


def _minutes(hhmm: int) -> int:
    return (hhmm // 100) * 60 + hhmm % 100


def _clean_slots(slots: list[tuple[int, int]]) -> list[tuple[int, int]] | None:
    """Слоты в минутах, если запись корректна: минуты < 60, начало < конца,
    слоты идут по возрастанию без наложений. Иначе None — это артефакт извлечения
    ('1435-152' — обрезанная половина), а не расписание."""
    out: list[tuple[int, int]] = []
    for raw_start, raw_end in slots:
        if raw_start % 100 >= 60 or raw_end % 100 >= 60:
            return None
        start, end = _minutes(raw_start), _minutes(raw_end)
        if end <= start:
            return None
        if out and start < out[-1][1]:
            return None
        out.append((start, end))
    return out


def _block_pair(time_raw: str) -> int | None:
    """Номер пары для блока в 3+ ак. часа. None — это не блок.

    Блок начинается у границы пары (или чуть рядом — '1350' при начале пары
    13:45) и тянется сплошным окном ≥ 135 минут, но не длиннее 240: так
    отсекаются и
    одинокие половины (короче), и склейка всей колонки времени (длиннее). Номер
    пары — ближайшая по времени начала: '800'→1, '1055'→3, '1350'→4.
    """
    slots = _clean_slots([(int(a), int(b)) for a, b in _SLOT.findall(time_raw)])
    if not slots:
        return None
    span = slots[-1][1] - slots[0][0]
    if span < _BLOCK_MIN_SPAN or span > _BLOCK_MAX_SPAN:
        return None
    start = slots[0][0]
    return min(PAIR_STARTS, key=lambda pair: abs(PAIR_STARTS[pair] - start))


def _straddle_pair(slots: list[tuple[int, int]]) -> int | None:
    """Пара для сдвинутого блока в 2 ак. часа: ВТОРАЯ половина пары N + ПЕРВАЯ
    половина пары N+1 ('1040-1125 1155-1240' — языковой понедельник 3 курса,
    13471 p2: так записан весь день у всех групп). None — не этот случай.

    Это НЕ «угадывание съехавшего окна»: обе половины обязаны дословно
    совпадать с сеткой, а пары — быть соседними. Одинокие половины (1 слот),
    битые артефакты (не из сетки) и произвольные сдвиги сюда не проходят.
    Студент времени не перепутает: приложение показывает реальные границы из
    parse_time_bounds (10:40–12:40), номер пары — только ключ слота/сортировки.
    """
    if len(slots) != 2:
        return None
    for pair, halves in PAIR_HALVES.items():
        nxt = PAIR_HALVES.get(pair + 1)
        if nxt is None:
            break
        if slots == [halves[1], nxt[0]]:
            return pair
    return None


def parse_pair_number(time_raw: str) -> int | None:
    """Номер пары по тексту ячейки времени. None — время вне сетки.

    Точное совпадение с сеткой пар: половинами ('800-845 850-935') или слитно
    ('800-935'). Если не совпало — это может быть сдвинутый блок в 2 ак. часа
    (вторая половина пары N + первая половина N+1: языковые дни) или блок в
    3+ ак. часа (иняз по вторникам, вечерние окна магистров): тогда пара по
    времени начала. Всё прочее — одинокие половины, съехавшие мимо границы
    окна, битые артефакты — честный None: пара из них не выводится.
    """
    slots = [(int(a), int(b)) for a, b in _SLOT.findall(time_raw)]
    if not slots:
        return None
    for pair, (first, second) in PAIR_HALVES.items():
        if slots == [first, second]:
            return pair
        if slots == [(first[0], second[1])]:
            return pair
    straddle = _straddle_pair(slots)
    if straddle is not None:
        return straddle
    return _block_pair(time_raw)


def parse_time_bounds(time_raw: str) -> tuple[time, time] | None:
    """Реальные границы занятия: начало первого слота, конец последнего.

    Для обычной пары это те же 08:00–09:35, что дают внешние края её половин;
    для блока — его настоящее окно (08:00–10:25). None — корректных слотов нет.
    Считается ТОЛЬКО когда parse_pair_number уже признал время: иначе граница
    занятия без номера пары бессмысленна.
    """
    slots = _clean_slots([(int(a), int(b)) for a, b in _SLOT.findall(time_raw)])
    if not slots:
        return None
    start, end = slots[0][0], slots[-1][1]
    return time(start // 60, start % 60), time(end // 60, end % 60)


def week_type_from_heading(text: str) -> WeekType | None:
    """Тип недели из заголовка страницы: 'ВЕРХНЯЯ НЕДЕЛЯ' или 'НЕДЕЛЯ: ВЕРХНЯЯ'.

    Оба маркера лежат в тексте страницы ВНЕ таблицы, поэтому Grid их не видит —
    текст сюда приносит importer. Третий способ (маркер внутри ячейки) живёт
    в cells.py.
    """
    match = _WEEK_HEADING.search(text)
    if not match:
        return None
    word = (match.group(1) or match.group(2)).upper()
    return WeekType.UPPER if word == "ВЕРХНЯЯ" else WeekType.LOWER


@dataclass(frozen=True)
class GroupColumn:
    """Диапазон колонок одной группы (бакалавры) или программы (магистры).

    Ровно одно из number/program заполнено: у магистров номера группы НЕТ.
    """

    col_start: int
    col_end: int
    number: str | None = None
    program: str | None = None


@dataclass(frozen=True)
class GridHeader:
    header_row: int  # последняя строка шапки; данные идут ниже
    time_col: int
    groups: tuple[GroupColumn, ...]
    level: EducationLevel
    course: int | None = None


@dataclass(frozen=True)
class RowSlot:
    row: int
    weekday: int | None
    pair_number: int | None
    time_raw: str | None
    is_separator: bool
    reason: str | None = None
    # Реальные границы занятия из ячейки времени: у блока — его окно, у обычной
    # пары — внешние края её половин. None, если пара не распознана.
    starts_at: time | None = None
    ends_at: time | None = None


@dataclass(frozen=True)
class CellPlacement:
    """Ячейка, привязанная к одной группе. subgroup: 0 = вся группа."""

    cell: Cell
    group: GroupColumn
    subgroup: int


def find_time_column(grid: Grid) -> int | None:
    """Колонка времени — та, где больше всего ячеек вида '800-845'."""
    counts = Counter(
        cell.col_start for cell in grid.cells if _SLOT.search(cell.text)
    )
    if not counts:
        return None
    return counts.most_common(1)[0][0]


def _group_row(grid: Grid) -> int | None:
    """Строка с 'Группа N.M'. Берём ту, где таких ячеек больше всего."""
    counts = Counter(cell.row for cell in grid.cells if _GROUP.search(cell.text))
    if not counts:
        return None
    best = max(counts.values())
    return min(row for row, n in counts.items() if n == best)


def parse_header(grid: Grid) -> GridHeader | None:
    """Шапка таблицы. None — шапки нет (страница-продолжение или не расписание).

    Возвращать None, а не выдумывать шапку из первой строки — принципиально:
    13472 p3/p5 продолжают предыдущую страницу, и шапку им обязан выдать
    вызывающий (геометрия колонок совпадает, наследование безопасно).
    """
    time_col = find_time_column(grid)
    if time_col is None:
        return None

    time_header = [
        cell.row
        for cell in grid.cells
        if _is_time_header(cell.text) and cell.col_start == time_col
    ]
    if not time_header:
        return None  # страница-продолжение: колонка времени есть, а шапки нет
    header_row = min(time_header)

    course = None
    for cell in grid.cells:
        if cell.row <= header_row + 2 and _FORM.search(cell.text):
            match = _COURSE.search(cell.text)
            if match:
                course = int(match.group(1))
            header_row = max(header_row, cell.row)

    group_row = _group_row(grid)
    if group_row is not None:
        groups = tuple(
            GroupColumn(
                col_start=cell.col_start,
                col_end=cell.col_end,
                number=_GROUP.search(cell.text).group(1),
            )
            for cell in sorted(grid.cells, key=lambda c: c.col_start)
            if cell.row == group_row and _GROUP.search(cell.text)
        )
        return GridHeader(
            header_row=max(header_row, group_row),
            time_col=time_col,
            groups=groups,
            level=EducationLevel.BACHELOR,
            course=course or _course_from_groups(groups),
        )

    content = [
        cell
        for cell in grid.cells
        if cell.row <= header_row and cell.col_start > time_col and not cell.is_empty
    ]
    if not content:
        return None
    title = min(content, key=lambda c: (c.row, c.col_start))
    span = (time_col + 1, grid.n_cols - 1)

    embedded = _TITLE_WITH_GROUP.search(title.text)
    if embedded:
        return GridHeader(
            header_row=header_row,
            time_col=time_col,
            groups=(GroupColumn(span[0], span[1], number=embedded.group(2)),),
            level=EducationLevel.BACHELOR,
            course=course or int(embedded.group(2).split(".")[0]),
        )

    master = _MASTER_PROGRAM.search(title.text)
    program = master.group(1) if master else " ".join(title.text.split())
    return GridHeader(
        header_row=header_row,
        time_col=time_col,
        groups=(GroupColumn(span[0], span[1], program=program),),
        level=EducationLevel.MASTER,
        course=course,
    )


def _course_from_groups(groups: tuple[GroupColumn, ...]) -> int | None:
    courses = {int(g.number.split(".")[0]) for g in groups if g.number}
    return courses.pop() if len(courses) == 1 else None


def _time_cell_for_row(grid: Grid, row: int, time_col: int) -> Cell | None:
    """Ячейка времени строки, включая доказанное вертикальное объединение.

    В PDF объединённая по высоте ячейка принадлежит только первой строке
    pdfplumber. Наследуем её ниже лишь когда bbox времени геометрически
    накрывает всю текущую строку; по одному только отсутствию времени не
    угадываем, чтобы не протянуть предыдущую пару в новый слот.
    """
    direct = grid.cell_at(row, time_col)
    if direct is not None:
        return direct

    row_boxes = [cell.bbox for cell in grid.row(row) if cell.bbox is not None]
    if not row_boxes:
        return None  # DOCX и строки без геометрии не дают доказательства
    row_top = min(box[1] for box in row_boxes)
    row_bottom = max(box[3] for box in row_boxes)

    candidates = [
        cell
        for cell in grid.cells
        if cell.row < row
        and cell.col_start <= time_col <= cell.col_end
        and cell.bbox is not None
        and _SLOT.search(cell.text)
        and cell.bbox[1] <= row_top + 1.0
        and cell.bbox[3] >= row_bottom - 1.0
    ]
    return max(candidates, key=lambda cell: cell.row, default=None)


def parse_rows(
    grid: Grid,
    header: GridHeader,
    first_row: int | None = None,
    carry_day: int | None = None,
) -> list[RowSlot]:
    """День × пара для каждой строки данных.

    День тянется carry-forward'ом: в 13821 T5 R26 пара есть, а ячейка дня пуста
    и без vMerge — цепочка обрывается раньше последнего занятия, и опираться на
    неё нельзя. Строка-разделитель (ВСЕ ячейки пусты) день не сбрасывает.

    first_row=0 — для страницы-продолжения: своей шапки у неё нет, данные
    начинаются с нулевой строки.

    carry_day — день, унаследованный с предыдущей страницы: в 13472 разрыв
    страницы проходит ПОСРЕДИ дня (p2 кончается 'СРЕДА 800-845', p3 начинается
    '850-935'), и без него первые строки продолжения остались бы без дня.
    """
    start = header.header_row + 1 if first_row is None else first_row
    slots: list[RowSlot] = []
    current_day: int | None = carry_day

    for row in range(start, grid.n_rows):
        cells = grid.row(row)
        if all(cell.is_empty for cell in cells):
            slots.append(RowSlot(row, current_day, None, None, is_separator=True))
            continue

        day_cells = [
            cell for cell in cells if cell.col_start < header.time_col and not cell.is_empty
        ]
        reason = None
        if day_cells:
            # Склеиваем ВСЕ ячейки левее времени: повёрнутое имя дня свободно
            # разъезжается по нескольким колонкам (13497 p2 R2: 'ь л е д е н о П'
            # + 'к и н' = ПОНЕДЕЛЬНИК). Порознь не читается ни одна из них.
            found = decode_weekday(" ".join(cell.text for cell in day_cells))
            if found is None:
                found = next(
                    (d for d in map(decode_weekday, (c.text for c in day_cells))
                     if d is not None),
                    None,
                )
            if found is not None:
                current_day = found
            else:
                # ячейка дня есть, но не читается — тянуть предыдущий день
                # нельзя: он почти наверняка чужой (13830 p14 R16 'у С')
                current_day = None
                reason = REASON_DAY_UNKNOWN

        time_cell = _time_cell_for_row(grid, row, header.time_col)
        time_raw = time_cell.text if time_cell and not time_cell.is_empty else None
        pair = parse_pair_number(time_raw) if time_raw else None
        bounds = parse_time_bounds(time_raw) if pair is not None else None
        if time_raw and pair is None and reason is None:
            reason = REASON_TIME_OFF_GRID
        if current_day is None and reason is None:
            reason = REASON_DAY_UNKNOWN

        slots.append(
            RowSlot(
                row=row,
                weekday=current_day,
                pair_number=pair,
                time_raw=time_raw,
                is_separator=False,
                reason=reason,
                starts_at=bounds[0] if bounds else None,
                ends_at=bounds[1] if bounds else None,
            )
        )
    return slots


# Доля перекрытия, ниже которой ячейка к группе НЕ относится: касание края через
# тонкий столбец-границу (в PDF ячейка семинара заходит на соседнюю колонку на
# ~5 pt из ~115) — это не подгруппа, а артефакт геометрии. Порог считается от
# меньшей из двух ширин (ячейки/группы), чтобы узкая подгруппа осталась значимой.
_MEMBER_FRAC = 0.5
# Доля ГРУППЫ, накрытая ячейкой, выше которой это занятие всей группы (subgroup=0).
# В PDF настоящая ячейка группы смещена на полстолбца-границы и группу «целиком»
# по индексам не накрывает (covers ложен) — по площади же накрывает на ~95%.
_COVER_FRAC = 0.9


def _span_bounds(grid: Grid, col_start: int, col_end: int) -> tuple[float, float]:
    """Внешние x-границы диапазона колонок (PDF) или сами индексы (docx)."""
    if grid.col_bounds is not None:
        return grid.col_bounds[col_start], grid.col_bounds[col_end + 1]
    return float(col_start), float(col_end + 1)


def _cell_span(grid: Grid, cell: Cell) -> tuple[float, float]:
    """x-границы ячейки. В PDF берём реальный bbox (точнее снапнутых колонок),
    в docx — колонки."""
    if grid.col_bounds is not None and cell.bbox is not None:
        return cell.bbox[0], cell.bbox[2]
    return float(cell.col_start), float(cell.col_end + 1)


def _overlap(grid: Grid, cell: Cell, group: GroupColumn) -> tuple[float, float, float]:
    """(перекрытие, ширина ячейки, ширина группы) в общих единицах: pt для PDF,
    колонки для docx."""
    cell_lo, cell_hi = _cell_span(grid, cell)
    group_lo, group_hi = _span_bounds(grid, group.col_start, group.col_end)
    overlap = max(0.0, min(cell_hi, group_hi) - max(cell_lo, group_lo))
    return overlap, cell_hi - cell_lo, group_hi - group_lo


def place_row(grid: Grid, row: int, header: GridHeader) -> list[CellPlacement]:
    """Раскладывает занятия строки по группам.

    Ячейка относится к группе, только если перекрытие ЗНАЧИМО (> половины
    меньшей из ширин) — касание края через тонкий столбец-границу игнорируется,
    иначе сосед подмешивается выдуманной подгруппой (13470 Ср/Чт/Пт).

    Ячейка, накрывающая почти всю группу → занятие всей группы (subgroup=0);
    в PDF настоящая ячейка смещена на полстолбца и по индексам группу «целиком»
    не покрывает, поэтому порог по ПЛОЩАДИ, а не covers() по краям. Значимый, но
    не полный кусок → подгруппа, номер по порядку слева направо. Одна ячейка
    может быть подгруппой одной группы и целым занятием соседней: 13821 T5 R24
    кусок (6,10) — вторая подгруппа 2.3 (4–8) и вся группа 2.4 (9–10).
    """
    cells = sorted(
        (
            cell
            for cell in grid.row(row)
            if cell.col_start > header.time_col and not cell.is_empty
        ),
        key=lambda c: c.col_start,
    )

    placements: list[CellPlacement] = []
    for group in header.groups:
        members = []
        for cell in cells:
            overlap, cell_w, group_w = _overlap(grid, cell, group)
            if overlap > _MEMBER_FRAC * min(cell_w, group_w):
                members.append((cell, overlap >= _COVER_FRAC * group_w))
        pieces = [cell for cell, covers in members if not covers]
        for cell, covers in members:
            subgroup = 0 if covers else pieces.index(cell) + 1
            placements.append(CellPlacement(cell=cell, group=group, subgroup=subgroup))
    return placements
