"""docx → Grid. zipfile + ElementTree, курсор колонок по w:gridSpan.

python-docx не нужен: нам нужны ровно gridSpan, текст и порядок таблиц.
"""

from __future__ import annotations

import io
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from src.schedule.grid import Cell, Grid

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def _cell_text(tc: ET.Element) -> str:
    """Текст ячейки: абзацы и <w:br/> — переносами строк, <w:tab/> — табом.

    Без явного join абзацы склеятся ('…(с) ОнлайнРусский язык…'), и слой разбора
    ячейки увидит два занятия как одно.
    """
    lines: list[str] = []
    for p in tc.findall(f"{W}p"):
        parts: list[str] = []
        for node in p.iter():
            tag = node.tag
            if tag == f"{W}t":
                parts.append(node.text or "")
            elif tag == f"{W}tab":
                parts.append("\t")
            elif tag in (f"{W}br", f"{W}cr"):
                parts.append("\n")
        lines.append("".join(parts))
    return "\n".join(lines)


def _grid_span(tc: ET.Element) -> int:
    pr = tc.find(f"{W}tcPr")
    if pr is None:
        return 1
    span = pr.find(f"{W}gridSpan")
    if span is None:
        return 1
    try:
        return max(1, int(span.get(f"{W}val", "1")))
    except ValueError:
        return 1


def _table_to_grid(tbl: ET.Element, table_index: int) -> Grid:
    cells: list[Cell] = []
    width = 0

    for row_index, tr in enumerate(tbl.findall(f"{W}tr")):
        cursor = 0
        # ВАЖНО: колонка ячейки — это не её индекс среди tc. Лекция на поток —
        # один tc с gridSpan=6; считая по индексу, мы отдали бы её одной группе.
        for tc in tr.findall(f"{W}tc"):
            span = _grid_span(tc)
            cells.append(
                Cell(
                    row=row_index,
                    col_start=cursor,
                    col_end=cursor + span - 1,
                    text=_cell_text(tc),
                )
            )
            cursor += span
        width = max(width, cursor)

    grid_def = tbl.find(f"{W}tblGrid")
    declared = len(grid_def.findall(f"{W}gridCol")) if grid_def is not None else 0
    # объявленная ширина бывает меньше фактической — берём максимум, чтобы
    # ни одна колонка не оказалась за пределами сетки
    return Grid(
        cells=tuple(cells), n_cols=max(width, declared), table_index=table_index
    )


def extract_docx(source: str | Path | bytes) -> list[Grid]:
    """Все таблицы документа, по одному Grid на таблицу, в порядке документа.

    Берутся только таблицы верхнего уровня (прямые дети body); таблица внутри
    ячейки другой таблицы отдельным Grid не станет.
    """
    data = source if isinstance(source, bytes) else Path(source).read_bytes()
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        document = ET.fromstring(archive.read("word/document.xml"))

    body = document.find(f"{W}body")
    if body is None:
        return []
    return [_table_to_grid(tbl, i) for i, tbl in enumerate(body.findall(f"{W}tbl"))]
