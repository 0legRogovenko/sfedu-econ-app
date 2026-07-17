"""docx → Grid. Тесты против настоящих файлов ЮФУ из tests/fixtures/schedule/.

Синтетический docx тут бесполезен: вся ценность слоя — в том, что он переживает
реальную разметку ЮФУ (gridSpan, vMerge, ячейки внахлёст границ групп).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.schedule.extract_docx import extract_docx
from src.schedule.grid import Cell, Grid

FIXTURES = Path(__file__).parent / "fixtures" / "schedule"


@pytest.fixture(scope="module")
def grids_13469() -> list[Grid]:
    return extract_docx(FIXTURES / "13469.docx")


@pytest.fixture(scope="module")
def grids_13821() -> list[Grid]:
    return extract_docx(FIXTURES / "13821.docx")


def test_extract_docx_returns_grid_per_table(grids_13469):
    # 13469 — 5 таблиц: календарь недель (4 колонки), три сетки по 8
    # и таблица 4 с другой схемой (6 колонок, разовые занятия по датам).
    assert len(grids_13469) == 5
    assert [g.n_cols for g in grids_13469] == [4, 8, 8, 6, 8]
    assert [g.table_index for g in grids_13469] == [0, 1, 2, 3, 4]


def test_lecture_with_gridspan_is_one_cell_spanning_all_groups(grids_13469):
    """ГЛАВНЫЙ тест слоя: колонка ячейки ≠ её индекс.

    13469.docx таблица 2, строка с лекцией на поток: один <tc> с gridSpan=6.
    Наивный парсер, считающий колонку по индексу tc, увидит здесь колонку 2 и
    припишет лекцию только группе 1.2 — а она у всего потока. Курсор обязан
    считаться по сумме gridSpan предыдущих tc.
    """
    grid = grids_13469[1]  # таблица 2
    row = [c for c in grid.row(11) if not c.is_empty]

    lecture = [c for c in row if "История России (л)" in c.text]
    assert len(lecture) == 1, "лекция на поток — ОДНА ячейка, а не шесть"
    cell = lecture[0]

    assert (cell.col_start, cell.col_end) == (2, 7)
    assert cell.col_span == 6, "не одна колонка с col=2 — ячейка шириной в 6 колонок"
    assert cell.columns() == range(2, 8)


def test_lecture_cell_overlaps_every_group_column(grids_13469):
    """Проверка ради downstream: по col_start/col_end лекция находится у всех 6 групп."""
    grid = grids_13469[1]
    groups = {
        c.text.strip(): (c.col_start, c.col_end)
        for c in grid.row(1)
        if c.text.strip().startswith("Группа")
    }
    assert groups == {
        "Группа 1.2": (2, 2),
        "Группа 1.3": (3, 3),
        "Группа 1.4": (4, 4),
        "Группа 1.5": (5, 5),
        "Группа 1.6": (6, 6),
        "Группа 1.1": (7, 7),
    }

    lecture = next(c for c in grid.row(11) if "История России (л)" in c.text)
    assert all(lecture.overlaps(*rng) for rng in groups.values())


def test_straddling_cells_keep_their_real_column_ranges(grids_13821):
    """13821 T5 R23 — ячейка, залезающая на границу двух групп.

    'Бух. учет' занимает хвост группы 2.3 (4–8) и всю группу 2.4 (9–10).
    Слой 2 обязан отдать честный диапазон 6–10; разбираться, чья это пара,
    будет слой structure.
    """
    grid = grids_13821[4]  # T5
    row = {(c.col_start, c.col_end): c.text for c in grid.row(23) if not c.is_empty}

    assert (4, 5) in row and "Анализ данных" in row[(4, 5)]
    assert (6, 10) in row and "Бух. учет" in row[(6, 10)]

    groups = {
        c.text.strip(): (c.col_start, c.col_end)
        for c in grid.row(1)
        if c.text.strip().startswith("Группа")
    }
    assert groups["Группа 2.3"] == (4, 8)
    assert groups["Группа 2.4"] == (9, 10)

    buh = next(c for c in grid.row(23) if "Бух. учет" in c.text)
    assert buh.overlaps(*groups["Группа 2.3"])
    assert buh.overlaps(*groups["Группа 2.4"])
    assert not buh.covers(*groups["Группа 2.3"]), "2.3 задета лишь частично — подгруппа"
    assert buh.covers(*groups["Группа 2.4"])


def test_header_rows_are_not_aligned_and_that_is_expected(grids_13821):
    """Шапка направлений (R0) съехала относительно шапки групп (R1) — берём R1.

    Фиксируем факт в тесте: 'Экономика' = 2–11, но группа 2.5 занимает 11–12.
    Маппинг группа→направление из XML строго не выводится.
    """
    grid = grids_13821[4]
    econ = next(c for c in grid.row(0) if c.text.strip() == "Экономика")
    assert (econ.col_start, econ.col_end) == (2, 11)

    g25 = next(c for c in grid.row(1) if c.text.strip() == "Группа 2.5")
    assert (g25.col_start, g25.col_end) == (11, 12)
    assert econ.overlaps(*(g25.col_start, g25.col_end))
    assert not econ.covers(g25.col_start, g25.col_end)


def test_paragraphs_inside_cell_joined_with_newline(grids_13469):
    """Два параллельных занятия в одной ячейке разделены \\n, а не склеены.

    В XML это два <w:p>; без явного join получится
    'Иностранный язык (с) ОнлайнРусский язык…' и слой 4 разберёт мусор.
    """
    grid = grids_13469[1]
    cell = next(c for c in grid.row(2) if "Иностранный язык" in c.text)
    lines = cell.text.split("\n")
    assert len(lines) == 2
    assert lines[0] == "Иностранный язык (с) Онлайн"
    assert lines[1].startswith("Русский язык для иностранных студентов (с)")
    # пробелы внутри строки не схлопываем: text уходит в cell_raw как есть,
    # нормализацией занимается слой разбора ячейки
    assert "Груданова И.Ю." in lines[1] and "ауд.222" in lines[1]


def test_vmerge_continue_yields_empty_cell_in_day_column(grids_13469):
    """vMerge continue — это ячейка с пустым текстом, а не отсутствие ячейки.

    Слой structure тянет день carry-forward'ом именно по пустоте (цепочка
    vMerge в 13821 обрывается раньше последнего занятия — на неё нельзя опираться).
    """
    grid = grids_13469[1]
    monday = grid.cell_at(row=2, col=0)
    assert monday is not None and monday.text.strip() == "ПОНЕДЕЛЬНИК"

    carried = grid.cell_at(row=3, col=0)
    assert carried is not None
    assert carried.is_empty


def test_separator_row_has_all_cells_empty(grids_13469):
    grid = grids_13469[1]
    assert all(c.is_empty for c in grid.row(5)), "R5 — строка-разделитель"
    assert not all(c.is_empty for c in grid.row(6))


def test_cell_at_resolves_column_inside_a_span(grids_13469):
    """cell_at по любой колонке внутри объединения отдаёт ту же ячейку."""
    grid = grids_13469[1]
    cells = {grid.cell_at(row=11, col=col) for col in range(2, 8)}
    assert len(cells) == 1
    assert "История России (л)" in next(iter(cells)).text


def test_docx_cells_have_no_bbox_but_grid_is_still_uniform(grids_13469):
    """У docx нет координат — bbox None. Слой выше обязан жить и без него."""
    grid = grids_13469[1]
    assert all(c.bbox is None for c in grid.cells)
    assert grid.col_bounds is None
    assert grid.page is None


def test_extract_docx_accepts_bytes(grids_13469):
    """fetch.py отдаёт тело файла в памяти — путь на диск не обязателен."""
    data = (FIXTURES / "13469.docx").read_bytes()
    assert [g.n_cols for g in extract_docx(data)] == [g.n_cols for g in grids_13469]


def test_exam_docx_is_a_plain_grid_too(grids_13469):
    """13984 — сессия, другая схема, но тот же Grid: слой 2 не знает о типах."""
    grids = extract_docx(FIXTURES / "13984.docx")
    assert len(grids) == 1
    assert grids[0].n_cols == 6
    # в шапке ЮФУ переносит слова внутри ячейки: 'Дата\nэкзамена'
    header = [" ".join(c.text.split()) for c in grids[0].row(0)]
    assert header == [
        "№ группы",
        "Направление / профиль",
        "Кол-во студентов",
        "Наименование дисциплины",
        "Дата консультации",
        "Дата экзамена",
    ]


def test_cell_is_frozen():
    cell = Cell(row=0, col_start=0, col_end=0, text="x")
    with pytest.raises(Exception):
        cell.text = "y"  # type: ignore[misc]
