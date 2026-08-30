from dataclasses import FrozenInstanceError, replace
from datetime import date, time

import pytest

from src.models import (
    EducationLevel,
    Group,
    Lesson,
    LessonKind,
    Module,
    Teacher,
    WeekType,
)
from src.schedule.reviewed_schedule import (
    GroupIdentity,
    ModuleIdentity,
    lesson_state,
    state_signature,
)


def _lesson(*, group: Group, **overrides) -> Lesson:
    data = {
        "group": group,
        "weekday": 1,
        "pair_number": 1,
        "starts_at": time(8),
        "ends_at": time(9, 35),
        "subject": "Экономическая теория",
        "lesson_kind": LessonKind.LECTURE,
        "room": "118",
        "week_type": None,
        "subgroup": 0,
        "date_constraint_raw": None,
        "cell_raw": "Экономическая теория (л) ауд.118",
        "valid_from": None,
        "valid_to": None,
        "specific_dates": [],
    }
    data.update(overrides)
    return Lesson(**data)


def test_reviewed_signature_contains_every_visible_and_filtering_field():
    group = Group(
        course=1,
        number=None,
        level=EducationLevel.MASTER,
        program="Корпоративные финансы",
        subgroup_count=1,
    )
    lesson = Lesson(
        group=group,
        weekday=5,
        pair_number=2,
        starts_at=time(9, 50),
        ends_at=time(11, 25),
        subject="Международная экономика",
        lesson_kind=LessonKind.SEMINAR,
        room="209",
        week_type=WeekType.UPPER,
        subgroup=0,
        date_constraint_raw="до 07.10",
        cell_raw="Международная экономика (с) ауд.209",
        cell_key="1:2:3",
        valid_from=date(2026, 9, 1),
        valid_to=date(2026, 10, 7),
        specific_dates=["2026-09-05"],
    )

    state = lesson_state(lesson, p_doc_id="14159")

    assert state.group == GroupIdentity(
        level="master", course=1, number=None, program="Корпоративные финансы"
    )
    assert state_signature(state) == (
        "документ=14159|группа=master/1//Корпоративные финансы|день=5|пара=2|"
        "начало=09:50:00|конец=11:25:00|предмет=Международная экономика|"
        "вид=seminar|препод=|ауд=209|неделя=upper|п/г=0|модуль=|"
        "даты=до 07.10|с=2026-09-01|по=2026-10-07|конкретные=2026-09-05"
    )


def test_bachelor_identity_uses_number_and_empty_program():
    group = Group(
        course=3,
        number="3.1",
        level=EducationLevel.BACHELOR,
        program=None,
    )

    state = lesson_state(_lesson(group=group), p_doc_id="14161")

    assert state.group == GroupIdentity(
        level="bachelor", course=3, number="3.1", program=None
    )
    assert "|группа=bachelor/3/3.1/|" in state_signature(state)


def test_teacher_and_module_are_included_by_natural_identity():
    group = Group(
        course=1,
        number=None,
        level=EducationLevel.MASTER,
        program="Экономическая аналитика",
    )
    module = Module(
        date_from=date(2026, 9, 1),
        date_to=date(2026, 11, 1),
    )
    teacher = Teacher(full_name="Иванова И.И.")
    lesson = _lesson(group=group, module=module, teacher=teacher)

    state = lesson_state(lesson, p_doc_id="14159")

    assert state.teacher == "Иванова И.И."
    assert state.module == ModuleIdentity(
        date_from=date(2026, 9, 1), date_to=date(2026, 11, 1)
    )
    assert "|препод=Иванова И.И.|" in state_signature(state)
    assert "|модуль=2026-09-01..2026-11-01|" in state_signature(state)


def test_lower_week_and_null_optional_fields_have_stable_empty_values():
    group = Group(
        course=4,
        number="4.2",
        level=EducationLevel.BACHELOR,
        program=None,
    )
    lesson = _lesson(
        group=group,
        weekday=0,
        pair_number=3,
        starts_at=time(11, 55),
        ends_at=time(13, 30),
        subject="Статистика",
        lesson_kind=None,
        room=None,
        week_type=WeekType.LOWER,
        cell_raw=None,
    )

    state = lesson_state(lesson, p_doc_id="14162")

    assert state_signature(state) == (
        "документ=14162|группа=bachelor/4/4.2/|день=0|пара=3|"
        "начало=11:55:00|конец=13:30:00|предмет=Статистика|вид=|"
        "препод=|ауд=|неделя=lower|п/г=0|модуль=|даты=|с=|по=|конкретные="
    )


def test_specific_dates_accept_dates_and_iso_strings_and_sort_in_signature():
    group = Group(
        course=2,
        number="2.1",
        level=EducationLevel.BACHELOR,
        program=None,
    )
    lesson = _lesson(
        group=group,
        specific_dates=[
            date(2026, 9, 19),
            "2026-09-05",
            date(2026, 9, 12),
        ],
    )

    state = lesson_state(lesson, p_doc_id="14160")

    assert state.specific_dates == (
        date(2026, 9, 19),
        date(2026, 9, 5),
        date(2026, 9, 12),
    )
    assert state_signature(state).endswith(
        "|конкретные=2026-09-05,2026-09-12,2026-09-19"
    )


def test_cell_raw_changes_state_equality_but_not_signature():
    group = Group(
        course=2,
        number="2.1",
        level=EducationLevel.BACHELOR,
        program=None,
    )
    first = lesson_state(
        _lesson(group=group, cell_raw="Экономическая теория (л) ауд.118"),
        p_doc_id="14160",
    )
    second = lesson_state(
        _lesson(group=group, cell_raw="Экономическая теория, лекция, 118"),
        p_doc_id="14160",
    )

    assert first != second
    assert state_signature(first) == state_signature(second)


def test_lesson_state_is_immutable():
    group = Group(
        course=2,
        number="2.1",
        level=EducationLevel.BACHELOR,
        program=None,
    )
    state = lesson_state(_lesson(group=group), p_doc_id="14160")

    with pytest.raises(FrozenInstanceError):
        state.subject = "Изменённый предмет"


def test_signature_distinguishes_delimiters_in_teacher_and_room():
    group = Group(
        course=2,
        number="2.1",
        level=EducationLevel.BACHELOR,
        program=None,
    )
    base = lesson_state(_lesson(group=group), p_doc_id="14160")
    teacher_contains_field = replace(base, teacher="A|ауд=B", room="C")
    room_contains_field = replace(base, teacher="A", room="B|ауд=C")

    assert teacher_contains_field != room_contains_field
    assert state_signature(teacher_contains_field) != state_signature(
        room_contains_field
    )


def test_signature_distinguishes_none_empty_and_literal_empty_token():
    group = Group(
        course=2,
        number="2.1",
        level=EducationLevel.BACHELOR,
        program=None,
    )
    base = lesson_state(_lesson(group=group), p_doc_id="14160")
    none_signature = state_signature(replace(base, teacher=None))
    empty_signature = state_signature(replace(base, teacher=""))
    literal_token_signature = state_signature(replace(base, teacher=r"\0"))

    assert len({none_signature, empty_signature, literal_token_signature}) == 3
    assert "|препод=|" in none_signature
    assert r"|препод=\0|" in empty_signature
    assert r"|препод=\\0|" in literal_token_signature


def test_signature_distinguishes_delimiters_in_group_components():
    group = Group(
        course=2,
        number="2.1",
        level=EducationLevel.BACHELOR,
        program=None,
    )
    base = lesson_state(_lesson(group=group), p_doc_id="14160")
    number_contains_separator = replace(
        base,
        group=GroupIdentity(
            level="bachelor", course=2, number="A/B", program="C"
        ),
    )
    program_contains_separator = replace(
        base,
        group=GroupIdentity(
            level="bachelor", course=2, number="A", program="B/C"
        ),
    )

    assert state_signature(number_contains_separator) != state_signature(
        program_contains_separator
    )
    assert r"|группа=bachelor/2/A\/B/C|" in state_signature(
        number_contains_separator
    )
    assert r"|группа=bachelor/2/A/B\/C|" in state_signature(
        program_contains_separator
    )


def test_signature_escapes_subject_and_date_constraint_control_characters():
    group = Group(
        course=2,
        number="2.1",
        level=EducationLevel.BACHELOR,
        program=None,
    )
    base = lesson_state(_lesson(group=group), p_doc_id="14160")
    state = replace(
        base,
        subject="A\\B|C/D\nE\rF",
        date_constraint_raw="G\\H|I/J\nK\rL",
    )

    signature = state_signature(state)

    assert r"|предмет=A\\B\|C\/D\nE\rF|вид=" in signature
    assert r"|даты=G\\H\|I\/J\nK\rL|с=" in signature
