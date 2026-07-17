"""Шапка, дни, время, привязка занятия к группе. Только настоящие файлы ЮФУ.

Здесь живёт скелет расписания: кто (группа) — когда (день × пара). Ошибка
этого слоя тихая и самая дорогая: пара уезжает не той группе или не в тот день,
и никто не замечает, пока студент не придёт не туда.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.models import EducationLevel, WeekType
from src.schedule.extract_docx import extract_docx
from src.schedule.extract_pdf import extract_pdf
from src.schedule.structure import (
    REASON_TIME_OFF_GRID,
    decode_weekday,
    find_time_column,
    parse_header,
    parse_pair_number,
    parse_rows,
    place_row,
    week_type_from_heading,
)

FIXTURES = Path(__file__).parent / "fixtures" / "schedule"


@pytest.fixture(scope="module")
def grids_13469():
    return extract_docx(FIXTURES / "13469.docx")


@pytest.fixture(scope="module")
def grids_13821():
    return extract_docx(FIXTURES / "13821.docx")


@pytest.fixture(scope="module")
def grids_13470():
    return extract_pdf(FIXTURES / "13470.pdf")


@pytest.fixture(scope="module")
def grids_13471():
    return extract_pdf(FIXTURES / "13471.pdf")


@pytest.fixture(scope="module")
def grids_13472():
    return extract_pdf(FIXTURES / "13472.pdf")


@pytest.fixture(scope="module")
def grids_13830():
    return extract_pdf(FIXTURES / "13830.pdf")


@pytest.fixture(scope="module")
def grids_13497():
    return extract_pdf(FIXTURES / "13497.pdf")


def page(grids, number):
    return next(g for g in grids if g.page == number)


# --- время → номер пары ----------------------------------------------------


@pytest.mark.parametrize(
    "time_raw, pair",
    [
        ("800-845\n850-935", 1),
        ("950-1035\n1040-1125", 2),
        ("1155- 1240\n1245- 1330", 3),  # пробелы после дефиса — как в источнике
        ("1345-1430\n1435-1520", 4),
        ("1550-1635\n1640-1725", 5),
        ("1735-1820\n1825-1910", 6),
    ],
)
def test_two_halves_map_to_pair_number(time_raw, pair):
    assert parse_pair_number(time_raw) == pair


@pytest.mark.parametrize(
    "time_raw, pair",
    [
        ("800-935", 1),
        ("950-1125", 2),
        ("1155- 1330", 3),
        ("1345-1520", 4),
        ("1550-1725", 5),
        ("1735-1910", 6),
    ],
)
def test_merged_pair_notation_maps_too(time_raw, pair):
    """Вторая запись того же: пара одним диапазоном, без половин.

    В плане её нет, а в 13472 таких ячеек 105 из ~200 — потеряй мы их, от файла
    осталась бы половина.
    """
    assert parse_pair_number(time_raw) == pair


def test_double_dash_is_still_a_pair():
    """'800--935' — опечатка ЮФУ, а не другая пара."""
    assert parse_pair_number("800--935") == 1


@pytest.mark.parametrize(
    "time_raw",
    [
        "800- 1025",  # блок в 3 ак. часа
        "1055-1320",
        "1350-1615",
        "1040-1125",  # одинокая половина
        "800-845\n850-935\n950-1035",  # полторы пары (иняз)
        "1825-1910\n1915-2000",  # съехало на половину: между парами 6 и 7
        "1640-1725\n1735-1820",
        "1345-1430\n1435-152",  # артефакт извлечения — обрезано
        "9501125",  # артефакт: дефис потерян
    ],
)
def test_time_outside_the_pair_grid_is_not_guessed(time_raw):
    """Время вне сетки пар → UnparsedCell. НЕ угадывать.

    Соблазн «ну это же примерно вторая пара» — прямой путь к тому, что студент
    придёт к 9:50 на занятие, которое началось в 8:00.
    """
    assert parse_pair_number(time_raw) is None


# --- день недели -----------------------------------------------------------


@pytest.mark.parametrize(
    "text, weekday",
    [
        ("ПОНЕДЕЛЬНИК", 0),
        ("Вторник", 1),
        ("СРЕДА", 2),
        ("ПОНЕДЕЛЬНИК 15.09", 0),  # с датой в той же ячейке
    ],
)
def test_plain_weekday(text, weekday):
    assert decode_weekday(text) == weekday


@pytest.mark.parametrize(
    "text, weekday",
    [
        ("К И Н Ь Л Е Д Е Н О П", 0),  # 13470 p2 — «ПОНЕДЕЛЬНИК» задом наперёд
        ("К И Н Р О Т В", 1),
        ("РД А СЕ", 2),  # 13472 p2 R13 — порядок символов вообще случайный
        ("Г Р Е В Т Е Ч", 3),
        ("А Ц И Н Т Я П", 4),
        ("а т о б б у С", 5),
        ("К И Н Ь Л9 Е Д Е 0 1 . Н О П", 0),  # 13471 p8 — с вкраплённой датой
        ("Л Е Д Е Н К И Н ОЬ П", 0),  # 13822 p13
    ],
)
def test_rotated_weekday_is_decoded(text, weekday):
    """В PDF имя дня повёрнуто на 90°, и pdfplumber отдаёт буквы В СЛУЧАЙНОМ
    ПОРЯДКЕ — не просто задом наперёд ('РД А СЕ' = СРЕДА).

    Поэтому день опознаётся по МУЛЬТИМНОЖЕСТВУ букв: порядок доверия не
    заслуживает, а набор букв у шести дней различается однозначно.
    """
    assert decode_weekday(text) == weekday


def test_rotated_day_split_across_two_cells(grids_13497):
    """13497 p2 R2: повёрнутое «ПОНЕДЕЛЬНИК» разорвано на ДВЕ ячейки —
    [1-2]'ь л е д е н о П' и [3-4]'к и н'. Порознь не читается ни одна.

    День склеивается из всех ячеек левее колонки времени: у магистров под день
    отдано шесть колонок, и слово свободно расползается по ним.
    """
    grid = page(grids_13497, 2)
    header = parse_header(grid)
    rows = {r.row: r for r in parse_rows(grid, header)}

    assert rows[2].weekday == 0
    assert rows[2].reason is None
    assert rows[3].weekday == 0  # дальше тянется carry-forward'ом
    assert rows[4].weekday == 1  # 'к и н р о т В' — вторник


def test_unreadable_day_is_not_guessed():
    """13830 p14 R16: 'у С' — от «СУББОТА» уцелели две буквы, остальные
    разъехались по соседним ячейкам. Не угадываем."""
    assert decode_weekday("у С") is None
    assert decode_weekday("День недели") is None
    assert decode_weekday("") is None


# --- тип недели страницей/заголовком ---------------------------------------


def test_week_type_from_page_heading():
    """13471 p10/p11 — маркер целой страницей; 13472 p14 — заголовком.

    Оба лежат в тексте страницы, ВНЕ таблицы, поэтому Grid их не видит: сюда
    их приносит слой importer, наше дело — распознать обе записи.
    """
    assert week_type_from_heading("ВЕРХНЯЯ НЕДЕЛЯ") is WeekType.UPPER
    assert week_type_from_heading("НИЖНЯЯ НЕДЕЛЯ") is WeekType.LOWER
    assert week_type_from_heading("НЕДЕЛЯ: ВЕРХНЯЯ") is WeekType.UPPER
    assert week_type_from_heading("НЕДЕЛЯ: НИЖНЯЯ") is WeekType.LOWER
    assert week_type_from_heading("День") is None


# --- шапка: где колонка времени и где группы -------------------------------


def test_group_header_row_is_not_r1_in_pdf(grids_13470):
    """План говорит «шапка групп в R1» — это факт про docx, и на PDF он ЛОЖЕН.

    В 13470 p2 названия направлений размазаны по R0–R3, а строка групп — R6.
    Жёсткий индекс R1 привязал бы все пары к пустой строке.
    """
    header = parse_header(page(grids_13470, 2))
    assert header.header_row == 6
    assert header.level is EducationLevel.BACHELOR
    assert {g.number: (g.col_start, g.col_end) for g in header.groups} == {
        "2.2": (2, 2),
        "2.3": (3, 5),
        "2.4": (6, 7),
        "2.5": (8, 10),
        "2.6": (11, 12),
        "2.1": (13, 15),
    }


def test_group_header_row_is_r1_in_docx(grids_13821):
    """А в docx он действительно R1 — то же правило «строка с 'Группа N.M'»
    даёт оба ответа, и помнить про формат не нужно."""
    header = parse_header(grids_13821[4])
    assert header.header_row == 1
    assert {g.number: (g.col_start, g.col_end) for g in header.groups} == {
        "2.2": (2, 3),
        "2.3": (4, 8),
        "2.4": (9, 10),
        "2.5": (11, 12),
        "2.6": (13, 14),
        "2.1": (15, 16),
    }


def test_directions_row_r0_is_ignored(grids_13821):
    """R0 съехал относительно R1: «Экономика» = 2–11, а группа 2.5 = 11–12.

    Маппинг группа→направление из XML строго не выводится, поэтому направления
    не берём вообще — лучше без данных, чем с выдуманными.
    """
    header = parse_header(grids_13821[4])
    assert all(g.program is None for g in header.groups)


def test_time_column_is_not_always_column_one(grids_13830):
    """13830 p14: день лежит в колонках 0–5, время — в 6, занятия — в 7.

    Колонка времени ищется по СОДЕРЖИМОМУ; жёсткая «колонка 1» разложила бы
    магистерские файлы (35% корпуса) по пустым местам.
    """
    grid = page(grids_13830, 14)
    assert find_time_column(grid) == 6

    header = parse_header(grid)
    assert header.time_col == 6
    assert header.level is EducationLevel.MASTER


def test_time_column_is_one_for_bachelors(grids_13469):
    assert find_time_column(grids_13469[1]) == 1


# --- магистры --------------------------------------------------------------


def test_master_page_is_a_program_without_group_numbers(grids_13830):
    """У магистров номера группы НЕТ: страница = программа."""
    header = parse_header(page(grids_13830, 14))
    assert header.level is EducationLevel.MASTER
    assert len(header.groups) == 1
    group = header.groups[0]
    assert group.number is None
    assert group.program == "Корпоративные финансы"
    assert header.course == 1


def test_bachelor_group_number_embedded_in_programme_title(grids_13471):
    """13471 p8: '«ИНФОРМАЦИОННЫЕ ТЕХНОЛОГИИ И БИЗНЕС-АНАЛИТИКА» 3.7'.

    Строки 'Группа N.M' нет, но это бакалавры — номер вшит в заголовок.
    Принять страницу за магистерскую значило бы потерять группу 3.7.
    """
    header = parse_header(page(grids_13471, 8))
    assert header.level is EducationLevel.BACHELOR
    assert len(header.groups) == 1
    assert header.groups[0].number == "3.7"


# --- дни: carry-forward ----------------------------------------------------


def test_day_is_carried_forward(grids_13821):
    """13821 T5 R26: пара есть, время есть, а ячейка дня ПУСТАЯ и без vMerge —
    цепочка оборвана на строку раньше. Без carry-forward пара теряет день."""
    grid = grids_13821[4]
    header = parse_header(grid)
    rows = {r.row: r for r in parse_rows(grid, header)}

    assert rows[22].weekday == 4  # ПЯТНИЦА — ячейка дня есть
    assert rows[23].weekday == 4  # ячейки дня нет → тянем
    assert rows[26].weekday == 4  # четыре строки спустя — всё ещё пятница
    assert rows[26].pair_number == 5
    assert rows[26].reason is None


def test_separator_row_is_all_cells_empty(grids_13821):
    """Критерий разделителя — ВСЕ ячейки пусты, а не «день пустой»:
    у строк с парами день тоже пуст (см. carry-forward)."""
    grid = grids_13821[4]
    header = parse_header(grid)
    rows = {r.row: r for r in parse_rows(grid, header)}

    assert rows[21].is_separator
    assert not rows[22].is_separator
    assert not rows[23].is_separator, "у строки нет дня, но есть пары — не разделитель"


def test_row_with_off_grid_time_is_flagged(grids_13469):
    """Время вне сетки пар → строка помечена причиной, пары уедут в очередь."""
    grid = grids_13469[1]
    header = parse_header(grid)
    rows = [r for r in parse_rows(grid, header) if r.reason == REASON_TIME_OFF_GRID]
    assert rows, "в 13469 T2 есть '800-845 850-935 950-1035' — полторы пары"
    assert all(r.pair_number is None for r in rows)


# --- привязка занятия к группе --------------------------------------------


def test_lecture_for_the_whole_stream_lands_on_every_group(grids_13469):
    """Лекция на поток — одна ячейка на 6 групп; каждая должна её увидеть."""
    grid = grids_13469[1]
    header = parse_header(grid)
    placements = place_row(grid, 11, header)

    lecture = [p for p in placements if "История России (л)" in p.cell.text]
    assert len(lecture) == 6
    assert {p.group.number for p in lecture} == {"1.1", "1.2", "1.3", "1.4", "1.5", "1.6"}
    assert all(p.subgroup == 0 for p in lecture), "вся группа, а не подгруппа"


def test_partial_overlap_is_a_subgroup_numbered_by_order(grids_13821):
    """13821 T5 R24 — самый злой случай корпуса.

    Группа 2.3 занимает 4–8 и дробится на два куска: (4,5) и (6,10). Второй
    кусок при этом накрывает ВСЮ группу 2.4 (9–10). Значит одна и та же ячейка
    для 2.3 — вторая подгруппа, а для 2.4 — занятие всей группы.
    """
    grid = grids_13821[4]
    header = parse_header(grid)
    placements = place_row(grid, 23, header)

    by_group = {}
    for p in placements:
        by_group.setdefault(p.group.number, []).append(p)

    g23 = sorted(by_group["2.3"], key=lambda p: p.cell.col_start)
    assert len(g23) == 2
    assert g23[0].subgroup == 1 and "Анализ данных" in g23[0].cell.text
    assert g23[1].subgroup == 2 and "Бух. учет и фин.анализ" in g23[1].cell.text

    g24 = by_group["2.4"]
    assert len(g24) == 1
    assert "Бух. учет и фин.анализ" in g24[0].cell.text
    assert g24[0].subgroup == 0, "2.4 накрыта целиком — это не подгруппа"


def test_cell_covering_group_exactly_is_not_a_subgroup(grids_13821):
    grid = grids_13821[4]
    header = parse_header(grid)
    placements = place_row(grid, 22, header)
    g26 = [p for p in placements if p.group.number == "2.6"]
    assert len(g26) == 1
    assert g26[0].subgroup == 0


# --- страницы без шапки ----------------------------------------------------


def test_headerless_page_has_no_header_of_its_own(grids_13472):
    """13472 p3 — продолжение p2: шапки нет, парсер обязан это ЗАМЕТИТЬ,
    а не выдумать шапку из первой попавшейся строки."""
    assert parse_header(page(grids_13472, 3)) is None


def test_headerless_page_inherits_header_from_previous(grids_13472):
    """Наследование безопасно: геометрия колонок p2 и p3 совпадает.

    Проверяем именно это — иначе унаследованные диапазоны групп легли бы на
    другую сетку и пары разъехались бы по чужим группам.
    """
    prev = page(grids_13472, 2)
    cont = page(grids_13472, 3)
    header = parse_header(prev)

    assert cont.n_cols == prev.n_cols
    assert cont.col_bounds is not None and prev.col_bounds is not None
    assert all(
        abs(a - b) < 1.0 for a, b in zip(cont.col_bounds, prev.col_bounds)
    ), "геометрия колонок разошлась — наследовать шапку нельзя"

    # разрыв страницы проходит ПОСРЕДИ дня: p2 кончается 'СРЕДА 800-845',
    # p3 начинается '850-935' — той же среды. День приносим с собой.
    rows = parse_rows(cont, header, first_row=0, carry_day=2)
    assert rows[0].weekday == 2, "среда продолжается со следующей страницы"

    paired = [r for r in rows if r.pair_number is not None]
    assert paired, "на странице-продолжении обязаны найтись нормальные пары"
    assert all(r.weekday is not None for r in paired)
    # занятия на унаследованной шапке ложатся на настоящие группы
    placements = place_row(cont, paired[0].row, header)
    assert {p.group.number for p in placements} <= {g.number for g in header.groups}


def test_pair_split_across_page_break_is_not_guessed(grids_13472):
    """Оборотная сторона: половина пары, оставшаяся на предыдущей странице.

    13472 p3 R0 — это '850-935', вторая половина пары, начавшейся на p2. Сама
    по себе она в сетку не ложится, и склеивать половины через разрыв страницы
    мы не беремся — строка уедет в очередь админа с честной причиной.
    """
    rows = parse_rows(page(grids_13472, 3), parse_header(page(grids_13472, 2)),
                      first_row=0, carry_day=2)
    assert rows[0].time_raw.strip() == "850-935"
    assert rows[0].pair_number is None
    assert rows[0].reason == REASON_TIME_OFF_GRID
