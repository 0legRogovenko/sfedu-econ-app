"""pdf → Grid. Тесты против настоящих файлов ЮФУ из tests/fixtures/schedule/.

Часть тестов намеренно вызывает pdfplumber напрямую и показывает, что «простые»
API (extract_table, extract_text) на этих файлах дают неверный результат.
Это не любопытство: без них следующий читатель «упростит» extract_pdf и молча
сломает привязку пар к группам.
"""

from __future__ import annotations

import re
from pathlib import Path

import pdfplumber
import pytest

from src.schedule.extract_pdf import extract_pdf
from src.schedule.grid import Grid

FIXTURES = Path(__file__).parent / "fixtures" / "schedule"


@pytest.fixture(scope="module")
def grids_13470() -> list[Grid]:
    return extract_pdf(FIXTURES / "13470.pdf")


def _page_grid(grids: list[Grid], page: int) -> Grid:
    on_page = [g for g in grids if g.page == page]
    assert len(on_page) == 1, f"на стр.{page} ожидалась одна таблица"
    return on_page[0]


def _groups(grid: Grid) -> dict[str, tuple[int, int]]:
    for row in grid.rows():
        found = {
            c.text.strip(): (c.col_start, c.col_end)
            for c in row
            if c.text.strip().startswith("Группа")
        }
        if found:
            return found
    raise AssertionError("шапка групп не найдена")


def test_pages_are_one_based_and_grid_carries_geometry(grids_13470):
    assert min(g.page for g in grids_13470) == 1
    grid = _page_grid(grids_13470, 2)
    assert grid.page == 2
    # col_bounds — это x-границы колонок; их на одну больше, чем колонок
    assert grid.col_bounds is not None
    assert len(grid.col_bounds) == grid.n_cols + 1
    assert all(c.bbox is not None for c in grid.cells)


def test_row_of_three_cells_binds_to_the_right_groups(grids_13470):
    """ГЛАВНЫЙ тест слоя: привязка к группам держится на геометрии по x.

    13470.pdf стр.2, строка 8: три занятия. Одно накрывает 2.2–2.5, второе — 2.6,
    третье — 2.1. Никакой индекс колонки этого не даёт: диапазоны разной ширины.
    """
    grid = _page_grid(grids_13470, 2)
    groups = _groups(grid)
    assert groups == {
        "Группа 2.2": (2, 2),
        "Группа 2.3": (3, 5),
        "Группа 2.4": (6, 7),
        "Группа 2.5": (8, 10),
        "Группа 2.6": (11, 12),
        "Группа 2.1": (13, 15),
    }

    lessons = [c for c in grid.row(8) if not c.is_empty and c.col_start >= 2]
    assert len(lessons) == 3

    covered = [
        sorted(
            (name for name, rng in groups.items() if cell.overlaps(*rng)),
            key=lambda n: groups[n],
        )
        for cell in lessons
    ]
    assert covered == [
        ["Группа 2.2", "Группа 2.3", "Группа 2.4", "Группа 2.5"],
        ["Группа 2.6"],
        ["Группа 2.1"],
    ]
    assert "Монетарная экономика" in lessons[0].text
    assert "Безопасность" in lessons[1].text
    assert "Теория и практика" in lessons[2].text


def test_lecture_row_covers_all_six_groups(grids_13470):
    grid = _page_grid(grids_13470, 2)
    groups = _groups(grid)
    lecture = next(c for c in grid.row(7) if "Теория и практика управления (л)" in c.text)
    assert all(lecture.covers(*rng) for rng in groups.values())


def test_extract_table_loses_group_binding_therefore_we_use_cells(grids_13470):
    """НЕ ЗАМЕНЯТЬ extract_pdf на extract_table(). Вот почему.

    extract_table() кладёт текст объединённой ячейки в её ЛЕВУЮ колонку, а во все
    остальные — None. Текст при этом не пропадает, и потому подмена выглядит
    безобидной. Теряется ШИРИНА: сколько групп накрыло занятие, из результата
    больше не восстановить, а None не отличить от пустой ячейки.

    Ниже — две строки одной таблицы. В стр.7 лекция у ВСЕХ ШЕСТИ групп, в стр.8
    лекция только у 2.2–2.5 (четыре). После extract_table() обе выглядят
    одинаково: текст в колонке 2 и None дальше. Разница в четыре группы —
    именно та ошибка, которая тихо приведёт студента на чужую пару.
    """
    with pdfplumber.open(FIXTURES / "13470.pdf") as pdf:
        naive = pdf.pages[1].find_tables()[0].extract()

    lecture_all_six = naive[7]
    lecture_four = naive[8]
    assert "Теория и практика управления (л)" in lecture_all_six[2]
    assert "Монетарная экономика" in lecture_four[2]
    # обе — в колонке 2, обе — с None во всех колонках 3..10: неразличимы
    assert lecture_all_six[3:11] == [None] * 8
    assert lecture_four[3:11] == [None] * 8

    # .cells различает их честно: 2..15 против 2..10
    grid = _page_grid(grids_13470, 2)
    wide = next(c for c in grid.row(7) if "Теория и практика управления (л)" in c.text)
    narrow = next(c for c in grid.row(8) if "Монетарная экономика" in c.text)
    assert (wide.col_start, wide.col_end) == (2, 15)
    assert (narrow.col_start, narrow.col_end) == (2, 10)

    groups = _groups(grid)
    assert sum(wide.overlaps(*r) for r in groups.values()) == 6
    assert sum(narrow.overlaps(*r) for r in groups.values()) == 4


def test_extract_text_mixes_rotated_day_name_therefore_we_read_cells(grids_13470):
    """НЕ ЗАМЕНЯТЬ extract_pdf на построчный extract_text(). Вот почему.

    Имя дня недели повёрнуто на 90°, и постраничный extract_text() высыпает его
    в поток по одной букве на строку, вперемешку с занятиями. Плюс занятия
    РАЗНЫХ групп, оказавшиеся на одной высоте, склеиваются в одну строку.
    Читать страницу построчно нельзя — только по ячейкам.
    """
    with pdfplumber.open(FIXTURES / "13470.pdf") as pdf:
        flow = pdf.pages[1].extract_text() or ""

    assert "ПОНЕДЕЛЬНИК" not in flow, "целиком имя дня в потоке не встречается"
    singles = [ln for ln in flow.split("\n") if re.fullmatch(r"[А-Я]", ln.strip())]
    assert len(singles) >= 8, f"повёрнутый день рассыпан по буквам: {singles}"

    # занятия 2.6 и 2.1 слиплись в одну строку — какое чьё, уже не понять
    assert "Безопасность Теория и практика" in flow

    # у нас те же два занятия — разные ячейки с разными диапазонами колонок
    grid = _page_grid(grids_13470, 2)
    groups = _groups(grid)
    bez = next(c for c in grid.row(8) if "Безопасность" in c.text)
    teo = next(c for c in grid.row(8) if "Теория и практика" in c.text)
    assert bez.covers(*groups["Группа 2.6"])
    assert teo.covers(*groups["Группа 2.1"])
    assert not bez.overlaps(*groups["Группа 2.1"])

    # и ни одной буквы повёрнутого дня в ячейках занятий
    assert all(len(ln) > 1 for c in (bez, teo) for ln in c.text.split("\n") if ln.strip())


def test_superscript_of_next_row_does_not_bleed_into_time_cell():
    """Время пишется с надстрочными минутами (8⁵⁰-9³⁵), и надстрочные минуты
    СЛЕДУЮЩЕЙ строки попадают в bbox предыдущей ячейки.

    Отсюда мусор вида '850-935\\n50 35', который ловила разведка. Лечится тем, что
    символ относится к ячейке по своему ЦЕНТРУ, а не по факту пересечения bbox.
    """
    grids = extract_pdf(FIXTURES / "13472.pdf")
    grid = _page_grid(grids, 3)
    times = [grid.cell_at(row=r, col=1) for r in (0, 1, 2)]

    assert times[0].text == "850-935"
    assert times[1].text == "950-1035\n1040-1125"
    assert times[2].text == "1155- 1240\n1245- 1330"
    assert all("50 35" not in c.text for c in times if c)


def test_char_ownership_by_center_also_kills_spurious_spaces():
    """Тот же приём чинит разрывы внутри слов: crop() режет символ на границе и
    extract_text() вставляет пробел ('13.0 1.26', 'М агистерская')."""
    grids = extract_pdf(FIXTURES / "13744.pdf")
    grid = _page_grid(grids, 1)
    text = "\n".join(c.text for c in grid.cells)
    assert "13.01.26" in text
    assert "13.0 1.26" not in text


def test_sibling_tables_on_one_page_are_all_kept():
    """14058 стр.3: три таблицы рядом по вертикали. find_tables()[0] отдал бы
    только первую — и две таблицы экзаменов исчезли бы молча."""
    grids = extract_pdf(FIXTURES / "14058.pdf")
    on_p3 = [g for g in grids if g.page == 3]
    assert len(on_p3) == 3
    assert [g.table_index for g in on_p3] == [0, 1, 2]

    text = "\n".join(c.text for g in on_p3 for c in g.cells)
    assert "Дата" in text and "экзамена" in text


def test_nested_false_tables_are_dropped():
    """13820 стр.5: pdfplumber находит внутри ячейки шапки вторую 'таблицу'.

    Её содержимое уже есть в основной таблице — если оставить, ячейки задвоятся
    и сверка «ни одна ячейка не потеряна» на слое importer начнёт врать.
    """
    with pdfplumber.open(FIXTURES / "13820.pdf") as pdf:
        assert len(pdf.pages[4].find_tables()) == 2, "pdfplumber видит две"

    grids = extract_pdf(FIXTURES / "13820.pdf")
    on_p5 = [g for g in grids if g.page == 5]
    assert len(on_p5) == 1, "вложенная — артефакт, наружу не выходит"
    assert on_p5[0].n_cols > 10


def test_duplicate_cell_nested_inside_another_is_dropped():
    """13471 стр.11 R26: занятие нарисовано дважды — внешней ячейкой и внутренней
    рамкой вокруг текста. Тексты одинаковые, ширина разная.

    Оставь мы обе — занятие задвоится, а два кандидата с разной привязкой к
    группам будут спорить, кому пара принадлежит. Внешняя совпадает по x с
    соседними строками, она и настоящая.
    """
    with pdfplumber.open(FIXTURES / "13471.pdf") as pdf:
        raw = [c for c in pdf.pages[10].find_tables()[0].rows[26].cells if c]
    assert len(raw) == 3, "pdfplumber отдаёт время + внешнюю + вложенную"

    grid = _page_grid(extract_pdf(FIXTURES / "13471.pdf"), 11)
    row = grid.row(26)
    lessons = [c for c in row if "Проектирование и разработка" in c.text]
    assert len(lessons) == 1, "занятие ровно одно, а не задвоено"
    assert (lessons[0].bbox[0], lessons[0].bbox[2]) == pytest.approx((241.05, 779.61), abs=0.01)


def test_page_without_tables_is_skipped_not_crashed():
    """13619 стр.5 — пустая концевая страница (0 слов, 0 линий). Не скан."""
    grids = extract_pdf(FIXTURES / "13619.pdf")
    assert grids, "остальные страницы разобрались"
    assert not [g for g in grids if g.page == 5]


def test_extract_pdf_accepts_bytes(grids_13470):
    data = (FIXTURES / "13470.pdf").read_bytes()
    assert len(extract_pdf(data)) == len(grids_13470)


def test_cells_of_a_row_are_ordered_left_to_right(grids_13470):
    grid = _page_grid(grids_13470, 2)
    for row in grid.rows():
        starts = [c.col_start for c in row]
        assert starts == sorted(starts)
        for prev, nxt in zip(row, row[1:]):
            assert prev.col_end < nxt.col_start, "ячейки одной строки не перекрываются"


def test_no_row_has_overlapping_cells_across_the_whole_corpus():
    """Сплошная проверка инварианта по всем 29 фикстурам: в пределах строки
    ячейки идут слева направо и не перекрываются, колонки не выходят за сетку.

    Именно эта проверка нашла задвоенную ячейку в 13471 стр.11 — точечными
    тестами такое не ловится, потому что заранее неизвестно, где оно.
    """
    for path in sorted(FIXTURES.glob("*.pdf")):
        for grid in extract_pdf(path):
            where = f"{path.name} стр.{grid.page} T{grid.table_index}"
            for index in range(grid.n_rows):
                row = grid.row(index)
                for prev, nxt in zip(row, row[1:]):
                    assert prev.col_end < nxt.col_start, f"перекрытие: {where} R{index}"
                for cell in row:
                    assert 0 <= cell.col_start <= cell.col_end < grid.n_cols, (
                        f"колонка вне сетки: {where} R{index}"
                    )
