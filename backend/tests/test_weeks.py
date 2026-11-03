"""Календарь недель. Тесты против настоящих файлов ЮФУ.

Синтетика тут появляется ровно там, где реального примера НЕТ и быть не может:
расхождение календаря с ISO-чётностью в корпусе не встречается (228/228 сошлись),
а обработать его надо — иначе первый же сломанный источник уедет в тишину.
Всё остальное проверяется на 12 семестровых файлах.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from src.models import WeekType
from src.schedule.extract_docx import extract_docx
from src.schedule.extract_pdf import extract_pdf
from src.schedule.grid import Cell, Grid
from src.schedule.weeks import (
    is_week_calendar,
    iso_parity_week_type,
    parse_week_calendar,
)

FIXTURES = Path(__file__).parent / "fixtures" / "schedule"

# Все 12 файлов с недельной сеткой: 8 бакалавров + 4 магистров.
# Осенние дают 18 диапазонов (9 строк × 2 пары), весенние — 20 (10 × 2).
AUTUMN = ["13469.docx", "13470.pdf", "13471.pdf", "13472.pdf", "13497.pdf", "13498.pdf"]
SPRING = ["13820.pdf", "13821.docx", "13822.pdf", "13828.pdf", "13829.pdf", "13830.pdf"]


def calendar_grid(name: str) -> Grid:
    """Календарь — таблица 1 семестрового файла (стр.1 у PDF)."""
    path = FIXTURES / name
    if path.suffix == ".docx":
        return extract_docx(path)[0]
    return [g for g in extract_pdf(path) if g.page == 1][0]


@pytest.fixture(scope="module")
def autumn() -> Grid:
    return calendar_grid("13469.docx")


@pytest.fixture(scope="module")
def spring() -> Grid:
    return calendar_grid("13820.pdf")


def test_extracts_18_ranges_from_13469(autumn):
    parsed = parse_week_calendar(autumn)

    assert len(parsed.weeks) == 18
    assert parsed.anomalies == ()

    first = parsed.weeks[0]
    assert (first.date_from, first.date_to) == (date(2025, 9, 1), date(2025, 9, 7))
    assert first.week_type is WeekType.UPPER


def test_read_by_column_pairs_not_by_rows(autumn):
    """ГЛАВНЫЙ тест слоя: левая пара колонок непрерывно продолжается правой.

    Построчное чтение дало бы 01.09 → 03.11 → 08.09 → 10.11: сентябрь и ноябрь
    вперемешку. Порядок здесь не косметика — на нём держится непрерывность
    цепочки, а по ней downstream ищет неделю по дате.
    """
    weeks = parse_week_calendar(autumn).weeks

    # Стык колонок: 9 строк левой пары, затем правая с самого начала.
    assert weeks[8].date_from == date(2025, 10, 27)
    assert weeks[9].date_from == date(2025, 11, 3), "после левой колонки идёт правая"

    dates = [w.date_from for w in weeks]
    assert dates == sorted(dates), "диапазоны идут по возрастанию дат"

    gaps = [
        (a.date_to, b.date_from)
        for a, b in zip(weeks, weeks[1:])
        if (b.date_from - a.date_to).days != 1
    ]
    assert gaps == [], "цепочка недель непрерывна: каждая начинается назавтра"


def test_both_dash_kinds_are_parsed(autumn):
    """В одном файле оба дефиса: '-' (U+002D) и '–' (U+2013), пробелы плавают."""
    raws = [w.raw for w in parse_week_calendar(autumn).weeks]

    assert any("-" in r for r in raws), "дефис-минус в корпусе есть"
    assert any("–" in r for r in raws), "тире в корпусе есть"

    # '22.09.25 – 28.09.25' — тире; '01.09.25 - 07.09.25' — дефис. Оба разобраны.
    by_start = {w.date_from: w for w in parse_week_calendar(autumn).weeks}
    assert by_start[date(2025, 9, 22)].date_to == date(2025, 9, 28)
    assert by_start[date(2025, 9, 1)].date_to == date(2025, 9, 7)


def test_year_rollover_inside_range(autumn):
    """'29.12.25 – 04.01.26' — конец в следующем году, а не в том же."""
    last = parse_week_calendar(autumn).weeks[-1]

    assert (last.date_from, last.date_to) == (date(2025, 12, 29), date(2026, 1, 4))
    assert last.week_type is WeekType.LOWER


def test_spring_file_gives_20_ranges(spring):
    parsed = parse_week_calendar(spring)

    assert len(parsed.weeks) == 20
    assert parsed.anomalies == ()

    first = parsed.weeks[0]
    assert (first.date_from, first.date_to) == (date(2026, 2, 9), date(2026, 2, 15))
    assert first.week_type is WeekType.LOWER


@pytest.mark.parametrize("name", AUTUMN + SPRING)
def test_every_semester_file_parses_without_anomalies(name):
    """Сплошной прогон: 12 файлов, оба формата, 228 диапазонов, 0 аномалий.

    Сюда же входит ассерт по ISO-чётности — он часть parse_week_calendar.
    """
    parsed = parse_week_calendar(calendar_grid(name))

    expected = 18 if name in AUTUMN else 20
    assert len(parsed.weeks) == expected
    assert parsed.anomalies == ()


def test_docx_and_pdf_give_identical_calendar():
    """Слой форматно-нейтрален: 13469.docx и 13470.pdf — один и тот же семестр."""
    from_docx = parse_week_calendar(calendar_grid("13469.docx")).weeks
    from_pdf = parse_week_calendar(calendar_grid("13470.pdf")).weeks

    assert [(w.date_from, w.date_to, w.week_type) for w in from_docx] == [
        (w.date_from, w.date_to, w.week_type) for w in from_pdf
    ]


def test_iso_parity_formula_matches_corpus():
    """Формула «чётная ISO = верхняя» сходится 228/228 — и всё равно не источник
    истины: она держится на одном учебном годе. Здесь она проверяется как факт,
    в parse_week_calendar работает как ассерт."""
    for name in AUTUMN + SPRING:
        for week in parse_week_calendar(calendar_grid(name)).weeks:
            assert iso_parity_week_type(week.date_from) is week.week_type, name


def test_iso_parity_of_bare_dates():
    assert iso_parity_week_type(date(2025, 9, 1)) is WeekType.UPPER  # ISO 36
    assert iso_parity_week_type(date(2026, 2, 9)) is WeekType.LOWER  # ISO 7
    # 29.12.25 — ISO-неделя 1 уже следующего года: чётность считается по ISO,
    # а не по календарному году.
    assert iso_parity_week_type(date(2025, 12, 29)) is WeekType.LOWER


def synthetic(rows: list[tuple[str, str]]) -> Grid:
    cells = []
    for i, (rng, kind) in enumerate(rows):
        cells.append(Cell(row=i, col_start=0, col_end=0, text=rng))
        cells.append(Cell(row=i, col_start=1, col_end=1, text=kind))
    return Grid(cells=tuple(cells), n_cols=2, table_index=0)


def test_iso_mismatch_is_anomaly_not_failure():
    """Разошлось с формулой → НЕ падаем. Календарь всё равно данные, а
    расхождение — сигнал админу, что источник изменился."""
    grid = synthetic([("01.09.25 - 07.09.25", "Нижняя неделя")])  # ISO 36 → ждём upper

    parsed = parse_week_calendar(grid)

    assert len(parsed.weeks) == 1
    assert parsed.weeks[0].week_type is WeekType.LOWER, "верим файлу, а не формуле"
    assert len(parsed.anomalies) == 1
    assert "ISO" in parsed.anomalies[0].reason
    assert "01.09.25" in parsed.anomalies[0].raw_text


def test_unparsable_range_becomes_anomaly():
    grid = synthetic(
        [
            ("01.09.25 - 07.09.25", "Верхняя неделя"),
            ("сентябрь", "Нижняя неделя"),
        ]
    )

    parsed = parse_week_calendar(grid)

    assert len(parsed.weeks) == 1, "разобранная строка не теряется из-за соседней"
    assert len(parsed.anomalies) == 1
    assert parsed.anomalies[0].raw_text == "сентябрь | Нижняя неделя"


def test_unknown_week_type_becomes_anomaly():
    grid = synthetic([("01.09.25 - 07.09.25", "Числитель")])

    parsed = parse_week_calendar(grid)

    assert parsed.weeks == ()
    assert len(parsed.anomalies) == 1
    assert "Числитель" in parsed.anomalies[0].raw_text


def test_half_filled_row_becomes_anomaly():
    grid = synthetic([("01.09.25 - 07.09.25", "")])

    parsed = parse_week_calendar(grid)

    assert parsed.weeks == ()
    assert len(parsed.anomalies) == 1


def test_fully_empty_row_is_skipped_silently():
    """Пустая строка — это конец таблицы, а не потеря данных."""
    grid = synthetic([("01.09.25 - 07.09.25", "Верхняя неделя"), ("", "")])

    parsed = parse_week_calendar(grid)

    assert len(parsed.weeks) == 1
    assert parsed.anomalies == ()


def test_anomaly_reason_fits_unparsed_cell_column():
    """UnparsedCell.reason — String(200). Причина обязана туда влезть."""
    grid = synthetic([("сентябрь", "Числитель")])

    for anomaly in parse_week_calendar(grid).anomalies:
        assert len(anomaly.reason) <= 200


@pytest.mark.parametrize("name", AUTUMN + SPRING)
def test_is_week_calendar_true_for_semester_table_1(name):
    assert is_week_calendar(calendar_grid(name))


def test_is_week_calendar_false_for_lesson_grid():
    """Сетка занятий — не календарь: importer не должен принять её за таблицу 1."""
    lessons = [g for g in extract_pdf(FIXTURES / "13470.pdf") if g.page == 2][0]

    assert not is_week_calendar(lessons)


def test_is_week_calendar_false_for_exam_session():
    exams = extract_docx(FIXTURES / "13984.docx")[0]

    assert not is_week_calendar(exams)
