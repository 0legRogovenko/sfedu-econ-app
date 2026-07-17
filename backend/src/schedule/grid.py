"""Grid — общая абстракция таблицы, единая для docx и PDF.

Оба формата ЮФУ дают одно и то же: прямоугольную сетку с объединёнными
ячейками, где колонка задаётся КООРДИНАТОЙ, а не порядковым номером ячейки
в строке. Всё, что выше слоя извлечения (structure, cells, exams, importer),
работает только с этим типом и не знает, docx там был или PDF.

Инвариант границы: Cell несёт col_start/col_end, а не индекс. Занятие
привязывается к группе пересечением диапазонов колонок — единственный способ,
работающий и для лекции на поток (одна ячейка на 6 групп), и для ячейки,
залезшей на границу двух групп.

Соглашение: col_end ВКЛЮЧИТЕЛЬНО (последняя занятая колонка). Ячейка шириной
в одну колонку имеет col_start == col_end. Чтобы этим не приходилось помнить,
арифметика диапазонов спрятана в columns()/overlaps()/covers() — пользуйтесь
ими, а не сравнением полей руками.
"""

from __future__ import annotations

from dataclasses import dataclass

# (x0, top, x1, bottom) в координатах страницы PDF. У docx координат нет.
BBox = tuple[float, float, float, float]


@dataclass(frozen=True)
class Cell:
    """Одна ячейка таблицы.

    row        — номер строки в таблице, с нуля.
    col_start  — первая занятая колонка.
    col_end    — последняя занятая колонка, ВКЛЮЧИТЕЛЬНО.
    text       — текст как в источнике: абзацы через \\n, внутренние пробелы
                 не тронуты (уходит в Lesson.cell_raw и в UnparsedCell.raw_text).
    bbox       — координаты для PDF; None для docx.
    """

    row: int
    col_start: int
    col_end: int
    text: str
    bbox: BBox | None = None

    def __post_init__(self) -> None:
        if self.col_end < self.col_start:
            raise ValueError(f"col_end < col_start: {self.col_start}..{self.col_end}")

    @property
    def col_span(self) -> int:
        """Сколько колонок занимает ячейка."""
        return self.col_end - self.col_start + 1

    @property
    def is_empty(self) -> bool:
        """Пустая ячейка. Внимание: '…………….' («занятий нет») — НЕ пустая,
        это непустой текст, и он обязан дойти до слоя разбора."""
        return not self.text.strip()

    def columns(self) -> range:
        return range(self.col_start, self.col_end + 1)

    def overlaps(self, col_start: int, col_end: int) -> bool:
        """Пересекается ли ячейка с диапазоном колонок хотя бы одной колонкой."""
        return self.col_start <= col_end and col_start <= self.col_end

    def covers(self, col_start: int, col_end: int) -> bool:
        """Накрывает ли ячейка диапазон целиком.

        overlaps, но не covers — ячейка задела группу частично: это подгруппа
        либо занятие внахлёст границ групп (решает слой structure).
        """
        return self.col_start <= col_start and col_end <= self.col_end


@dataclass(frozen=True)
class Grid:
    """Одна таблица: docx — таблица документа, PDF — таблица на странице.

    cells       — все ячейки, упорядоченные (row, col_start). Пустые ячейки
                  тоже здесь: строка-разделитель = строка, где все ячейки пусты.
    n_cols      — ширина сетки в колонках.
    table_index — номер таблицы: в документе (docx) или на странице (PDF).
    page        — страница PDF, с единицы; None для docx.
    col_bounds  — x-границы колонок для PDF, len == n_cols + 1; None для docx.
    """

    cells: tuple[Cell, ...]
    n_cols: int
    table_index: int
    page: int | None = None
    col_bounds: tuple[float, ...] | None = None

    @property
    def n_rows(self) -> int:
        return max((c.row for c in self.cells), default=-1) + 1

    def row(self, index: int) -> list[Cell]:
        """Ячейки строки слева направо."""
        return [c for c in self.cells if c.row == index]

    def rows(self) -> list[list[Cell]]:
        return [self.row(i) for i in range(self.n_rows)]

    def cell_at(self, row: int, col: int) -> Cell | None:
        """Ячейка, накрывающая колонку col в строке row.

        Для любой колонки внутри объединения вернётся одна и та же ячейка.
        None — в этой строке колонка не покрыта (в PDF так выглядит вертикальное
        объединение: ячейка есть только в своей первой строке).
        """
        for cell in self.cells:
            if cell.row == row and cell.col_start <= col <= cell.col_end:
                return cell
        return None
