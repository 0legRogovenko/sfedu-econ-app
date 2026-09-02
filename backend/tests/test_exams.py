"""Сессия → ExamEvent. Тесты против настоящих файлов ЮФУ.

Все 11 файлов сессий разобраны глазами перед тем, как писать тесты; каждая
проверка ниже — конкретная строка конкретного файла, а не выдуманный пример.
Синтетики здесь нет намеренно: тест, который проходит на придуманной строке
и падает на файле ЮФУ, бесполезен.
"""

from __future__ import annotations

import re
from datetime import date, time
from pathlib import Path

import pytest

from src.schedule.exams import parse_exams
from src.schedule.extract_docx import extract_docx
from src.schedule.extract_pdf import extract_pdf
from src.schedule.grid import Grid

FIXTURES = Path(__file__).parent / "fixtures" / "schedule"

# 11 файлов сессий по классификатору (см. test_classify.py).
SESSION_FILES = [
    "13744.pdf",
    "13745.pdf",
    "13746.pdf",
    "13747.pdf",
    "13767.pdf",
    "13768.pdf",
    "13984.docx",
    "14049.pdf",
    "14057.pdf",
    "14058.pdf",
    "14092.pdf",
]


def _grids(name: str) -> list[Grid]:
    path = FIXTURES / name
    if path.suffix == ".docx":
        return extract_docx(path)
    return extract_pdf(path)


@pytest.fixture(scope="module")
def exams_13984():
    return parse_exams(_grids("13984.docx"))


@pytest.fixture(scope="module")
def exams_13745():
    return parse_exams(_grids("13745.pdf"))


@pytest.fixture(scope="module")
def exams_13767():
    return parse_exams(_grids("13767.pdf"))


# --- 13984.docx — единственный docx среди сессий -------------------------


def test_13984_parses_three_exams_of_group_4_1(exams_13984):
    """Строка из плана Task A7, разобранная по полям.

    В файле 5 строк: шапка, три экзамена и пустая концевая. Группа «4.1»
    стоит только в первой из них — дальше ячейка пустая, номер тянется
    carry-forward'ом (ровно как день недели в семестровой сетке).
    """
    exams = exams_13984.exams
    assert len(exams) == 3
    assert {e.group_number for e in exams} == {"4.1"}

    first = exams[0]
    assert first.subject == "Экосистема современной организации"
    assert first.teachers == ("Чернова О.А.",)
    assert first.master_program is None

    assert first.consultation.date == date(2026, 4, 8)
    assert first.consultation.time_start == time(11, 0)
    # префикс «ауд.» срезан при разборе (src/schedule/rooms.py)
    assert first.consultation.room == "306"
    assert first.consultation.kind is None

    assert first.exam.date == date(2026, 4, 9)
    assert first.exam.time_start == time(9, 0)
    assert first.exam.time_end == time(13, 30)
    assert first.exam.kind == "устный"
    assert first.exam.room == "214"


def test_13984_teacher_on_the_same_line_as_subject(exams_13984):
    """«Интернет-маркетинг Володин Р.С.» — препод БЕЗ \\n, в одну строку.

    Наивное «последняя строка ячейки = преподаватель» на этой строке молча
    отдаёт предмет целиком вместе с ФИО. ФИО ищется регэкспом, а не срезом.
    """
    third = exams_13984.exams[2]
    assert third.subject == "Интернет-маркетинг"
    assert third.teachers == ("Володин Р.С.",)


def test_13984_form_is_free_text_not_a_guessed_enum(exams_13984):
    """«письменное тестирование» — форма, которой нет в списке «устный/письменный»."""
    second = exams_13984.exams[1]
    assert second.exam.kind == "письменное тестирование"
    assert second.exam.time_start == time(8, 0)


# --- 13745.pdf — вертикальное объединение и carry-forward ----------------


def test_13745_group_carries_forward_through_vertical_merge(exams_13745):
    """В PDF объединённая по вертикали ячейка группы существует только в своей
    первой строке: у R2/R3 колонки 0-1 НЕТ вообще (не пустая — отсутствует).

    Без carry-forward два экзамена из трёх у каждой группы остались бы без
    группы, то есть молча пропали бы.
    """
    exams = exams_13745.exams
    assert [e.group_number for e in exams[:3]] == ["1.1", "1.1", "1.1"]
    # 6 групп × 3 экзамена
    assert len(exams) == 18
    assert sorted({e.group_number for e in exams}) == [
        "1.1",
        "1.2",
        "1.3",
        "1.4",
        "1.5",
        "1.6",
    ]


def test_13745_two_teachers_split_by_comma(exams_13745):
    """«Экономическая теория\\nАлехин В.В., Захарова Д.С.» — двое через запятую."""
    exam = next(
        e
        for e in exams_13745.exams
        if e.group_number == "1.2" and e.subject == "Экономическая теория"
    )
    assert exam.teachers == ("Алехин В.В.", "Захарова Д.С.")


def test_13745_hyphenated_wrap_is_joined_without_space(exams_13745):
    """PDF переносит «Информационно-\\nкоммуникационные\\nтехнологии».

    Строка, оборванная дефисом, склеивается БЕЗ пробела, остальные — через
    пробел. Иначе в предмете окажется «Информационно- коммуникационные».
    """
    exam = exams_13745.exams[1]
    assert exam.subject == "Информационно-коммуникационные технологии"


def test_13745_form_wrapped_across_two_lines(exams_13745):
    """«компьютерное\\nтестирование» — форма разорвана переносом на две строки,
    а аудитория двойная: «ауд.324, 325»."""
    exam = exams_13745.exams[1]
    assert exam.exam.kind == "компьютерное тестирование"
    assert exam.exam.room == "324, 325"
    assert exam.exam.time_start == time(9, 0)
    assert exam.exam.time_end == time(13, 30)


# --- Магистры: группы нет, есть программа --------------------------------


def test_13767_master_program_instead_of_group_number(exams_13767):
    """У магистров колонка «№ группы» пустая, а в «Направление» — программа.

    Group(number) для них не годится: номера вида «2.1» у магистров не бывает.
    """
    exams = exams_13767.exams
    assert all(e.group_number is None for e in exams)
    assert all(e.master_program for e in exams)
    assert (
        exams[0].master_program
        == "Магистерская программа «Экономика, управление и право»"
    )


def test_13767_program_carries_forward_across_pages(exams_13767):
    """13767 стр.2 R1: и «№ группы», и «Направление» пустые — это продолжение
    программы «Учетные технологии и аудит» с предыдущей страницы.

    Carry-forward обязан переживать границу страницы, иначе экзамен уедет
    в неопознанные.
    """
    page2 = [e for e in exams_13767.exams if e.page == 2]
    first = page2[0]
    assert first.subject.startswith("Финансовый учет")
    assert first.master_program == "Магистерская программа «Учетные технологии и аудит»"


def test_13767_teachers_on_separate_lines_without_comma(exams_13767):
    """«Туманян Ю.Р\\nПогосян Н.В.» — двое, разделены переносом, а не запятой,
    и у первого потеряна точка после инициала (опечатка ЮФУ)."""
    exam = next(
        e
        for e in exams_13767.exams
        if e.subject == "Микроэкономика (продвинутый уровень)"
        and e.master_program.endswith("«Учетные технологии и аудит»")
    )
    assert exam.teachers == ("Туманян Ю.Р", "Погосян Н.В.")


def test_13767_leading_dot_is_stripped(exams_13767):
    """«. Институциональная экономика и право» — ведущая точка из источника."""
    subjects = {e.subject for e in exams_13767.exams}
    assert "Институциональная экономика и право" in subjects
    assert not any(s.startswith(".") for s in subjects)


def test_13767_essay_form(exams_13767):
    """«эссе» — форма, которой нет ни в одном списке «устный/письменный»."""
    exam = next(
        e
        for e in exams_13767.exams
        if e.subject == "Институциональная экономика и право"
    )
    assert exam.exam.kind == "эссе"


# --- Колонки задаются шапкой, а не индексом ------------------------------


def test_13744_header_spans_do_not_break_column_roles():
    """13744 стр.2: та же таблица, но n_cols=14 — колонки шапки занимают
    диапазоны (2,4), (5,7), (8,10), (11,13).

    Индекс колонки тут не значит НИЧЕГО: на стр.1 «Дата экзамена» — колонка 5,
    на стр.2 — 11–13. Роль колонки берётся из шапки по пересечению диапазонов.
    Захардкодить индексы — потерять всю страницу.
    """
    grids = _grids("13744.pdf")
    page2 = next(g for g in grids if g.page == 2)
    assert page2.n_cols == 14

    result = parse_exams(grids)
    page2_exams = [e for e in result.exams if e.page == 2]
    assert page2_exams, "стр.2 не разобрана — роли колонок взяты по индексу?"
    assert page2_exams[0].group_number == "4.3"
    assert page2_exams[0].subject == "Цифровая экономика"
    assert page2_exams[0].teachers == ("Никитаева А.Ю.", "Ковалев Д.В.")


def test_13746_page_without_header_inherits_layout():
    """13746 стр.2 начинается сразу с данных: шапки на странице нет.

    Разметка колонок наследуется с предыдущей страницы — геометрия совпадает.
    """
    result = parse_exams(_grids("13746.pdf"))
    page2 = [e for e in result.exams if e.page == 2]
    assert page2, "страница без шапки потеряна целиком"
    assert page2[0].group_number == "2.3"


def test_14049_headerless_page_inherits_by_geometry_not_by_recency():
    """14049: стр.1 — 5 колонок, стр.2 — 15, стр.3 — снова 5 и БЕЗ шапки.

    Наследовать «последнюю виденную» шапку тут нельзя: 15-колоночная разметка
    на 5-колоночной странице съезжает, все роли уходят влево, строки выглядят
    пустыми — и страница исчезает целиком, молча. Шапка наследуется от
    страницы С ТОЙ ЖЕ геометрией (стр.1), и только поэтому стр.3 жива.
    """
    grids = _grids("14049.pdf")
    assert [g.n_cols for g in grids] == [5, 15, 5], "геометрия фикстуры изменилась"

    result = parse_exams(grids)
    page3 = [e for e in result.exams if e.page == 3]
    assert page3, "стр.3 потеряна целиком: шапка унаследована по давности?"
    assert page3[0].group_number == "2.6"
    assert [e.subject for e in page3] == [
        "Иностранный язык",
        "Анализ данных",
        "Основы экономики труда",
        "Основы современной аналитики персонала",
    ]


# --- Ячейка даты: форма, время, аудитория, адрес -------------------------


def test_13747_form_may_be_absent():
    """«23.01.26\\n09.00-13.30\\nауд.217» — формы нет вовсе (13746 2.1).

    kind=None — это нормальная дыра источника, а не повод ронять разбор.
    """
    result = parse_exams(_grids("13746.pdf"))
    exam = next(e for e in result.exams if e.subject == "Поведенческий бизнес-анализ")
    assert exam.exam.kind is None
    assert exam.exam.room == "217"
    assert exam.exam.date == date(2026, 1, 23)


def test_13747_form_before_time_is_still_found():
    """13747 стр.3: «22.01.26\\nкомпьютерное\\nтестирование\\n09.00 – 13.30\\nауд.324»
    — форма стоит ПЕРЕД временем. Порядок строк в ячейке не фиксирован."""
    result = parse_exams(_grids("13747.pdf"))
    exam = next(e for e in result.exams if e.subject == "Цифровые технологии в HR")
    assert exam.exam.kind == "компьютерное тестирование"
    assert exam.exam.time_start == time(9, 0)
    assert exam.exam.time_end == time(13, 30)  # тире здесь длинное: «–»
    assert exam.exam.room == "324"


def test_13747_address_goes_to_room_not_to_form():
    """«24.01.26\\n11.55-15.20\\nг.Таганрог,\\nул.Энгельса, 1\\nГ-215» — занятие
    в другом городе: адрес и аудитория без «ауд.», формы нет.

    Если ловить аудиторию только по «ауд.», адрес утечёт в форму, и админ
    прочитает kind='г.Таганрог, ул.Энгельса, 1 Г-215'.
    """
    result = parse_exams(_grids("13747.pdf"))
    exam = next(e for e in result.exams if e.subject == "Методы оптимизации")
    assert exam.exam.kind is None
    assert exam.exam.room == "г.Таганрог, ул.Энгельса, 1 Г-215"
    assert exam.exam.time_start == time(11, 55)


def test_13747_combined_form_survives():
    """«компьютерное\\nтестирование+\\nустный» — составная форма."""
    result = parse_exams(_grids("13747.pdf"))
    exam = next(e for e in result.exams if e.subject == "Корпоративные финансы")
    assert exam.exam.kind == "компьютерное тестирование+ устный"


def _foreign_language_2_6():
    """Иняз группы 2.6 — единственный в 14049 с ОДНОЙ датой экзамена.

    У групп 2.1–2.5 тот же предмет расписан на две даты по уровням языка,
    и они уходят в очередь админа (см. тест ниже).
    """
    result = parse_exams(_grids("14049.pdf"))
    return next(
        e
        for e in result.exams
        if e.subject == "Иностранный язык" and e.group_number == "2.6"
    )


def test_14049_online_consultation_room():
    """«03.06.26\\n14.00\\nMicrosoft Teams» — вместо аудитории площадка."""
    exam = _foreign_language_2_6()
    assert exam.consultation.room == "Microsoft Teams"
    assert exam.consultation.time_start == time(14, 0)
    assert exam.consultation.kind is None


def test_14049_subject_without_teacher():
    """«Иностранный язык» — преподавателя в источнике нет. Это дыра источника,
    а не дефект разбора: ждём None/(), а не значение."""
    assert _foreign_language_2_6().teachers == ()


def test_14049_two_dates_in_one_cell_go_to_unparsed_not_silently_halved():
    """«04.06.26 (уровень А)\\n05.06.26 (уровень В)\\n08.00-13.30\\nустно\\nауд.109…»
    — ОДНА ячейка с ДВУМЯ датами экзамена (потоки по уровням языка).

    Взять первую дату — соврать половине группы. Такое уходит в очередь
    админа с исходным текстом, а не молча теряется и не угадывается.
    """
    result = parse_exams(_grids("14049.pdf"))
    two_dates = [u for u in result.unparsed if "уровень А" in u.raw_text]
    assert two_dates, "ячейка с двумя датами исчезла молча"
    assert all("дат" in u.reason for u in two_dates)


def test_14058_rotated_column_text_does_not_break_the_row():
    """14058 стр.1 R5: в колонке «Кол-во студентов» лежит «у\\nр\\nо\\nб\\nы\\nв\\nо\\nП»
    — это повёрнутое на 90° «По выбору», буквы задом наперёд.

    Строка при этом настоящая: у неё есть предмет и обе даты. Колонка
    количества студентов не читается вовсе, поэтому артефакт безвреден —
    но строку он пустой не делает.
    """
    result = parse_exams(_grids("14058.pdf"))
    exam = next(
        e for e in result.exams if e.subject == "Анализ хозяйственной деятельности"
    )
    assert exam.group_number == "3.2"
    assert exam.exam.date == date(2026, 6, 29)
    assert exam.exam.kind == "устно"


# --- Корпус целиком -------------------------------------------------------


@pytest.mark.parametrize("name", SESSION_FILES)
def test_every_session_file_yields_exams(name):
    """Ни один из 11 файлов сессий не падает и не даёт пусто."""
    result = parse_exams(_grids(name))
    assert result.exams, f"{name}: не извлечено ни одного экзамена"
    for exam in result.exams:
        assert exam.subject
        assert exam.group_number or exam.master_program
        assert exam.cell_raw


@pytest.mark.parametrize("name", SESSION_FILES)
def test_nothing_is_lost_silently(name):
    """Каждая строка с полезной нагрузкой легла либо в ExamEvent, либо
    в UnparsedCell."""
    result = parse_exams(_grids(name))
    accounted = len(result.exams) + len(result.unparsed)
    assert accounted == result.subject_rows_seen, (
        f"{name}: строк с нагрузкой {result.subject_rows_seen}, "
        f"разобрано+в очереди {accounted}"
    )


# Пересчитано глазами по дампу сеток всех 11 файлов. Этот тест — не тавтология
# (в отличие от инварианта выше, который считает по той же разметке, которой
# разбирает, и поэтому не заметил, как 14049 стр.3 пропала целиком): числа
# прибиты снаружи, и любая потеря страницы или строки роняет тест.
EXPECTED = {
    "13744.pdf": (39, 1),  # + одинокое «ВПК» без дат → в очередь
    "13745.pdf": (18, 0),  # 6 групп × 3 экзамена
    "13746.pdf": (24, 0),  # 6 групп × 4
    "13747.pdf": (31, 0),
    "13767.pdf": (17, 0),
    "13768.pdf": (14, 0),
    "13984.docx": (3, 0),
    "14049.pdf": (19, 5),  # 5 инязов на две даты → в очередь админа
    "14057.pdf": (17, 0),
    "14058.pdf": (31, 0),
    "14092.pdf": (18, 0),
}


@pytest.mark.parametrize("name", SESSION_FILES)
def test_exam_counts_per_file_are_pinned(name):
    result = parse_exams(_grids(name))
    expected_exams, expected_unparsed = EXPECTED[name]
    assert (len(result.exams), len(result.unparsed)) == (
        expected_exams,
        expected_unparsed,
    )


def test_13768_rows_drawn_off_grid_are_bound_by_x_not_by_column_index():
    """13768 рисует часть строк рамками на ~4 pt левее шапки.

    Из-за этого одна физическая колонка получает две границы, сетка выходит на
    12 колонок вместо 6, и ячейка предмета (6,7) пересекает по КОЛОНКАМ и
    «Кол-во студентов», и «Наименование дисциплины» — по одной каждую, ничья.
    Разрешение ничьей по порядку — это молчаливая порча: у 8 из 14 строк
    в предмет уезжала дата консультации, а экзамен исчезал совсем. Тест
    смотрит на ЗНАЧЕНИЯ, а не на количество: количество при порче не менялось.
    """
    result = parse_exams(_grids("13768.pdf"))
    assert len(result.exams) == 14

    shifted = next(
        e for e in result.exams if e.subject == "Система внутреннего контроля"
    )
    assert shifted.master_program.endswith("«Учетные технологии и аудит»")
    assert shifted.exam.date == date(2026, 1, 14)
    assert shifted.exam.kind == "устный"
    assert shifted.exam.room == "209"
    assert shifted.consultation.date == date(2026, 1, 12)

    for exam in result.exams:
        assert not re.match(r"^[\d.\s]+$", exam.subject), (
            f"в предмет уехала дата: {exam.subject!r}"
        )
        assert exam.exam is not None


def test_13744_lone_marker_without_dates_is_not_an_exam():
    """13744 стр.4: одинокое «ВПК» в колонке дисциплины — ни дат, ни препода.

    Отдать его как ExamEvent — положить студенту в список экзамен без даты.
    """
    result = parse_exams(_grids("13744.pdf"))
    assert "ВПК" not in {e.subject for e in result.exams}
    assert [(u.raw_text, u.reason) for u in result.unparsed] == [
        ("ВПК", "дисциплина без дат консультации и экзамена")
    ]


@pytest.mark.parametrize("name", SESSION_FILES)
def test_every_parsed_exam_has_a_date_and_a_plausible_subject(name):
    """Сплошная проверка ЗНАЧЕНИЙ по всему корпусу, а не количеств.

    Именно она ловит порчу разметки колонок: при ней счётчики не меняются,
    а в предмете оказывается «12.01.26 17.30 ауд.209».
    """
    for exam in parse_exams(_grids(name)).exams:
        assert exam.exam is not None and exam.exam.date, (
            f"{name}: {exam.subject!r} без даты"
        )
        assert len(exam.subject) >= 4, f"{name}: огрызок предмета {exam.subject!r}"
        assert not re.search(r"\d\d\.\d\d\.\d\d", exam.subject), (
            f"{name}: дата в предмете"
        )
        # ФИО не должно остаться в названии предмета
        assert not re.search(r"[А-ЯЁ]\.\s?[А-ЯЁ]\.", exam.subject), (
            f"{name}: ФИО в предмете"
        )


@pytest.mark.parametrize("name", SESSION_FILES)
def test_no_page_is_silently_dropped(name):
    """С КАЖДОЙ страницы каждого файла что-то извлеклось.

    Именно так ловится самый тихий отказ этого слоя: страница, где разметка
    колонок не подошла, не падает и не шумит — она просто выглядит пустой.
    """
    grids = _grids(name)
    result = parse_exams(grids)
    pages_with_tables = {g.page for g in grids}
    pages_with_output = {e.page for e in result.exams} | {
        u.page for u in result.unparsed
    }
    assert pages_with_tables <= pages_with_output, (
        f"{name}: страницы без единой строки — {pages_with_tables - pages_with_output}"
    )
