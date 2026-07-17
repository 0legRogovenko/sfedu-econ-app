"""pdf → Grid. pdfplumber find_tables(), .rows[i].cells, колонки через x-границы.

Три вещи, которые тут выглядят усложнением и таковыми не являются. Каждая
куплена разбором настоящих файлов ЮФУ — прежде чем «упрощать», прочтите
tests/test_grid_pdf.py, там на каждую есть падающий тест.

1. Только `.rows[i].cells`, НИКОГДА `extract_table()`. Последний схлопывает
   объединённую ячейку в левую колонку, а в остальные кладёт None: ширина
   занятия теряется, а вместе с ней — то, каким группам оно принадлежит.
2. Никакого постраничного `extract_text()`. Имя дня недели повёрнуто на 90°,
   и в поток оно попадает как 'К И Н Ь Л Е Д Е Н О П' («ПОНЕДЕЛЬНИК» задом
   наперёд), перемешиваясь с занятиями. Текст читается только по ячейкам.
3. Символ принадлежит ячейке по СВОЕМУ ЦЕНТРУ, а не по пересечению bbox.
   Время в шапке набрано надстрочными минутами (8⁵⁰-9³⁵); надстрочные минуты
   следующей строки физически заезжают в bbox предыдущей ячейки, и pdfplumber
   crop() честно их подхватывает — отсюда мусор '850-935\\n50 35'. Заодно
   crop() режет символ на границе колонки, и extract_text() вставляет пробел
   внутрь слова: '13.0 1.26', 'М агистерская'.
"""

from __future__ import annotations

import io
from pathlib import Path

import pdfplumber
from pdfplumber.utils import extract_text as chars_to_text

from src.schedule.grid import BBox, Cell, Grid

# Границы колонок в пределах одной таблицы pdfplumber отдаёт без дрожания
# (минимальный зазор по всему корпусу — 3.96 pt), так что допуск нужен только
# как страховка от будущих файлов.
_SNAP = 1.0


def _snap(value: float, bounds: list[float]) -> int:
    """Индекс ближайшей границы колонки."""
    best = min(range(len(bounds)), key=lambda i: abs(bounds[i] - value))
    return best


def _column_bounds(table) -> list[float]:
    """x-границы колонок таблицы — из самих ячеек.

    table.columns для этого не годится: pdfplumber отдаёт там перекрывающиеся
    диапазоны (в 13470 стр.2 «колонка» 2 тянется на всю таблицу), и индекс
    ячейки в row.cells по ним не восстанавливается.
    """
    values: list[float] = []
    for row in table.rows:
        for cell in row.cells:
            if cell is None:
                continue
            values.extend((cell[0], cell[2]))

    bounds: list[float] = []
    for value in sorted(values):
        if not bounds or value - bounds[-1] > _SNAP:
            bounds.append(value)
    return bounds


def _is_inside(inner: BBox, outer: BBox, tol: float = 1.0) -> bool:
    return (
        inner[0] >= outer[0] - tol
        and inner[1] >= outer[1] - tol
        and inner[2] <= outer[2] + tol
        and inner[3] <= outer[3] + tol
    )


def _top_level_tables(tables: list) -> list:
    """Отбрасывает таблицы, вложенные в другую таблицу страницы.

    pdfplumber иногда видит внутри ячейки с рамкой отдельную «таблицу»: её
    содержимое уже есть в родителе, и оставь мы её — ячейки задвоятся, а сверка
    «ни одна ячейка не потеряна» на слое importer начнёт врать. Соседние
    (не вложенные) таблицы — другое дело: на 14058 стр.3 это настоящие таблицы
    экзаменов, и брать find_tables()[0] значило бы потерять две из трёх.
    """
    return [
        table
        for table in tables
        if not any(
            other is not table and _is_inside(table.bbox, other.bbox)
            for other in tables
        )
    ]


def _cell_text(page, bbox: BBox) -> str:
    x0, top, x1, bottom = bbox
    chars = [
        char
        for char in page.chars
        if x0 <= (char["x0"] + char["x1"]) / 2 <= x1
        and top <= (char["top"] + char["bottom"]) / 2 <= bottom
    ]
    return chars_to_text(chars) if chars else ""


def _drop_nested(boxes: list[BBox]) -> list[BBox]:
    """Убирает ячейки, целиком лежащие внутри другой ячейки той же строки.

    В 13471 стр.11 занятие нарисовано дважды: внешним прямоугольником ячейки и
    внутренним (рамка вокруг текста). Оба приходят из .cells с ОДНИМ И ТЕМ ЖЕ
    текстом, но разной шириной — то есть с разной привязкой к группам. Внешний
    совпадает по x с соседними строками, он и настоящий.
    """
    return [
        box
        for box in boxes
        if not any(
            other is not box and _is_inside(box, other) and not _is_inside(other, box)
            for other in boxes
        )
    ]


def _table_to_grid(page, table, table_index: int) -> Grid:
    bounds = _column_bounds(table)
    cells: list[Cell] = []

    for row_index, row in enumerate(table.rows):
        found: list[Cell] = []
        for cell in _drop_nested([c for c in row.cells if c is not None]):
            col_start = _snap(cell[0], bounds)
            col_end = _snap(cell[2], bounds) - 1
            if col_end < col_start:  # схлопнутая по x ячейка — колонок не занимает
                continue
            found.append(
                Cell(
                    row=row_index,
                    col_start=col_start,
                    col_end=col_end,
                    text=_cell_text(page, cell),
                    bbox=(cell[0], cell[1], cell[2], cell[3]),
                )
            )
        found.sort(key=lambda c: c.col_start)
        cells.extend(found)

    return Grid(
        cells=tuple(cells),
        n_cols=max(len(bounds) - 1, 0),
        table_index=table_index,
        page=page.page_number,
        col_bounds=tuple(bounds),
    )


def extract_pdf(source: str | Path | bytes) -> list[Grid]:
    """Все таблицы документа, по одному Grid на таблицу.

    Страницы нумеруются с единицы. Страница без таблиц (в корпусе такая одна —
    пустая концевая) просто не даёт Grid.
    """
    stream = io.BytesIO(source) if isinstance(source, bytes) else Path(source)
    grids: list[Grid] = []
    with pdfplumber.open(stream) as pdf:
        for page in pdf.pages:
            tables = _top_level_tables(page.find_tables())
            for table_index, table in enumerate(tables):
                grids.append(_table_to_grid(page, table, table_index))
    return grids
