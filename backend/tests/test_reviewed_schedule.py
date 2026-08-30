import json
from dataclasses import FrozenInstanceError, replace
from datetime import date, time

import pytest
from sqlalchemy import select, text

from src.models import (
    DocType,
    EducationLevel,
    Group,
    Lesson,
    LessonKind,
    Module,
    ScheduleDocument,
    Teacher,
    WeekType,
)
from src.schedule.reviewed_schedule import (
    CorrectionOperation,
    CorrectionRegistry,
    CorrectionResult,
    DocumentCorrections,
    GroupIdentity,
    ModuleIdentity,
    ReviewValidationError,
    apply_document_corrections,
    lesson_state,
    load_correction_registry,
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


def _state_json(**overrides):
    payload = {
        "p_doc_id": "14159",
        "group": {
            "level": "master",
            "course": 1,
            "number": None,
            "program": "Корпоративные финансы",
        },
        "weekday": 5,
        "pair_number": 2,
        "starts_at": "09:50:00",
        "ends_at": "11:25:00",
        "subject": "Международная экономика",
        "lesson_kind": "seminar",
        "teacher": None,
        "room": "209",
        "week_type": "upper",
        "subgroup": 0,
        "module": {
            "date_from": "2026-09-01",
            "date_to": "2026-11-01",
        },
        "date_constraint_raw": "до 07.10",
        "valid_from": "2026-09-01",
        "valid_to": "2026-10-07",
        "specific_dates": ["2026-09-05"],
        "cell_raw": "Международная экономика (с) ауд.209",
    }
    payload.update(overrides)
    return payload


def _operation_json(operation="replace", **overrides):
    payload = {
        "id": "master-room-209",
        "operation": operation,
        "page": 4,
        "evidence": "reviewed PDF page 4",
        "expected_before": _state_json(),
        "after": _state_json(room="210"),
    }
    if operation == "add":
        payload["expected_before"] = None
    elif operation == "remove":
        payload["after"] = None
    payload.update(overrides)
    return payload


def _document_json(*, p_doc_id="14159", sha256=None, operations=None):
    return {
        "p_doc_id": p_doc_id,
        "sha256": sha256 or "a" * 64,
        "operations": operations if operations is not None else [],
    }


def _write_registry(tmp_path, *, documents=None, **overrides):
    payload = {
        "version": 1,
        "documents": documents if documents is not None else [],
    }
    payload.update(overrides)
    path = tmp_path / "corrections.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def test_registry_loads_strict_typed_operations_and_guards_sources(tmp_path):
    operations = [
        _operation_json("add", id="add-master-lesson"),
        _operation_json("replace", id="replace-master-room"),
        _operation_json("remove", id="remove-master-lesson"),
    ]
    path = _write_registry(
        tmp_path,
        documents=[_document_json(operations=operations)],
    )

    registry = load_correction_registry(path)

    assert isinstance(registry, CorrectionRegistry)
    assert registry.manages("14159")
    assert registry.manages(14159)
    document = registry.documents["14159"]
    assert isinstance(document, DocumentCorrections)
    assert document.operations == tuple(document.operations)
    assert all(isinstance(item, CorrectionOperation) for item in document.operations)
    assert document.operations[0].expected_before is None
    assert document.operations[0].after.starts_at == time(9, 50)
    assert document.operations[1].after.module == ModuleIdentity(
        date_from=date(2026, 9, 1), date_to=date(2026, 11, 1)
    )
    assert document.operations[1].after.specific_dates == (date(2026, 9, 5),)
    assert document.operations[2].after is None
    registry.guard_source(14159, "a" * 64)

    with pytest.raises(FrozenInstanceError):
        document.operations[0].page = 8


def test_registry_rejects_unknown_hash_for_managed_document(tmp_path):
    path = _write_registry(
        tmp_path,
        documents=[_document_json()],
    )
    registry = load_correction_registry(path)

    with pytest.raises(
        ReviewValidationError,
        match="document 14159 changed and requires review",
    ):
        registry.guard_source("14159", "b" * 64)


def test_registry_guard_is_noop_for_unmanaged_document(tmp_path):
    registry = load_correction_registry(
        _write_registry(tmp_path, documents=[_document_json()])
    )

    assert not registry.manages("99999")
    registry.guard_source("99999", "not-even-a-hash")


def test_registry_documents_mapping_cannot_be_mutated_or_disable_guard(tmp_path):
    registry = load_correction_registry(
        _write_registry(tmp_path, documents=[_document_json()])
    )

    with pytest.raises(TypeError):
        registry.documents["14160"] = registry.documents["14159"]
    with pytest.raises(TypeError):
        del registry.documents["14159"]
    with pytest.raises(AttributeError):
        registry.documents.clear()

    assert registry.manages(14159)
    with pytest.raises(
        ReviewValidationError,
        match="document 14159 changed and requires review",
    ):
        registry.guard_source(14159, "b" * 64)


@pytest.mark.parametrize(
    "p_doc_id",
    ["014159", "0", "+14159", "-14159", " 14159", "14159 "],
)
def test_registry_rejects_noncanonical_document_ids(tmp_path, p_doc_id):
    path = _write_registry(
        tmp_path,
        documents=[_document_json(p_doc_id=p_doc_id)],
    )

    with pytest.raises(ReviewValidationError, match="invalid document id"):
        load_correction_registry(path)


def test_registry_keeps_canonical_document_id_compatible_with_integer_lookup(
    tmp_path,
):
    registry = load_correction_registry(
        _write_registry(tmp_path, documents=[_document_json(p_doc_id="14159")])
    )

    assert registry.manages("14159")
    assert registry.manages(14159)


@pytest.mark.parametrize("p_doc_id", ["014159", "0", " 14159"])
def test_registry_manages_rejects_noncanonical_public_document_id(
    tmp_path, p_doc_id
):
    registry = load_correction_registry(
        _write_registry(tmp_path, documents=[_document_json()])
    )

    with pytest.raises(ReviewValidationError, match="invalid document id"):
        registry.manages(p_doc_id)


@pytest.mark.parametrize("p_doc_id", ["014159", "0", " 14159"])
def test_registry_guard_rejects_noncanonical_public_document_id(
    tmp_path, p_doc_id
):
    registry = load_correction_registry(
        _write_registry(tmp_path, documents=[_document_json()])
    )

    with pytest.raises(ReviewValidationError, match="invalid document id"):
        registry.guard_source(p_doc_id, "a" * 64)


@pytest.mark.parametrize("p_doc_id", [0, -14159])
def test_registry_public_api_rejects_nonpositive_integer_document_id(
    tmp_path, p_doc_id
):
    registry = load_correction_registry(
        _write_registry(tmp_path, documents=[_document_json()])
    )

    with pytest.raises(ReviewValidationError, match="invalid document id"):
        registry.manages(p_doc_id)
    with pytest.raises(ReviewValidationError, match="invalid document id"):
        registry.guard_source(p_doc_id, "a" * 64)


def test_registry_rejects_duplicate_document_ids(tmp_path):
    path = _write_registry(
        tmp_path,
        documents=[_document_json(), _document_json()],
    )

    with pytest.raises(ReviewValidationError, match="duplicate document id 14159"):
        load_correction_registry(path)


def test_registry_rejects_duplicate_operation_ids_in_one_document(tmp_path):
    operation = _operation_json("remove")
    path = _write_registry(
        tmp_path,
        documents=[_document_json(operations=[operation, operation])],
    )

    with pytest.raises(
        ReviewValidationError,
        match="duplicate correction id master-room-209",
    ):
        load_correction_registry(path)


def test_registry_rejects_duplicate_operation_ids_across_documents(tmp_path):
    first = _operation_json("remove")
    second = _operation_json(
        "remove",
        expected_before=_state_json(p_doc_id="14160"),
    )
    path = _write_registry(
        tmp_path,
        documents=[
            _document_json(operations=[first]),
            _document_json(
                p_doc_id="14160",
                sha256="b" * 64,
                operations=[second],
            ),
        ],
    )

    with pytest.raises(
        ReviewValidationError,
        match="duplicate correction id master-room-209",
    ):
        load_correction_registry(path)


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"version": 1, "documents": [], "typo": True}, "registry: unknown keys"),
        (
            {
                "version": 1,
                "documents": [_document_json() | {"source": "pdf"}],
            },
            "document 14159: unknown keys",
        ),
        (
            {
                "version": 1,
                "documents": [
                    _document_json(
                        operations=[_operation_json("remove", typo=True)]
                    )
                ],
            },
            "correction master-room-209: unknown keys",
        ),
        (
            {
                "version": 1,
                "documents": [
                    _document_json(
                        operations=[
                            _operation_json(
                                "remove",
                                expected_before=_state_json(typo=True),
                            )
                        ]
                    )
                ],
            },
            "lesson state: unknown keys",
        ),
        (
            {
                "version": 1,
                "documents": [
                    _document_json(
                        operations=[
                            _operation_json(
                                "remove",
                                expected_before=_state_json(
                                    group=_state_json()["group"] | {"typo": True}
                                ),
                            )
                        ]
                    )
                ],
            },
            "group identity: unknown keys",
        ),
        (
            {
                "version": 1,
                "documents": [
                    _document_json(
                        operations=[
                            _operation_json(
                                "remove",
                                expected_before=_state_json(
                                    module=_state_json()["module"] | {"typo": True}
                                ),
                            )
                        ]
                    )
                ],
            },
            "module identity: unknown keys",
        ),
    ],
)
def test_registry_rejects_unknown_keys_at_every_level(tmp_path, payload, message):
    path = tmp_path / "corrections.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(ReviewValidationError, match=message):
        load_correction_registry(path)


@pytest.mark.parametrize(
    ("sha256", "message"),
    [
        ("a" * 63, "invalid SHA-256"),
        ("g" * 64, "invalid SHA-256"),
        ("A" * 64, "invalid SHA-256"),
    ],
)
def test_registry_rejects_malformed_sha256(tmp_path, sha256, message):
    path = _write_registry(
        tmp_path,
        documents=[_document_json(sha256=sha256)],
    )

    with pytest.raises(ReviewValidationError, match=message):
        load_correction_registry(path)


@pytest.mark.parametrize(
    "correction_id",
    ["", "UPPERCASE", "spaces are unsafe", "../escape", "a" * 44],
)
def test_registry_rejects_unsafe_correction_id(tmp_path, correction_id):
    path = _write_registry(
        tmp_path,
        documents=[
            _document_json(
                operations=[_operation_json("remove", id=correction_id)]
            )
        ],
    )

    with pytest.raises(ReviewValidationError, match="unsafe correction id"):
        load_correction_registry(path)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("level", "postgraduate", "invalid education level"),
        ("lesson_kind", "practice", "invalid lesson kind"),
        ("week_type", "both", "invalid week type"),
    ],
)
def test_registry_validates_enum_values(tmp_path, field, value, message):
    state = _state_json()
    if field == "level":
        state["group"] = state["group"] | {"level": value}
    else:
        state[field] = value
    path = _write_registry(
        tmp_path,
        documents=[
            _document_json(
                operations=[_operation_json("remove", expected_before=state)]
            )
        ],
    )

    with pytest.raises(ReviewValidationError, match=message):
        load_correction_registry(path)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("weekday", -1, "weekday must be between 0 and 5"),
        ("weekday", 6, "weekday must be between 0 and 5"),
        ("pair_number", 0, "pair number must be between 1 and 7"),
        ("pair_number", 8, "pair number must be between 1 and 7"),
        ("subgroup", -1, "subgroup must be between 0 and 99"),
        ("subgroup", 100, "subgroup must be between 0 and 99"),
    ],
)
def test_registry_validates_lesson_integer_boundaries(
    tmp_path, field, value, message
):
    path = _write_registry(
        tmp_path,
        documents=[
            _document_json(
                operations=[
                    _operation_json(
                        "remove",
                        expected_before=_state_json(**{field: value}),
                    )
                ]
            )
        ],
    )

    with pytest.raises(ReviewValidationError, match=message):
        load_correction_registry(path)


@pytest.mark.parametrize("page", [0, -1, 10_001])
def test_registry_validates_source_page_boundaries(tmp_path, page):
    path = _write_registry(
        tmp_path,
        documents=[
            _document_json(
                operations=[_operation_json("remove", page=page)]
            )
        ],
    )

    with pytest.raises(ReviewValidationError, match="page must be between 1 and 10000"):
        load_correction_registry(path)


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        (
            {"starts_at": "11:25:00", "ends_at": "09:50:00"},
            "lesson time range is invalid",
        ),
        ({"starts_at": "not-a-time"}, "invalid ISO time"),
        ({"valid_from": "30.02.2026"}, "invalid ISO date"),
        (
            {"valid_from": "2026-11-01", "valid_to": "2026-09-01"},
            "validity date range is invalid",
        ),
        (
            {
                "module": {
                    "date_from": "2026-11-01",
                    "date_to": "2026-09-01",
                }
            },
            "module date range is invalid",
        ),
    ],
)
def test_registry_validates_iso_values_and_ranges(tmp_path, overrides, message):
    path = _write_registry(
        tmp_path,
        documents=[
            _document_json(
                operations=[
                    _operation_json(
                        "remove",
                        expected_before=_state_json(**overrides),
                    )
                ]
            )
        ],
    )

    with pytest.raises(ReviewValidationError, match=message):
        load_correction_registry(path)


def test_registry_rejects_specific_date_on_another_weekday(tmp_path):
    path = _write_registry(
        tmp_path,
        documents=[
            _document_json(
                operations=[
                    _operation_json(
                        "remove",
                        expected_before=_state_json(
                            weekday=4,
                            specific_dates=["2026-09-05"],
                        ),
                    )
                ]
            )
        ],
    )

    with pytest.raises(
        ReviewValidationError,
        match="specific date 2026-09-05 does not match weekday 4",
    ):
        load_correction_registry(path)


@pytest.mark.parametrize(
    ("specific_date", "valid_from", "valid_to", "message"),
    [
        (
            "2026-08-29",
            "2026-09-01",
            "2026-10-07",
            "specific date 2026-08-29 is before valid_from 2026-09-01",
        ),
        (
            "2026-10-10",
            "2026-09-01",
            "2026-10-07",
            "specific date 2026-10-10 is after valid_to 2026-10-07",
        ),
    ],
)
def test_registry_requires_specific_dates_inside_validity_window(
    tmp_path, specific_date, valid_from, valid_to, message
):
    path = _write_registry(
        tmp_path,
        documents=[
            _document_json(
                operations=[
                    _operation_json(
                        "remove",
                        expected_before=_state_json(
                            specific_dates=[specific_date],
                            valid_from=valid_from,
                            valid_to=valid_to,
                            module=None,
                        ),
                    )
                ]
            )
        ],
    )

    with pytest.raises(ReviewValidationError, match=message):
        load_correction_registry(path)


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        (
            {"valid_from": "2026-08-29"},
            "valid_from 2026-08-29 is outside module",
        ),
        (
            {"valid_to": "2026-11-02"},
            "valid_to 2026-11-02 is outside module",
        ),
        (
            {
                "specific_dates": ["2026-08-29"],
                "valid_from": "2026-09-01",
                "valid_to": "2026-10-31",
            },
            "specific date 2026-08-29 is outside module",
        ),
    ],
)
def test_registry_requires_validity_and_specific_dates_inside_module(
    tmp_path, overrides, message
):
    path = _write_registry(
        tmp_path,
        documents=[
            _document_json(
                operations=[
                    _operation_json(
                        "remove",
                        expected_before=_state_json(**overrides),
                    )
                ]
            )
        ],
    )

    with pytest.raises(ReviewValidationError, match=message):
        load_correction_registry(path)


@pytest.mark.parametrize(
    ("valid_from", "valid_to"),
    [
        (None, None),
        ("2026-09-01", None),
        (None, "2026-10-31"),
    ],
)
def test_registry_requires_complete_validity_window_for_module(
    tmp_path, valid_from, valid_to
):
    state = _state_json(
        valid_from=valid_from,
        valid_to=valid_to,
        specific_dates=[],
    )
    path = _write_registry(
        tmp_path,
        documents=[
            _document_json(
                operations=[
                    _operation_json("remove", expected_before=state)
                ]
            )
        ],
    )

    with pytest.raises(
        ReviewValidationError,
        match="module requires both valid_from and valid_to",
    ):
        load_correction_registry(path)


def test_registry_accepts_validity_window_without_module(tmp_path):
    state = _state_json(
        module=None,
        valid_from="2026-09-01",
        valid_to="2026-10-31",
        specific_dates=["2026-09-05"],
    )
    registry = load_correction_registry(
        _write_registry(
            tmp_path,
            documents=[
                _document_json(
                    operations=[
                        _operation_json("remove", expected_before=state)
                    ]
                )
            ],
        )
    )

    loaded = registry.documents["14159"].operations[0].expected_before
    assert loaded is not None
    assert loaded.module is None
    assert loaded.valid_from == date(2026, 9, 1)
    assert loaded.valid_to == date(2026, 10, 31)


def test_registry_accepts_consistent_specific_dates_and_ranges(tmp_path):
    state = _state_json(
        weekday=5,
        module={"date_from": "2026-09-01", "date_to": "2026-11-01"},
        valid_from="2026-09-01",
        valid_to="2026-10-31",
        specific_dates=["2026-09-05", "2026-09-12", "2026-10-31"],
    )
    registry = load_correction_registry(
        _write_registry(
            tmp_path,
            documents=[
                _document_json(
                    operations=[
                        _operation_json("remove", expected_before=state)
                    ]
                )
            ],
        )
    )

    loaded = registry.documents["14159"].operations[0].expected_before
    assert loaded is not None
    assert loaded.specific_dates == (
        date(2026, 9, 5),
        date(2026, 9, 12),
        date(2026, 10, 31),
    )


@pytest.mark.parametrize(
    ("starts_at", "ends_at", "message"),
    [
        (
            "09:50:00",
            "09:50:00.000001",
            "ISO time must not contain microseconds",
        ),
        (
            "09:50:00+03:00",
            "11:25:00+03:00",
            "ISO time must not contain a timezone offset",
        ),
        (
            "09:50:00",
            "09:50:00",
            "lesson time range is invalid",
        ),
    ],
)
def test_registry_rejects_noncanonical_or_empty_time_ranges(
    tmp_path, starts_at, ends_at, message
):
    path = _write_registry(
        tmp_path,
        documents=[
            _document_json(
                operations=[
                    _operation_json(
                        "remove",
                        expected_before=_state_json(
                            starts_at=starts_at,
                            ends_at=ends_at,
                        ),
                    )
                ]
            )
        ],
    )

    with pytest.raises(ReviewValidationError, match=message):
        load_correction_registry(path)


@pytest.mark.parametrize(
    ("starts_at", "ends_at", "expected_start", "expected_end"),
    [
        ("09:50", "11:25", time(9, 50), time(11, 25)),
        ("09:50:00", "11:25:00", time(9, 50), time(11, 25)),
    ],
)
def test_registry_accepts_iso_times_with_optional_seconds(
    tmp_path, starts_at, ends_at, expected_start, expected_end
):
    operation = _operation_json(
        "remove",
        expected_before=_state_json(starts_at=starts_at, ends_at=ends_at),
    )
    registry = load_correction_registry(
        _write_registry(
            tmp_path,
            documents=[_document_json(operations=[operation])],
        )
    )

    state = registry.documents["14159"].operations[0].expected_before
    assert state is not None
    assert (state.starts_at, state.ends_at) == (expected_start, expected_end)


@pytest.mark.parametrize("evidence", ["", "   ", "\n\t"])
def test_registry_rejects_blank_evidence(tmp_path, evidence):
    path = _write_registry(
        tmp_path,
        documents=[
            _document_json(
                operations=[_operation_json("remove", evidence=evidence)]
            )
        ],
    )

    with pytest.raises(ReviewValidationError, match="evidence must not be blank"):
        load_correction_registry(path)


@pytest.mark.parametrize(
    ("operation", "changes", "message"),
    [
        ("add", {"after": None}, "add requires after"),
        (
            "add",
            {"expected_before": _state_json()},
            "add forbids expected_before",
        ),
        (
            "replace",
            {"expected_before": None},
            "replace requires expected_before and after",
        ),
        (
            "replace",
            {"after": None},
            "replace requires expected_before and after",
        ),
        ("remove", {"expected_before": None}, "remove requires expected_before"),
        (
            "remove",
            {"after": _state_json()},
            "remove forbids after",
        ),
    ],
)
def test_registry_enforces_operation_semantics(
    tmp_path, operation, changes, message
):
    path = _write_registry(
        tmp_path,
        documents=[
            _document_json(
                operations=[_operation_json(operation, **changes)]
            )
        ],
    )

    with pytest.raises(ReviewValidationError, match=message):
        load_correction_registry(path)


def test_registry_accepts_absent_irrelevant_state_keys(tmp_path):
    add = _operation_json("add", id="add-state")
    add.pop("expected_before")
    remove = _operation_json("remove", id="remove-state")
    remove.pop("after")

    registry = load_correction_registry(
        _write_registry(
            tmp_path,
            documents=[_document_json(operations=[add, remove])],
        )
    )

    assert registry.documents["14159"].operations[0].expected_before is None
    assert registry.documents["14159"].operations[1].after is None


@pytest.mark.parametrize("state_field", ["expected_before", "after"])
def test_registry_requires_state_document_id_to_match_document(
    tmp_path, state_field
):
    operation = _operation_json(
        "replace",
        **{state_field: _state_json(p_doc_id="14160")},
    )
    path = _write_registry(
        tmp_path,
        documents=[_document_json(operations=[operation])],
    )

    with pytest.raises(
        ReviewValidationError,
        match="lesson state document 14160 does not match document 14159",
    ):
        load_correction_registry(path)


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"documents": []}, "registry: missing keys: version"),
        ({"version": 2, "documents": []}, "unsupported correction version 2"),
        ({"version": 1, "documents": "not-a-list"}, "documents must be a list"),
    ],
)
def test_registry_rejects_missing_version_and_wrong_top_level_types(
    tmp_path, payload, message
):
    path = tmp_path / "corrections.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ReviewValidationError, match=message):
        load_correction_registry(path)


def _seed_correction_document(db_session):
    document = ScheduleDocument(
        p_doc_id=14159,
        section="Осенний семестр",
        label="1 курс Маг",
        doc_type=DocType.SEMESTER_GRID_MASTER,
        sha256="a" * 64,
        source_url="https://example.test/14159.pdf",
    )
    group = Group(
        course=1,
        number=None,
        level=EducationLevel.MASTER,
        program="Корпоративные финансы",
        subgroup_count=2,
    )
    module = Module(
        document=document,
        name="I модуль",
        date_from=date(2026, 9, 1),
        date_to=date(2026, 11, 1),
    )
    teacher = Teacher(full_name="Иванова И.И.")
    db_session.add_all([document, group, module, teacher])
    db_session.flush()
    lesson = Lesson(
        group=group,
        document_id=document.id,
        module=module,
        weekday=0,
        pair_number=1,
        starts_at=time(8),
        ends_at=time(9, 35),
        subject="Экономическая теория",
        lesson_kind=LessonKind.LECTURE,
        teacher=teacher,
        room="118",
        week_type=None,
        subgroup=0,
        date_constraint_raw=None,
        cell_raw="Экономическая теория (л) Иванова И.И. ауд.118",
        cell_key="1:2:3",
        valid_from=date(2026, 9, 1),
        valid_to=date(2026, 11, 1),
        specific_dates=[],
    )
    db_session.add(lesson)
    db_session.flush()
    return document, group, module, teacher, lesson


def _correction(
    operation,
    *,
    operation_id="master-room-209",
    expected_before=None,
    after=None,
):
    return CorrectionOperation(
        id=operation_id,
        operation=operation,
        page=4,
        evidence="reviewed PDF page 4",
        expected_before=expected_before,
        after=after,
    )


def _corrections(document, *operations, p_doc_id=None, sha256=None):
    return DocumentCorrections(
        p_doc_id=p_doc_id or str(document.p_doc_id),
        sha256=sha256 or document.sha256,
        operations=tuple(operations),
    )


def _persisted_lessons(db_session, document):
    return db_session.scalars(
        select(Lesson).where(Lesson.document_id == document.id).order_by(Lesson.id)
    ).all()


def test_replace_writes_every_lesson_field_and_preserves_document(db_session):
    document, old_group, old_module, old_teacher, lesson = (
        _seed_correction_document(db_session)
    )
    new_group = Group(
        course=1,
        number=None,
        level=EducationLevel.MASTER,
        program="Финансовые технологии",
        subgroup_count=2,
    )
    new_module = Module(
        document=document,
        name="II модуль",
        date_from=date(2026, 11, 2),
        date_to=date(2027, 1, 10),
    )
    new_teacher = Teacher(full_name="Петрова П.П.")
    db_session.add_all([new_group, new_module, new_teacher])
    db_session.flush()
    before = lesson_state(lesson, p_doc_id=str(document.p_doc_id))
    after = replace(
        before,
        group=GroupIdentity(
            level="master",
            course=1,
            number=None,
            program="Финансовые технологии",
        ),
        weekday=5,
        pair_number=2,
        starts_at=time(9, 50),
        ends_at=time(11, 25),
        subject="Международная экономика",
        lesson_kind="seminar",
        teacher="Петрова П.П.",
        room="209",
        week_type="upper",
        subgroup=2,
        module=ModuleIdentity(
            date_from=date(2026, 11, 2),
            date_to=date(2027, 1, 10),
        ),
        date_constraint_raw="07.11, 21.11",
        valid_from=date(2026, 11, 2),
        valid_to=date(2027, 1, 10),
        specific_dates=(date(2026, 11, 7), date(2026, 11, 21)),
        cell_raw="Международная экономика (с) Петрова П.П. ауд.209",
    )

    result = apply_document_corrections(
        db_session,
        document,
        _corrections(
            document,
            _correction("replace", expected_before=before, after=after),
        ),
    )

    db_session.refresh(lesson)
    assert result == CorrectionResult(added=0, replaced=1, removed=0)
    assert lesson.document_id == document.id
    assert lesson.group_id == new_group.id
    assert lesson.module_id == new_module.id
    assert lesson.teacher_id == new_teacher.id
    assert lesson.weekday == 5
    assert lesson.pair_number == 2
    assert lesson.starts_at == time(9, 50)
    assert lesson.ends_at == time(11, 25)
    assert lesson.subject == "Международная экономика"
    assert lesson.lesson_kind is LessonKind.SEMINAR
    assert lesson.room == "209"
    assert lesson.week_type is WeekType.UPPER
    assert lesson.subgroup == 2
    assert lesson.date_constraint_raw == "07.11, 21.11"
    assert lesson.cell_raw == after.cell_raw
    assert lesson.cell_key == "manual:master-room-209"
    assert lesson.valid_from == date(2026, 11, 2)
    assert lesson.valid_to == date(2027, 1, 10)
    assert lesson.specific_dates == ["2026-11-07", "2026-11-21"]


def test_replace_stale_expected_state_matches_zero_and_does_not_mutate(db_session):
    document, _, _, _, lesson = _seed_correction_document(db_session)
    actual = lesson_state(lesson, p_doc_id=str(document.p_doc_id))
    stale = replace(actual, room="401")
    after = replace(actual, room="209")

    with pytest.raises(ReviewValidationError, match="matched 0 lessons"):
        apply_document_corrections(
            db_session,
            document,
            _corrections(
                document,
                _correction("replace", expected_before=stale, after=after),
            ),
        )

    db_session.refresh(lesson)
    assert lesson.room == "118"
    assert lesson.cell_key == "1:2:3"


def test_exact_match_ambiguity_is_rejected_without_mutation(db_session):
    document, group, module, teacher, lesson = _seed_correction_document(db_session)
    db_session.execute(text("DROP INDEX uq_lessons_slot"))
    duplicate = Lesson(
        group=group,
        document_id=document.id,
        module=module,
        weekday=lesson.weekday,
        pair_number=lesson.pair_number,
        starts_at=lesson.starts_at,
        ends_at=lesson.ends_at,
        subject=lesson.subject,
        lesson_kind=lesson.lesson_kind,
        teacher=teacher,
        room=lesson.room,
        week_type=lesson.week_type,
        subgroup=lesson.subgroup,
        date_constraint_raw=lesson.date_constraint_raw,
        cell_raw=lesson.cell_raw,
        cell_key="9:9:9",
        valid_from=lesson.valid_from,
        valid_to=lesson.valid_to,
        specific_dates=list(lesson.specific_dates),
    )
    db_session.add(duplicate)
    db_session.flush()
    before = lesson_state(lesson, p_doc_id=str(document.p_doc_id))

    with pytest.raises(ReviewValidationError, match="matched 2 lessons"):
        apply_document_corrections(
            db_session,
            document,
            _corrections(
                document,
                _correction("remove", expected_before=before),
            ),
        )

    assert len(_persisted_lessons(db_session, document)) == 2


def test_remove_deletes_only_the_exact_lesson(db_session):
    document, _, _, teacher, lesson = _seed_correction_document(db_session)
    other = Lesson(
        group_id=lesson.group_id,
        document_id=document.id,
        module_id=lesson.module_id,
        weekday=1,
        pair_number=2,
        starts_at=time(9, 50),
        ends_at=time(11, 25),
        subject="Финансы",
        lesson_kind=LessonKind.SEMINAR,
        teacher=teacher,
        room="209",
        week_type=None,
        subgroup=0,
        date_constraint_raw=None,
        cell_raw="Финансы (с)",
        cell_key="1:3:3",
        valid_from=date(2026, 9, 1),
        valid_to=date(2026, 11, 1),
        specific_dates=[],
    )
    db_session.add(other)
    db_session.flush()
    before = lesson_state(lesson, p_doc_id=str(document.p_doc_id))

    result = apply_document_corrections(
        db_session,
        document,
        _corrections(
            document,
            _correction("remove", expected_before=before),
        ),
    )

    assert result == CorrectionResult(added=0, replaced=0, removed=1)
    assert _persisted_lessons(db_session, document) == [other]


def test_add_creates_lesson_with_manual_provenance(db_session):
    document, _, _, teacher, lesson = _seed_correction_document(db_session)
    after = replace(
        lesson_state(lesson, p_doc_id=str(document.p_doc_id)),
        weekday=2,
        pair_number=3,
        starts_at=time(11, 55),
        ends_at=time(13, 30),
        subject="Финансы",
        teacher=teacher.full_name,
        room="401",
        date_constraint_raw="по 30.09",
        specific_dates=(),
        cell_raw="Финансы (л) Иванова И.И. ауд.401",
    )

    result = apply_document_corrections(
        db_session,
        document,
        _corrections(
            document,
            _correction(
                "add",
                operation_id="add-reviewed-finance",
                after=after,
            ),
        ),
    )

    added = _persisted_lessons(db_session, document)[1]
    assert result == CorrectionResult(added=1, replaced=0, removed=0)
    assert added.document_id == document.id
    assert added.cell_key == "manual:add-reviewed-finance"
    assert added.cell_raw == after.cell_raw
    assert lesson_state(added, p_doc_id="14159") == after


def test_missing_group_fails_without_creating_group(db_session):
    document, _, _, _, lesson = _seed_correction_document(db_session)
    before_groups = list(db_session.scalars(select(Group).order_by(Group.id)))
    after = replace(
        lesson_state(lesson, p_doc_id=str(document.p_doc_id)),
        group=GroupIdentity(
            level="master",
            course=2,
            number=None,
            program="Несуществующая программа",
        ),
        weekday=2,
        pair_number=3,
        subject="Финансы",
    )

    with pytest.raises(ReviewValidationError, match="group.*not found"):
        apply_document_corrections(
            db_session,
            document,
            _corrections(document, _correction("add", after=after)),
        )

    assert list(db_session.scalars(select(Group).order_by(Group.id))) == before_groups
    assert len(_persisted_lessons(db_session, document)) == 1


def test_missing_document_module_fails_without_creating_module(db_session):
    document, _, _, _, lesson = _seed_correction_document(db_session)
    before_modules = list(db_session.scalars(select(Module).order_by(Module.id)))
    after = replace(
        lesson_state(lesson, p_doc_id=str(document.p_doc_id)),
        weekday=2,
        pair_number=3,
        subject="Финансы",
        module=ModuleIdentity(
            date_from=date(2027, 2, 1),
            date_to=date(2027, 4, 1),
        ),
        valid_from=date(2027, 2, 1),
        valid_to=date(2027, 4, 1),
    )

    with pytest.raises(ReviewValidationError, match="module.*not found"):
        apply_document_corrections(
            db_session,
            document,
            _corrections(document, _correction("add", after=after)),
        )

    assert list(db_session.scalars(select(Module).order_by(Module.id))) == before_modules
    assert len(_persisted_lessons(db_session, document)) == 1


def test_add_reuses_exact_canonical_teacher_without_duplicate(db_session):
    document, _, _, teacher, lesson = _seed_correction_document(db_session)
    after = replace(
        lesson_state(lesson, p_doc_id=str(document.p_doc_id)),
        weekday=2,
        pair_number=3,
        subject="Финансы",
        cell_raw="Финансы (л) Иванова И.И.",
    )

    apply_document_corrections(
        db_session,
        document,
        _corrections(document, _correction("add", after=after)),
    )

    teachers = list(db_session.scalars(select(Teacher).order_by(Teacher.id)))
    assert teachers == [teacher]
    assert _persisted_lessons(db_session, document)[1].teacher_id == teacher.id


def test_teacher_spelling_variant_cannot_create_duplicate_person(db_session):
    document, _, _, teacher, lesson = _seed_correction_document(db_session)
    after = replace(
        lesson_state(lesson, p_doc_id=str(document.p_doc_id)),
        weekday=2,
        pair_number=3,
        subject="Финансы",
        teacher="Иванова И. И.",
    )

    with pytest.raises(ReviewValidationError, match="teacher spelling"):
        apply_document_corrections(
            db_session,
            document,
            _corrections(document, _correction("add", after=after)),
        )

    assert list(db_session.scalars(select(Teacher))) == [teacher]
    assert len(_persisted_lessons(db_session, document)) == 1


def test_unknown_teacher_is_created_once_like_the_importer(db_session):
    document, _, _, _, lesson = _seed_correction_document(db_session)
    after = replace(
        lesson_state(lesson, p_doc_id=str(document.p_doc_id)),
        weekday=2,
        pair_number=3,
        subject="Финансы",
        teacher="Новая Н.Н.",
    )

    apply_document_corrections(
        db_session,
        document,
        _corrections(document, _correction("add", after=after)),
    )

    teachers = list(db_session.scalars(select(Teacher).order_by(Teacher.id)))
    assert [row.full_name for row in teachers] == ["Иванова И.И.", "Новая Н.Н."]


@pytest.mark.parametrize(
    ("p_doc_id", "sha256", "message"),
    [
        ("99999", "a" * 64, "document id"),
        ("14159", "b" * 64, "changed and requires review"),
    ],
)
def test_corrections_require_exact_document_id_and_sha256(
    db_session, p_doc_id, sha256, message
):
    document, _, _, _, lesson = _seed_correction_document(db_session)
    before = lesson_state(lesson, p_doc_id=str(document.p_doc_id))

    with pytest.raises(ReviewValidationError, match=message):
        apply_document_corrections(
            db_session,
            document,
            _corrections(
                document,
                _correction(
                    "replace",
                    expected_before=before,
                    after=replace(before, room="209"),
                ),
                p_doc_id=p_doc_id,
                sha256=sha256,
            ),
        )

    db_session.refresh(lesson)
    assert lesson.room == "118"


def test_duplicate_exact_signature_is_review_error_not_integrity_error(db_session):
    document, _, _, _, lesson = _seed_correction_document(db_session)
    after = lesson_state(lesson, p_doc_id=str(document.p_doc_id))

    with pytest.raises(ReviewValidationError, match="duplicate exact signature"):
        apply_document_corrections(
            db_session,
            document,
            _corrections(document, _correction("add", after=after)),
        )

    assert len(_persisted_lessons(db_session, document)) == 1


def test_duplicate_database_slot_is_review_error_and_session_stays_usable(db_session):
    document, _, _, _, lesson = _seed_correction_document(db_session)
    after = replace(
        lesson_state(lesson, p_doc_id=str(document.p_doc_id)),
        room="209",
        teacher=None,
        cell_raw="same unique slot, different reviewed content",
    )

    with pytest.raises(ReviewValidationError, match="database constraint"):
        apply_document_corrections(
            db_session,
            document,
            _corrections(document, _correction("add", after=after)),
        )

    assert len(_persisted_lessons(db_session, document)) == 1
    assert db_session.scalar(select(ScheduleDocument).where(
        ScheduleDocument.id == document.id
    )) is document


def test_two_operation_failure_rolls_back_first_operation_inside_function(db_session):
    document, _, _, _, lesson = _seed_correction_document(db_session)
    before = lesson_state(lesson, p_doc_id=str(document.p_doc_id))
    replaced = replace(before, room="209", cell_raw="reviewed room 209")
    stale = replace(before, room="999")
    operations = (
        _correction(
            "replace",
            operation_id="first-replace",
            expected_before=before,
            after=replaced,
        ),
        _correction(
            "remove",
            operation_id="second-stale-remove",
            expected_before=stale,
        ),
    )

    with pytest.raises(ReviewValidationError, match="matched 0 lessons"):
        apply_document_corrections(
            db_session,
            document,
            _corrections(document, *operations),
        )

    persisted = db_session.scalar(select(Lesson).where(Lesson.id == lesson.id))
    assert persisted.room == "118"
    assert persisted.cell_raw == before.cell_raw
    assert persisted.cell_key == "1:2:3"
    assert db_session.scalar(select(ScheduleDocument).where(
        ScheduleDocument.id == document.id
    )) is document


def test_flush_failure_rolls_back_prior_operation_and_is_review_error(db_session):
    document, _, _, _, lesson = _seed_correction_document(db_session)
    before = lesson_state(lesson, p_doc_id=str(document.p_doc_id))
    first_add = replace(
        before,
        weekday=2,
        pair_number=3,
        subject="Финансы",
        room="209",
        cell_raw="Финансы (с)",
    )
    conflicting_add = replace(
        before,
        room="401",
        teacher=None,
        cell_raw="same DB slot as original",
    )

    with pytest.raises(ReviewValidationError, match="database constraint"):
        apply_document_corrections(
            db_session,
            document,
            _corrections(
                document,
                _correction(
                    "add", operation_id="first-valid-add", after=first_add
                ),
                _correction(
                    "add", operation_id="second-conflict", after=conflicting_add
                ),
            ),
        )

    assert _persisted_lessons(db_session, document) == [lesson]
    assert db_session.scalar(select(Group).where(Group.id == lesson.group_id)) is not None


def test_result_counts_add_replace_and_remove(db_session):
    document, _, _, _, first = _seed_correction_document(db_session)
    second = Lesson(
        group_id=first.group_id,
        document_id=document.id,
        module_id=first.module_id,
        weekday=1,
        pair_number=2,
        starts_at=time(9, 50),
        ends_at=time(11, 25),
        subject="Финансы",
        lesson_kind=LessonKind.SEMINAR,
        teacher_id=first.teacher_id,
        room="209",
        week_type=None,
        subgroup=0,
        date_constraint_raw=None,
        cell_raw="Финансы (с)",
        cell_key="1:3:3",
        valid_from=date(2026, 9, 1),
        valid_to=date(2026, 11, 1),
        specific_dates=[],
    )
    db_session.add(second)
    db_session.flush()
    first_before = lesson_state(first, p_doc_id="14159")
    second_before = lesson_state(second, p_doc_id="14159")
    added = replace(
        first_before,
        weekday=2,
        pair_number=3,
        subject="Банковское дело",
        cell_raw="Банковское дело (л)",
    )

    result = apply_document_corrections(
        db_session,
        document,
        _corrections(
            document,
            _correction(
                "replace",
                operation_id="replace-first",
                expected_before=first_before,
                after=replace(first_before, room="401"),
            ),
            _correction(
                "remove",
                operation_id="remove-second",
                expected_before=second_before,
            ),
            _correction("add", operation_id="add-third", after=added),
        ),
    )

    assert result == CorrectionResult(added=1, replaced=1, removed=1)
    assert len(_persisted_lessons(db_session, document)) == 2


def test_replace_does_not_delete_now_unused_related_rows(db_session):
    document, old_group, old_module, old_teacher, lesson = (
        _seed_correction_document(db_session)
    )
    new_group = Group(
        course=2,
        number=None,
        level=EducationLevel.MASTER,
        program="Экономическая аналитика",
    )
    new_module = Module(
        document=document,
        name="II модуль",
        date_from=date(2026, 11, 2),
        date_to=date(2027, 1, 10),
    )
    new_teacher = Teacher(full_name="Петрова П.П.")
    db_session.add_all([new_group, new_module, new_teacher])
    db_session.flush()
    before = lesson_state(lesson, p_doc_id="14159")
    after = replace(
        before,
        group=GroupIdentity("master", 2, None, "Экономическая аналитика"),
        module=ModuleIdentity(date(2026, 11, 2), date(2027, 1, 10)),
        teacher="Петрова П.П.",
        valid_from=date(2026, 11, 2),
        valid_to=date(2027, 1, 10),
    )

    apply_document_corrections(
        db_session,
        document,
        _corrections(
            document,
            _correction("replace", expected_before=before, after=after),
        ),
    )

    assert db_session.get(Group, old_group.id) is old_group
    assert db_session.get(Module, old_module.id) is old_module
    assert db_session.get(Teacher, old_teacher.id) is old_teacher


def test_reapplying_same_add_fails_closed_without_duplicate(db_session):
    document, _, _, _, lesson = _seed_correction_document(db_session)
    after = replace(
        lesson_state(lesson, p_doc_id="14159"),
        weekday=2,
        pair_number=3,
        subject="Финансы",
        cell_raw="Финансы (л)",
    )
    corrections = _corrections(
        document,
        _correction("add", operation_id="repeat-safe-add", after=after),
    )

    apply_document_corrections(db_session, document, corrections)
    with pytest.raises(ReviewValidationError, match="duplicate exact signature"):
        apply_document_corrections(db_session, document, corrections)

    assert len(_persisted_lessons(db_session, document)) == 2
