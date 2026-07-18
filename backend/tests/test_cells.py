"""Разбор ячейки занятия. Строки — настоящие, из корпуса ЮФУ.

Каждый литерал в этом файле выдран из фикстуры; где это дёшево, тест берёт
ячейку прямо из документа, а не из копипасты. Синтетика тут бесполезна: слой
существует ровно затем, чтобы пережить опечатки ЮФУ («Персонал-технологии (c)»
с латинской c), артефакты извлечения и три способа записать одно и то же.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.models import LessonKind, WeekType
from src.schedule.cells import CellParse, parse_cell, split_lessons
from src.schedule.extract_docx import extract_docx

FIXTURES = Path(__file__).parent / "fixtures" / "schedule"


@pytest.fixture(scope="module")
def grids_13469():
    return extract_docx(FIXTURES / "13469.docx")


def only(parse: CellParse):
    """Единственное занятие ячейки — с внятным сообщением, если их не одно."""
    assert parse.reason is None, f"ячейка не разобрана: {parse.reason}"
    assert len(parse.lessons) == 1, f"ожидалось одно занятие, вышло {len(parse.lessons)}"
    return parse.lessons[0]


# --- базовая форма ---------------------------------------------------------


def test_subject_kind_teacher_room(grids_13469):
    """Ячейка берётся из файла: 'Математика (с) Кораблина Ю.В.  \\n  ауд. 106'."""
    cell = next(c for c in grids_13469[1].row(6) if "Кораблина" in c.text)
    lesson = only(parse_cell(cell.text))

    assert lesson.subject == "Математика"
    assert lesson.lesson_kind is LessonKind.SEMINAR
    assert lesson.teachers == ("Кораблина Ю.В.",)
    # префикс «ауд.» срезан при разборе: в БД лежит голое значение,
    # канцелярию дописывает интерфейс (см. src/schedule/rooms.py)
    assert lesson.room == "106"
    # cell_raw хранится ВСЕГДА и не тронут: пробелы и \n как в источнике
    assert lesson.cell_raw == cell.text


def test_two_teachers_split_by_comma():
    text = "Экономическая теория (с)  \n Кот В.В., Стрельченко Е.А.  ауд. 217"
    lesson = only(parse_cell(text))
    assert lesson.subject == "Экономическая теория"
    assert lesson.teachers == ("Кот В.В.", "Стрельченко Е.А.")
    assert lesson.room == "217"


def test_moodle_instead_of_room():
    lesson = only(parse_cell("Физическая культура и спорт (л)  Бондин В.И.     Moodle"))
    assert lesson.subject == "Физическая культура и спорт"
    assert lesson.lesson_kind is LessonKind.LECTURE
    assert lesson.teachers == ("Бондин В.И.",)
    assert lesson.room == "Moodle"


def test_lesson_without_teacher_is_a_source_hole_not_an_error():
    """Отсутствие ФИО (8.1% ячеек) — дыра источника. Ждём None, а не падение."""
    lesson = only(parse_cell("Иностранный язык (с) Онлайн"))
    assert lesson.subject == "Иностранный язык"
    assert lesson.teachers == ()
    assert lesson.room == "Онлайн"


def test_lesson_without_room_is_a_source_hole_too():
    lesson = only(parse_cell("Экономика фирмы (л) Ермишина А.В."))
    assert lesson.subject == "Экономика фирмы"
    assert lesson.teachers == ("Ермишина А.В.",)
    assert lesson.room is None


def test_room_glued_to_teacher_without_space(grids_13469):
    """13821: 'Маличенко И.П.ауд.Креат.пр' — пробела перед «ауд» нет."""
    text = "Основы современной аналитики персонала (л) Маличенко И.П.ауд.Креат.пр"
    lesson = only(parse_cell(text))
    assert lesson.subject == "Основы современной аналитики персонала"
    assert lesson.teachers == ("Маличенко И.П.",)
    assert lesson.room == "Креат.пр"


def test_multiword_room_is_not_cut_at_first_space():
    """'ауд.Креативное пр-во' — аудитория из двух слов, режущий \\S+ её теряет."""
    text = "Основы российской государственности (с) Абросимов Д.В. ауд.Креативное пр-во"
    lesson = only(parse_cell(text))
    assert lesson.room == "Креативное пр-во"
    assert lesson.teachers == ("Абросимов Д.В.",)


def test_short_room_prefix_is_normalized_too():
    """«а.218» — краткая форма того же префикса; в БД обе дают «218»."""
    lesson = only(parse_cell("Эконометрика (с) Житников И.В. а.218"))
    assert lesson.room == "218"


def test_double_dot_room_prefix_is_tolerated():
    """«ауд..405» — опечатка источника (2 вхождения в живой базе)."""
    lesson = only(parse_cell("Экономика фирмы (л) Ермишина А.В. ауд..405"))
    assert lesson.room == "405"


def test_leading_dot_is_not_part_of_the_subject():
    lesson = only(parse_cell(". История России (с) Галич Ж.В.  \n  ауд.214"))
    assert lesson.subject == "История России"


def test_latin_c_typo_is_still_a_seminar():
    """13498 p10 R9: 'Персонал-технологии (c) …' — c ЛАТИНСКАЯ.

    Глазом не отличить, а regex по кириллице отправляет живое занятие в
    UnparsedCell. Опечатка ЮФУ, а не наша.
    """
    lesson = only(parse_cell("Персонал-технологии (c) Щетинина Д.П. ауд.209"))
    assert lesson.subject == "Персонал-технологии"
    assert lesson.lesson_kind is LessonKind.SEMINAR


def test_subject_with_parenthesised_part_keeps_it():
    """'(часть 2)' — часть названия, а не вид занятия (23 вхождения)."""
    text = "Информационно- коммуникационные технологии (часть 2) (с) Цыганков С.С. ауд.407"
    lesson = only(parse_cell(text))
    assert lesson.subject == "Информационно- коммуникационные технологии (часть 2)"
    assert lesson.lesson_kind is LessonKind.SEMINAR


# --- дата-префиксы ---------------------------------------------------------


def test_date_prefix_without_space_before_subject():
    """13821 T5 R20: 'До 14.05Анализ данных (л) …' — пробела после даты нет."""
    lesson = only(parse_cell("До 14.05Анализ данных (л) Шаль А.В.  ауд.118  "))
    assert lesson.date_constraint_raw == "До 14.05"
    assert lesson.subject == "Анализ данных"
    assert lesson.room == "118"


def test_date_prefix_with_enumeration():
    text = "08.11,  15.11   Основы российской государственности (л) Абросимов Д.В. ауд.118"
    lesson = only(parse_cell(text))
    # пробелы внутри префикса схлопнуты: разбор идёт по нормализованному тексту,
    # а исходное написание целиком лежит в cell_raw
    assert lesson.date_constraint_raw == "08.11, 15.11"
    assert lesson.subject == "Основы российской государственности"


def test_date_prefix_since():
    lesson = only(parse_cell("С 6.10 Экономика фирмы (л) Ермишина А.В. ауд.405"))
    assert lesson.date_constraint_raw == "С 6.10"
    assert lesson.subject == "Экономика фирмы"


# --- тип недели внутри ячейки ---------------------------------------------


def test_week_type_inside_cell_does_not_leak_into_subject():
    """13820 p5: третий способ записи типа недели — прямо в ячейке.

    Не вырежешь — «Верхняя неделя» уедет в название предмета, и предмет
    никогда не совпадёт с собой же на нижней неделе.
    """
    text = "Верхняя неделя Воображение, изображение и реальность (л) онлайн"
    lesson = only(parse_cell(text))
    assert lesson.week_type is WeekType.UPPER
    assert lesson.subject == "Воображение, изображение и реальность"
    assert lesson.room == "онлайн"


def test_no_week_marker_means_every_week():
    """NULL = каждую неделю. Это ОСНОВНОЙ случай, а не исключение."""
    lesson = only(parse_cell("Математика (с) Кораблина Ю.В. ауд.106"))
    assert lesson.week_type is None


# --- подгруппы -------------------------------------------------------------


def test_subgroup_label_is_parsed_and_stripped():
    """13472 p12: единственное место, где подгруппа помечена ТЕКСТОМ."""
    text = "Управление проектами (лаб) 1п/г Бермудес Сото Хосе Грегорио Г-138"
    lesson = only(parse_cell(text))
    assert lesson.subgroup == 1
    assert lesson.subject == "Управление проектами"
    assert lesson.teachers == ("Бермудес Сото Хосе Грегорио",)
    assert lesson.room == "Г-138"


def test_second_subgroup():
    text = "Проектирование и разработка информационных систем (лаб) 2п/г Жуков А.А. ауд.Г-138"
    lesson = only(parse_cell(text))
    assert lesson.subgroup == 2
    assert lesson.room == "Г-138"


def test_no_label_means_no_subgroup_from_text():
    """Метки нет → решает геометрия (слой structure), а не догадка тут."""
    lesson = only(parse_cell("Математика (с) Кораблина Ю.В. ауд.106"))
    assert lesson.subgroup is None


# --- виды занятий, которых нет в модели ------------------------------------


def test_lab_is_recognised_and_kept_raw():
    """'(лаб)' СУЩЕСТВУЕТ — 12 вхождений (разведка утверждала обратное).

    В LessonKind значения под «лаб» нет, поэтому lesson_kind=None, но kind_raw
    держит исходный токен: занятие остаётся у студента, а не уезжает в очередь.
    """
    text = "Управление проектами (лаб) 1п/г Бермудес Сото Хосе Грегорио Г-138"
    lesson = only(parse_cell(text))
    assert lesson.kind_raw == "лаб"
    assert lesson.lesson_kind is None


def test_lecture_slash_seminar_does_not_poison_teachers():
    """'(л)/(с)' — 45 вхождений; ни в плане, ни в разведке его нет.

    Базовый regex плана такую ячейку МАТЧИТ и молча кладёт '/(с)' в
    преподавателей — худший режим отказа: тест зелёный, данные кривые.
    """
    text = "Международные стандарты финансовой отчетности (л)/(с) Полховская Т.Ю., Шевченко А.А. ауд.310"
    lesson = only(parse_cell(text))
    assert lesson.kind_raw == "л/с"
    assert lesson.lesson_kind is None
    assert lesson.subject == "Международные стандарты финансовой отчетности"
    assert lesson.teachers == ("Полховская Т.Ю.", "Шевченко А.А.")
    assert lesson.room == "310"


def test_lecture_slash_seminar_spaced_variants():
    """13498 p10: 'Персонал-технологии (л) / (с) …' — пробелы вокруг слэша."""
    lesson = only(parse_cell("Персонал-технологии (л) / (с) Щетинина Д.П. ауд.209"))
    assert lesson.kind_raw == "л/с"
    assert lesson.teachers == ("Щетинина Д.П.",)


# --- заглушки и мусор ------------------------------------------------------


@pytest.mark.parametrize("text", ["…………….", "……..", "……", ".", ",,,,,,"])
def test_placeholder_means_no_lessons_not_a_failure(text):
    """'…………….' — непустой текст, означающий «занятий нет».

    Это НЕ потеря: заглушку не за что ругать, в очередь админа она не идёт.
    """
    parse = parse_cell(text)
    assert parse.is_placeholder
    assert parse.lessons == ()
    assert parse.reason is None


def test_cell_without_kind_marker_goes_to_the_queue():
    """Дыра источника: вида занятия нет вообще → разбирать нечего, но и терять
    нельзя. Причина обязана быть внятной для админа."""
    parse = parse_cell("История экономики и экономических учений Грищенко И.В. ауд.217")
    assert parse.lessons == ()
    assert parse.reason is not None
    assert "вид" in parse.reason


def test_fragment_cell_goes_to_the_queue():
    """Артефакт извлечения: 'ауд.221' сам по себе — не занятие."""
    parse = parse_cell("ауд.221")
    assert parse.lessons == ()
    assert parse.reason is not None


# --- несколько занятий в одной ячейке --------------------------------------


def test_two_parallel_lessons_in_one_cell(grids_13469):
    """13469 T2 R2: два параллельных занятия, разделитель — аудитория 'Онлайн'."""
    cell = next(c for c in grids_13469[1].row(2) if "Иностранный язык" in c.text)
    parse = parse_cell(cell.text)
    assert parse.reason is None
    assert len(parse.lessons) == 2

    first, second = parse.lessons
    assert first.subject == "Иностранный язык"
    assert first.room == "Онлайн"
    assert second.subject == "Русский язык для иностранных студентов"
    assert second.teachers == ("Груданова И.Ю.",)
    assert second.room == "222"
    # обе половины несут исходный текст ячейки целиком
    assert first.cell_raw == cell.text == second.cell_raw


def test_two_lessons_with_date_prefixes_in_one_cell():
    """13469: 'До 17.12 …ауд.220 24.12 …' — две пары, у каждой своя дата."""
    text = (
        "До 17.12     История менеджмента (л) Костенко Е.П. \nауд.220\n24.12\n"
        "Основы российской государственности (с) Абросимов Д.В. ауд.220"
    )
    parse = parse_cell(text)
    assert parse.reason is None
    assert len(parse.lessons) == 2

    first, second = parse.lessons
    assert first.date_constraint_raw == "До 17.12"
    assert first.subject == "История менеджмента"
    assert first.room == "220"
    assert second.date_constraint_raw == "24.12"
    assert second.subject == "Основы российской государственности"


def test_newline_is_not_a_lesson_separator():
    """ГЛАВНАЯ ловушка слоя: в PDF узкая ячейка переносит ОДНО занятие на 6 строк.

    13470 p4 R8. Резать по \\n — значит покрошить одну пару на шесть огрызков;
    настоящая граница — конец аудитории.
    """
    text = (
        "Кросс-культурный\nменеджмент (л)/(с)\nКостенко Е.П.,\nНесоленая О.В.,\n"
        "Кузнецова С.Ю.\nауд.301"
    )
    lesson = only(parse_cell(text))
    assert lesson.subject == "Кросс-культурный менеджмент"
    assert lesson.teachers == ("Костенко Е.П.", "Несоленая О.В.", "Кузнецова С.Ю.")
    assert lesson.room == "301"


def test_elective_list_without_rooms_cannot_be_split():
    """13471 p4 R6: 'Прикладной анализ данных на Python (л) Сайтостроение (л)'.

    Два курса по выбору, ни аудиторий, ни преподавателей — границы между ними
    нет. Угадывать нельзя: разрежешь неверно — студент придёт не туда.
    """
    parse = parse_cell("Прикладной анализ данных на Python (л) Сайтостроение (л)")
    assert parse.lessons == ()
    assert parse.reason is not None
    assert "границ" in parse.reason


def test_split_lessons_returns_none_when_boundary_is_unknown():
    assert split_lessons("Прикладной анализ данных на Python (л) Сайтостроение (л)") is None
    assert len(split_lessons("Иностранный язык (с) Онлайн Русский язык (с) И.Ю. ауд.222")) == 2
