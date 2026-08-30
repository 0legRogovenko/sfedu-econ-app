import difflib
import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import date, time
from pathlib import Path
from types import MappingProxyType
from typing import Literal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.models import (
    EducationLevel,
    ExamEvent,
    Group,
    Lesson,
    LessonKind,
    Module,
    ScheduleDocument,
    Teacher,
    WeekType,
)


_EMPTY_TEXT = r"\0"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_DOCUMENT_ID_RE = re.compile(r"^[1-9][0-9]*$")
_CORRECTION_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_MAX_CORRECTION_ID_LENGTH = 43  # len("manual:") + id must fit Lesson.cell_key(50)
_MAX_SOURCE_PAGE = 10_000
_MAX_SUBGROUP = 99
_MAX_COURSE = 9
_MAX_PAIR_NUMBER = 7


class ReviewValidationError(ValueError):
    """The reviewed schedule bundle is malformed or stale."""


def _canonical_document_id(p_doc_id: str | int) -> str:
    if isinstance(p_doc_id, bool):
        raise ReviewValidationError(f"invalid document id {p_doc_id!r}")
    if isinstance(p_doc_id, int):
        if p_doc_id <= 0:
            raise ReviewValidationError(f"invalid document id {p_doc_id!r}")
        return str(p_doc_id)
    if isinstance(p_doc_id, str) and _DOCUMENT_ID_RE.fullmatch(p_doc_id):
        return p_doc_id
    raise ReviewValidationError(f"invalid document id {p_doc_id!r}")


def _encode_text(value: str | None) -> str:
    if value is None:
        return ""
    if value == "":
        return _EMPTY_TEXT
    return (
        value.replace("\\", "\\\\")
        .replace("|", "\\|")
        .replace("/", "\\/")
        .replace("\n", "\\n")
        .replace("\r", "\\r")
    )


@dataclass(frozen=True)
class GroupIdentity:
    level: str
    course: int
    number: str | None
    program: str | None


@dataclass(frozen=True)
class ModuleIdentity:
    date_from: date
    date_to: date


@dataclass(frozen=True)
class LessonState:
    p_doc_id: str
    group: GroupIdentity
    weekday: int
    pair_number: int
    starts_at: time
    ends_at: time
    subject: str
    lesson_kind: str | None
    teacher: str | None
    room: str | None
    week_type: str | None
    subgroup: int
    module: ModuleIdentity | None
    date_constraint_raw: str | None
    valid_from: date | None
    valid_to: date | None
    specific_dates: tuple[date, ...]
    cell_raw: str | None


@dataclass(frozen=True)
class CorrectionOperation:
    id: str
    operation: Literal["add", "replace", "remove"]
    page: int
    evidence: str
    expected_before: LessonState | None
    after: LessonState | None


@dataclass(frozen=True)
class DocumentCorrections:
    p_doc_id: str
    sha256: str
    operations: tuple[CorrectionOperation, ...]


@dataclass(frozen=True)
class CorrectionRegistry:
    documents: Mapping[str, DocumentCorrections]

    def manages(self, p_doc_id: str | int) -> bool:
        return _canonical_document_id(p_doc_id) in self.documents

    def guard_source(self, p_doc_id: str | int, sha256: str) -> None:
        key = _canonical_document_id(p_doc_id)
        document = self.documents.get(key)
        if document is not None and document.sha256 != sha256:
            raise ReviewValidationError(
                f"document {key} changed and requires review"
            )


@dataclass(frozen=True)
class CorrectionResult:
    added: int = 0
    replaced: int = 0
    removed: int = 0


@dataclass(frozen=True)
class ReviewedDocument:
    p_doc_id: str
    sha256: str
    lesson_hash: str
    signatures: tuple[str, ...]


def _require_clean_session(session: Session, *, context: str) -> None:
    if session.new or session.dirty or session.deleted:
        raise ReviewValidationError(
            f"{context} requires a clean session boundary"
        )


def lesson_state(lesson: Lesson, *, p_doc_id: str) -> LessonState:
    return LessonState(
        p_doc_id=p_doc_id,
        group=GroupIdentity(
            level=lesson.group.level.value,
            course=lesson.group.course,
            number=lesson.group.number,
            program=lesson.group.program,
        ),
        weekday=lesson.weekday,
        pair_number=lesson.pair_number,
        starts_at=lesson.starts_at,
        ends_at=lesson.ends_at,
        subject=lesson.subject,
        lesson_kind=lesson.lesson_kind.value if lesson.lesson_kind else None,
        teacher=lesson.teacher.full_name if lesson.teacher else None,
        room=lesson.room,
        week_type=lesson.week_type.value if lesson.week_type else None,
        subgroup=lesson.subgroup,
        module=(
            ModuleIdentity(
                date_from=lesson.module.date_from,
                date_to=lesson.module.date_to,
            )
            if lesson.module
            else None
        ),
        date_constraint_raw=lesson.date_constraint_raw,
        valid_from=lesson.valid_from,
        valid_to=lesson.valid_to,
        specific_dates=tuple(
            item if isinstance(item, date) else date.fromisoformat(item)
            for item in lesson.specific_dates
        ),
        cell_raw=lesson.cell_raw,
    )


def state_signature(state: LessonState) -> str:
    group = state.group
    module = state.module
    specific_dates = ",".join(str(item) for item in sorted(state.specific_dates))
    return "|".join(
        (
            f"документ={state.p_doc_id}",
            f"группа={group.level}/{group.course}/{_encode_text(group.number)}/"
            f"{_encode_text(group.program)}",
            f"день={state.weekday}",
            f"пара={state.pair_number}",
            f"начало={state.starts_at}",
            f"конец={state.ends_at}",
            f"предмет={_encode_text(state.subject)}",
            f"вид={state.lesson_kind or ''}",
            f"препод={_encode_text(state.teacher)}",
            f"ауд={_encode_text(state.room)}",
            f"неделя={state.week_type or ''}",
            f"п/г={state.subgroup}",
            (
                f"модуль={module.date_from}..{module.date_to}"
                if module
                else "модуль="
            ),
            f"даты={_encode_text(state.date_constraint_raw)}",
            f"с={state.valid_from or ''}",
            f"по={state.valid_to or ''}",
            f"конкретные={specific_dates}",
        )
    )


def _matching_lessons(
    session: Session,
    document: ScheduleDocument,
    state: LessonState,
) -> list[Lesson]:
    candidates = session.scalars(
        select(Lesson).where(Lesson.document_id == document.id)
    ).all()
    return [
        lesson
        for lesson in candidates
        if lesson_state(lesson, p_doc_id=str(document.p_doc_id)) == state
    ]


def _matching_signatures(
    session: Session,
    document: ScheduleDocument,
    state: LessonState,
) -> list[Lesson]:
    expected = state_signature(state)
    candidates = session.scalars(
        select(Lesson).where(Lesson.document_id == document.id)
    ).all()
    return [
        lesson
        for lesson in candidates
        if state_signature(
            lesson_state(lesson, p_doc_id=str(document.p_doc_id))
        )
        == expected
    ]


def _resolve_group(session: Session, identity: GroupIdentity) -> Group:
    try:
        level = EducationLevel(identity.level)
    except ValueError as exc:
        raise ReviewValidationError(
            f"invalid education level {identity.level!r}"
        ) from exc
    groups = session.scalars(
        select(Group).where(
            Group.level == level,
            Group.course == identity.course,
            (
                Group.number.is_(None)
                if identity.number is None
                else Group.number == identity.number
            ),
            (
                Group.program.is_(None)
                if identity.program is None
                else Group.program == identity.program
            ),
        )
    ).all()
    if len(groups) != 1:
        raise ReviewValidationError(
            "group not found by exact natural identity"
            if not groups
            else "group identity is ambiguous"
        )
    return groups[0]


def _resolve_module(
    session: Session,
    document: ScheduleDocument,
    identity: ModuleIdentity | None,
) -> Module | None:
    if identity is None:
        return None
    modules = session.scalars(
        select(Module).where(
            Module.document_id == document.id,
            Module.date_from == identity.date_from,
            Module.date_to == identity.date_to,
        )
    ).all()
    if len(modules) != 1:
        raise ReviewValidationError(
            "module not found by exact document and date range"
            if not modules
            else "module identity is ambiguous"
        )
    return modules[0]


def _teacher_spelling_key(name: str) -> str:
    folded = name.casefold().replace("ё", "е")
    return "".join(character for character in folded if character.isalnum())


def _resolve_teacher(session: Session, name: str | None) -> Teacher | None:
    if name is None:
        return None
    spelling_key = _teacher_spelling_key(name)
    if not spelling_key:
        raise ReviewValidationError(
            "teacher spelling must contain letters or digits"
        )
    exact = session.scalars(
        select(Teacher).where(Teacher.full_name == name)
    ).all()
    if len(exact) == 1:
        return exact[0]
    if len(exact) > 1:
        raise ReviewValidationError(f"teacher {name!r} is ambiguous")

    variant = [
        teacher
        for teacher in session.scalars(select(Teacher)).all()
        if _teacher_spelling_key(teacher.full_name) == spelling_key
    ]
    if variant:
        raise ReviewValidationError(
            f"teacher spelling {name!r} would duplicate {variant[0].full_name!r}"
        )
    if len(name) > 200:
        raise ReviewValidationError("teacher name exceeds database limit")
    teacher = Teacher(full_name=name)
    session.add(teacher)
    session.flush()
    return teacher


def _manual_cell_key(operation_id: str) -> str:
    if (
        len(operation_id) > _MAX_CORRECTION_ID_LENGTH
        or _CORRECTION_ID_RE.fullmatch(operation_id) is None
    ):
        raise ReviewValidationError(f"unsafe correction id {operation_id!r}")
    value = f"manual:{operation_id}"
    if len(value) > 50:  # defensive mirror of Lesson.cell_key String(50)
        raise ReviewValidationError("manual provenance exceeds database limit")
    return value


def _write_state(
    session: Session,
    document: ScheduleDocument,
    target: Lesson,
    state: LessonState,
    operation_id: str,
) -> None:
    if state.p_doc_id != str(document.p_doc_id):
        raise ReviewValidationError(
            f"lesson state document {state.p_doc_id} does not match document "
            f"{document.p_doc_id}"
        )
    group = _resolve_group(session, state.group)
    module = _resolve_module(session, document, state.module)
    teacher = _resolve_teacher(session, state.teacher)
    try:
        lesson_kind = (
            LessonKind(state.lesson_kind) if state.lesson_kind is not None else None
        )
        week_type = WeekType(state.week_type) if state.week_type is not None else None
    except ValueError as exc:
        raise ReviewValidationError("invalid lesson enum value") from exc

    target.document_id = document.id
    target.group = group
    target.module = module
    target.weekday = state.weekday
    target.pair_number = state.pair_number
    target.starts_at = state.starts_at
    target.ends_at = state.ends_at
    target.subject = state.subject
    target.lesson_kind = lesson_kind
    target.teacher = teacher
    target.room = state.room
    target.week_type = week_type
    target.subgroup = state.subgroup
    target.date_constraint_raw = state.date_constraint_raw
    target.cell_raw = state.cell_raw
    target.cell_key = _manual_cell_key(operation_id)
    target.valid_from = state.valid_from
    target.valid_to = state.valid_to
    target.specific_dates = [item.isoformat() for item in state.specific_dates]


def apply_document_corrections(
    session: Session,
    document: ScheduleDocument,
    corrections: DocumentCorrections,
) -> CorrectionResult:
    """Apply one document's reviewed operations inside an owned savepoint."""
    document_key = _canonical_document_id(document.p_doc_id)
    correction_key = _canonical_document_id(corrections.p_doc_id)
    if correction_key != document_key:
        raise ReviewValidationError(
            f"correction document id {correction_key} does not match {document_key}"
        )
    if corrections.sha256 != document.sha256:
        raise ReviewValidationError(
            f"document {document_key} changed and requires review"
        )

    result = CorrectionResult()
    if not corrections.operations:
        return result
    _require_clean_session(session, context="manual corrections")
    current_operation: CorrectionOperation | None = None
    try:
        with session.begin_nested():
            for current_operation in corrections.operations:
                if current_operation.operation in {"replace", "remove"}:
                    expected = current_operation.expected_before
                    if expected is None:
                        raise ReviewValidationError(
                            f"correction {current_operation.id} has no expected state"
                        )
                    matches = _matching_lessons(session, document, expected)
                    if len(matches) != 1:
                        raise ReviewValidationError(
                            f"correction {current_operation.id} matched "
                            f"{len(matches)} lessons"
                        )
                    target = matches[0]
                    if current_operation.operation == "remove":
                        session.delete(target)
                        result = replace(result, removed=result.removed + 1)
                    else:
                        after = current_operation.after
                        if after is None:
                            raise ReviewValidationError(
                                f"correction {current_operation.id} has no after state"
                            )
                        _write_state(
                            session,
                            document,
                            target,
                            after,
                            current_operation.id,
                        )
                        result = replace(result, replaced=result.replaced + 1)
                elif current_operation.operation == "add":
                    after = current_operation.after
                    if after is None:
                        raise ReviewValidationError(
                            f"correction {current_operation.id} has no after state"
                        )
                    if _matching_signatures(session, document, after):
                        raise ReviewValidationError(
                            f"correction {current_operation.id} duplicate exact signature"
                        )
                    target = Lesson(document_id=document.id)
                    _write_state(
                        session,
                        document,
                        target,
                        after,
                        current_operation.id,
                    )
                    session.add(target)
                    result = replace(result, added=result.added + 1)
                else:
                    raise ReviewValidationError(
                        f"invalid correction operation {current_operation.operation!r}"
                    )
                session.flush()
    except IntegrityError as exc:
        operation_id = current_operation.id if current_operation else "unknown"
        raise ReviewValidationError(
            f"correction {operation_id} violates a database constraint"
        ) from exc
    return result


_REGISTRY_KEYS = frozenset({"version", "documents"})
_DOCUMENT_KEYS = frozenset({"p_doc_id", "sha256", "operations"})
_OPERATION_KEYS = frozenset(
    {"id", "operation", "page", "evidence", "expected_before", "after"}
)
_OPERATION_REQUIRED_KEYS = frozenset({"id", "operation", "page", "evidence"})
_STATE_KEYS = frozenset(
    {
        "p_doc_id",
        "group",
        "weekday",
        "pair_number",
        "starts_at",
        "ends_at",
        "subject",
        "lesson_kind",
        "teacher",
        "room",
        "week_type",
        "subgroup",
        "module",
        "date_constraint_raw",
        "valid_from",
        "valid_to",
        "specific_dates",
        "cell_raw",
    }
)
_GROUP_KEYS = frozenset({"level", "course", "number", "program"})
_MODULE_KEYS = frozenset({"date_from", "date_to"})


def _object(value, *, context: str) -> dict:
    if not isinstance(value, dict):
        raise ReviewValidationError(f"{context} must be an object")
    return value


def _check_keys(
    value: dict,
    *,
    context: str,
    allowed: frozenset[str],
    required: frozenset[str] | None = None,
) -> None:
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise ReviewValidationError(
            f"{context}: unknown keys: {', '.join(unknown)}"
        )
    missing = sorted((required if required is not None else allowed) - set(value))
    if missing:
        raise ReviewValidationError(
            f"{context}: missing keys: {', '.join(missing)}"
        )


def _string(value, *, context: str, blank: bool = True) -> str:
    if not isinstance(value, str):
        raise ReviewValidationError(f"{context} must be a string")
    if not blank and not value.strip():
        raise ReviewValidationError(f"{context} must not be blank")
    return value


def _optional_string(value, *, context: str) -> str | None:
    if value is None:
        return None
    return _string(value, context=context)


def _integer(value, *, context: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ReviewValidationError(f"{context} must be an integer")
    if not minimum <= value <= maximum:
        raise ReviewValidationError(
            f"{context} must be between {minimum} and {maximum}"
        )
    return value


def _iso_date(value, *, context: str, optional: bool = False) -> date | None:
    if optional and value is None:
        return None
    if not isinstance(value, str):
        raise ReviewValidationError(f"{context}: invalid ISO date")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ReviewValidationError(f"{context}: invalid ISO date") from exc


def _iso_time(value, *, context: str) -> time:
    if not isinstance(value, str):
        raise ReviewValidationError(f"{context}: invalid ISO time")
    try:
        parsed = time.fromisoformat(value)
    except ValueError as exc:
        raise ReviewValidationError(f"{context}: invalid ISO time") from exc
    if parsed.utcoffset() is not None:
        raise ReviewValidationError(
            f"{context}: ISO time must not contain a timezone offset"
        )
    if parsed.microsecond != 0:
        raise ReviewValidationError(
            f"{context}: ISO time must not contain microseconds"
        )
    return parsed


def _enum_value(value, enum_type, *, context: str, optional: bool = False):
    if optional and value is None:
        return None
    if not isinstance(value, str):
        raise ReviewValidationError(f"{context} must be a string or null")
    valid = {member.value for member in enum_type}
    if value not in valid:
        raise ReviewValidationError(f"invalid {context}: {value}")
    return value


def _parse_group(value) -> GroupIdentity:
    payload = _object(value, context="group identity")
    _check_keys(payload, context="group identity", allowed=_GROUP_KEYS)
    level = _enum_value(
        payload["level"], EducationLevel, context="education level"
    )
    course = _integer(
        payload["course"], context="course", minimum=1, maximum=_MAX_COURSE
    )
    number = _optional_string(payload["number"], context="group number")
    program = _optional_string(payload["program"], context="group program")
    if level == EducationLevel.BACHELOR.value:
        if number is None or not number.strip() or program is not None:
            raise ReviewValidationError(
                "bachelor group requires number and forbids program"
            )
    elif number is not None or program is None or not program.strip():
        raise ReviewValidationError(
            "master group requires program and forbids number"
        )
    return GroupIdentity(
        level=level,
        course=course,
        number=number,
        program=program,
    )


def _parse_module(value) -> ModuleIdentity | None:
    if value is None:
        return None
    payload = _object(value, context="module identity")
    _check_keys(payload, context="module identity", allowed=_MODULE_KEYS)
    date_from = _iso_date(payload["date_from"], context="module date_from")
    date_to = _iso_date(payload["date_to"], context="module date_to")
    assert date_from is not None and date_to is not None
    if date_from > date_to:
        raise ReviewValidationError("module date range is invalid")
    return ModuleIdentity(date_from=date_from, date_to=date_to)


def _parse_state(value, *, p_doc_id: str) -> LessonState:
    payload = _object(value, context="lesson state")
    _check_keys(payload, context="lesson state", allowed=_STATE_KEYS)
    state_document = _string(payload["p_doc_id"], context="lesson p_doc_id")
    if state_document != p_doc_id:
        raise ReviewValidationError(
            f"lesson state document {state_document} does not match document {p_doc_id}"
        )
    starts_at = _iso_time(payload["starts_at"], context="starts_at")
    ends_at = _iso_time(payload["ends_at"], context="ends_at")
    if starts_at >= ends_at:
        raise ReviewValidationError("lesson time range is invalid")
    valid_from = _iso_date(
        payload["valid_from"], context="valid_from", optional=True
    )
    valid_to = _iso_date(payload["valid_to"], context="valid_to", optional=True)
    if valid_from is not None and valid_to is not None and valid_from > valid_to:
        raise ReviewValidationError("validity date range is invalid")
    raw_specific_dates = payload["specific_dates"]
    if not isinstance(raw_specific_dates, list):
        raise ReviewValidationError("specific_dates must be a list")
    specific_dates = tuple(
        _iso_date(item, context="specific_dates") for item in raw_specific_dates
    )
    if len(set(specific_dates)) != len(specific_dates):
        raise ReviewValidationError("specific_dates must not contain duplicates")
    weekday = _integer(
        payload["weekday"], context="weekday", minimum=0, maximum=5
    )
    module = _parse_module(payload["module"])
    for specific_date in specific_dates:
        assert specific_date is not None
        if specific_date.weekday() != weekday:
            raise ReviewValidationError(
                f"specific date {specific_date} does not match weekday {weekday}"
            )
    if module is not None:
        if valid_from is None or valid_to is None:
            raise ReviewValidationError(
                "module requires both valid_from and valid_to"
            )
        if valid_from is not None and not (
            module.date_from <= valid_from <= module.date_to
        ):
            raise ReviewValidationError(
                f"valid_from {valid_from} is outside module"
            )
        if valid_to is not None and not (
            module.date_from <= valid_to <= module.date_to
        ):
            raise ReviewValidationError(f"valid_to {valid_to} is outside module")
        for specific_date in specific_dates:
            assert specific_date is not None
            if not module.date_from <= specific_date <= module.date_to:
                raise ReviewValidationError(
                    f"specific date {specific_date} is outside module"
                )
    for specific_date in specific_dates:
        assert specific_date is not None
        if valid_from is not None and specific_date < valid_from:
            raise ReviewValidationError(
                f"specific date {specific_date} is before valid_from {valid_from}"
            )
        if valid_to is not None and specific_date > valid_to:
            raise ReviewValidationError(
                f"specific date {specific_date} is after valid_to {valid_to}"
            )
    subject = _string(payload["subject"], context="subject", blank=False)
    teacher = _optional_string(payload["teacher"], context="teacher")
    if teacher is not None and not _teacher_spelling_key(teacher):
        raise ReviewValidationError(
            "teacher spelling must contain letters or digits"
        )
    return LessonState(
        p_doc_id=state_document,
        group=_parse_group(payload["group"]),
        weekday=weekday,
        pair_number=_integer(
            payload["pair_number"],
            context="pair number",
            minimum=1,
            maximum=_MAX_PAIR_NUMBER,
        ),
        starts_at=starts_at,
        ends_at=ends_at,
        subject=subject,
        lesson_kind=_enum_value(
            payload["lesson_kind"],
            LessonKind,
            context="lesson kind",
            optional=True,
        ),
        teacher=teacher,
        room=_optional_string(payload["room"], context="room"),
        week_type=_enum_value(
            payload["week_type"],
            WeekType,
            context="week type",
            optional=True,
        ),
        subgroup=_integer(
            payload["subgroup"],
            context="subgroup",
            minimum=0,
            maximum=_MAX_SUBGROUP,
        ),
        module=module,
        date_constraint_raw=_optional_string(
            payload["date_constraint_raw"], context="date_constraint_raw"
        ),
        valid_from=valid_from,
        valid_to=valid_to,
        specific_dates=specific_dates,
        cell_raw=_optional_string(payload["cell_raw"], context="cell_raw"),
    )


def _parse_operation(value, *, p_doc_id: str) -> CorrectionOperation:
    payload = _object(value, context="correction")
    raw_id = payload.get("id")
    context = (
        f"correction {raw_id}"
        if isinstance(raw_id, str) and raw_id
        else "correction"
    )
    _check_keys(
        payload,
        context=context,
        allowed=_OPERATION_KEYS,
        required=_OPERATION_REQUIRED_KEYS,
    )
    correction_id = _string(raw_id, context="correction id")
    if (
        len(correction_id) > _MAX_CORRECTION_ID_LENGTH
        or _CORRECTION_ID_RE.fullmatch(correction_id) is None
    ):
        raise ReviewValidationError(f"unsafe correction id {correction_id!r}")
    operation = _string(payload["operation"], context="operation")
    if operation not in {"add", "replace", "remove"}:
        raise ReviewValidationError(f"invalid correction operation {operation!r}")
    page = _integer(
        payload["page"],
        context="page",
        minimum=1,
        maximum=_MAX_SOURCE_PAGE,
    )
    evidence = _string(payload["evidence"], context="evidence", blank=False)
    expected_raw = payload.get("expected_before")
    after_raw = payload.get("after")
    if operation == "add":
        if expected_raw is not None:
            raise ReviewValidationError("add forbids expected_before")
        if after_raw is None:
            raise ReviewValidationError("add requires after")
    elif operation == "replace":
        if expected_raw is None or after_raw is None:
            raise ReviewValidationError("replace requires expected_before and after")
    else:
        if expected_raw is None:
            raise ReviewValidationError("remove requires expected_before")
        if after_raw is not None:
            raise ReviewValidationError("remove forbids after")
    return CorrectionOperation(
        id=correction_id,
        operation=operation,
        page=page,
        evidence=evidence,
        expected_before=(
            _parse_state(expected_raw, p_doc_id=p_doc_id)
            if expected_raw is not None
            else None
        ),
        after=(
            _parse_state(after_raw, p_doc_id=p_doc_id)
            if after_raw is not None
            else None
        ),
    )


def _parse_document(value) -> DocumentCorrections:
    payload = _object(value, context="document")
    raw_id = payload.get("p_doc_id")
    context = (
        f"document {raw_id}"
        if isinstance(raw_id, str) and raw_id
        else "document"
    )
    _check_keys(payload, context=context, allowed=_DOCUMENT_KEYS)
    p_doc_id = _string(raw_id, context="p_doc_id", blank=False)
    p_doc_id = _canonical_document_id(p_doc_id)
    sha256 = _string(payload["sha256"], context="sha256")
    if _SHA256_RE.fullmatch(sha256) is None:
        raise ReviewValidationError(f"document {p_doc_id}: invalid SHA-256")
    raw_operations = payload["operations"]
    if not isinstance(raw_operations, list):
        raise ReviewValidationError(f"document {p_doc_id}: operations must be a list")
    operations = tuple(
        _parse_operation(item, p_doc_id=p_doc_id) for item in raw_operations
    )
    return DocumentCorrections(
        p_doc_id=p_doc_id,
        sha256=sha256,
        operations=operations,
    )


def _json_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ReviewValidationError(f"duplicate JSON key {key}")
        result[key] = value
    return result


def load_correction_registry(path: str | Path) -> CorrectionRegistry:
    """Load a correction registry without accepting ambiguous or stale shapes."""
    try:
        payload = json.loads(
            Path(path).read_text(encoding="utf-8"),
            object_pairs_hook=_json_object,
        )
    except json.JSONDecodeError as exc:
        raise ReviewValidationError(f"invalid corrections JSON: {exc.msg}") from exc
    root = _object(payload, context="registry")
    _check_keys(root, context="registry", allowed=_REGISTRY_KEYS)
    version = root["version"]
    if isinstance(version, bool) or not isinstance(version, int):
        raise ReviewValidationError("correction version must be an integer")
    if version != 1:
        raise ReviewValidationError(f"unsupported correction version {version}")
    raw_documents = root["documents"]
    if not isinstance(raw_documents, list):
        raise ReviewValidationError("documents must be a list")

    documents: dict[str, DocumentCorrections] = {}
    correction_ids: set[str] = set()
    for raw_document in raw_documents:
        document = _parse_document(raw_document)
        if document.p_doc_id in documents:
            raise ReviewValidationError(
                f"duplicate document id {document.p_doc_id}"
            )
        for operation in document.operations:
            if operation.id in correction_ids:
                raise ReviewValidationError(
                    f"duplicate correction id {operation.id}"
                )
            correction_ids.add(operation.id)
        documents[document.p_doc_id] = document
    return CorrectionRegistry(documents=MappingProxyType(documents.copy()))


_MAX_DIFF_LINES = 40
_MAX_DIFF_LINE_BYTES = 500
_MAX_MISMATCH_BYTES = 8 * 1024


def _require_sha256(value: str, *, context: str) -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise ReviewValidationError(f"{context}: invalid SHA-256")
    return value


def _lesson_hash(signatures: tuple[str, ...]) -> str:
    payload = json.dumps(
        list(signatures),
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _validate_reviewed_metadata(reviewed: ReviewedDocument) -> str:
    if not isinstance(reviewed, ReviewedDocument):
        raise ReviewValidationError("reviewed document has invalid type")
    key = _canonical_document_id(reviewed.p_doc_id)
    if reviewed.p_doc_id != key:
        raise ReviewValidationError(
            f"reviewed document id {reviewed.p_doc_id!r} is not canonical"
        )
    _require_sha256(reviewed.sha256, context=f"document {key} source")
    _require_sha256(reviewed.lesson_hash, context=f"document {key} lesson hash")
    if not isinstance(reviewed.signatures, tuple) or not all(
        isinstance(item, str) for item in reviewed.signatures
    ):
        raise ReviewValidationError(
            f"document {key}: reviewed signatures must be a tuple of strings"
        )
    if _lesson_hash(reviewed.signatures) != reviewed.lesson_hash:
        raise ReviewValidationError(
            f"document {key}: reviewed lesson hash does not match signatures"
        )
    return key


def reviewed_document_output(
    session: Session,
    document: ScheduleDocument,
) -> ReviewedDocument:
    """Build the complete, deterministic lesson output for one source document."""
    _require_clean_session(session, context="reviewed schedule validation")
    key = _canonical_document_id(document.p_doc_id)
    sha256 = _require_sha256(
        document.sha256,
        context=f"document {key} source",
    )
    exam_id = session.scalar(
        select(ExamEvent.id)
        .where(ExamEvent.document_id == document.id)
        .limit(1)
    )
    if exam_id is not None:
        raise ReviewValidationError(
            f"document {key}: exams must remain empty"
        )
    lessons = session.scalars(
        select(Lesson).where(Lesson.document_id == document.id)
    ).all()
    signatures = tuple(
        sorted(
            state_signature(lesson_state(item, p_doc_id=key))
            for item in lessons
        )
    )
    return ReviewedDocument(
        p_doc_id=key,
        sha256=sha256,
        lesson_hash=_lesson_hash(signatures),
        signatures=signatures,
    )


def _bounded_unified_diff(
    expected: tuple[str, ...],
    actual: tuple[str, ...],
    *,
    p_doc_id: str,
    max_bytes: int,
) -> str:
    lines: list[str] = []
    byte_count = 0
    truncated = False
    marker = "... diff truncated ..."
    marker_bytes = len(marker.encode("utf-8"))
    diff = difflib.unified_diff(
        expected,
        actual,
        fromfile=f"reviewed/{p_doc_id}",
        tofile=f"actual/{p_doc_id}",
        lineterm="",
    )
    for index, raw_line in enumerate(diff):
        if index >= _MAX_DIFF_LINES:
            truncated = True
            break
        separator_bytes = 1 if lines else 0
        available = max_bytes - byte_count - separator_bytes - marker_bytes - 1
        if available <= 0:
            truncated = True
            break
        line, line_truncated = _truncate_utf8(
            raw_line,
            min(_MAX_DIFF_LINE_BYTES, available),
        )
        truncated = truncated or line_truncated
        required = len(line.encode("utf-8")) + separator_bytes
        lines.append(line)
        byte_count += required
    if truncated:
        separator_bytes = 1 if lines else 0
        if byte_count + separator_bytes + marker_bytes <= max_bytes:
            lines.append(marker)
    return "\n".join(lines)


def _truncate_utf8(value: str, max_bytes: int) -> tuple[str, bool]:
    encoded = value.encode("utf-8")
    if len(encoded) <= max_bytes:
        return value, False
    suffix = "..."
    suffix_bytes = len(suffix.encode("utf-8"))
    if max_bytes <= suffix_bytes:
        return "." * max_bytes, True
    prefix = encoded[: max_bytes - suffix_bytes].decode("utf-8", errors="ignore")
    return f"{prefix}{suffix}", True


def validate_reviewed_document(
    session: Session,
    document: ScheduleDocument,
    expected: ReviewedDocument,
) -> None:
    """Fail closed unless the whole imported document equals reviewed output.

    Authentication of the file that supplied ``expected`` belongs to Task 6;
    this boundary validates its internal consistency and the database result.
    """
    _require_clean_session(session, context="reviewed schedule validation")
    document_key = _canonical_document_id(document.p_doc_id)
    expected_key = _validate_reviewed_metadata(expected)
    if expected_key != document_key:
        raise ReviewValidationError(
            f"reviewed document id {expected_key} does not match {document_key}"
        )
    source_sha256 = _require_sha256(
        document.sha256,
        context=f"document {document_key} source",
    )
    if expected.sha256 != source_sha256:
        raise ReviewValidationError(
            f"document {document_key} changed and requires review"
        )

    actual = reviewed_document_output(session, document)
    if (
        actual.lesson_hash == expected.lesson_hash
        and actual.signatures == expected.signatures
    ):
        return
    mismatch = f"document {document_key}: reviewed schedule mismatch"
    diff_budget = _MAX_MISMATCH_BYTES - len(mismatch.encode("utf-8")) - 1
    diff = _bounded_unified_diff(
        expected.signatures,
        actual.signatures,
        p_doc_id=document_key,
        max_bytes=diff_budget,
    )
    suffix = f"\n{diff}" if diff else ""
    raise ReviewValidationError(f"{mismatch}{suffix}")


def _canonical_bundle_mapping(
    values: Mapping,
    *,
    context: str,
) -> dict[str, object]:
    if not isinstance(values, Mapping):
        raise ReviewValidationError(f"{context} must be a mapping")
    canonical: dict[str, object] = {}
    for raw_key, value in values.items():
        key = _canonical_document_id(raw_key)
        if key in canonical:
            raise ReviewValidationError(f"duplicate document id {key}")
        if raw_key != key:
            raise ReviewValidationError(
                f"{context} document id {raw_key!r} is not canonical"
            )
        canonical[key] = value
    return canonical


@dataclass(frozen=True)
class ReviewBundle:
    corrections: CorrectionRegistry
    reviewed_documents: Mapping[str, ReviewedDocument]

    def __post_init__(self) -> None:
        if not isinstance(self.corrections, CorrectionRegistry):
            raise ReviewValidationError("corrections must be a CorrectionRegistry")
        correction_documents = _canonical_bundle_mapping(
            self.corrections.documents,
            context="corrections",
        )
        reviewed_documents = _canonical_bundle_mapping(
            self.reviewed_documents,
            context="reviewed output",
        )
        if correction_documents.keys() != reviewed_documents.keys():
            raise ReviewValidationError(
                "correction and reviewed document key sets do not match"
            )
        frozen_corrections: dict[str, DocumentCorrections] = {}
        frozen_reviewed: dict[str, ReviewedDocument] = {}
        for key in sorted(correction_documents):
            corrections = correction_documents[key]
            reviewed = reviewed_documents[key]
            if not isinstance(corrections, DocumentCorrections):
                raise ReviewValidationError(
                    f"document {key}: invalid corrections type"
                )
            correction_key = _canonical_document_id(corrections.p_doc_id)
            if corrections.p_doc_id != key or correction_key != key:
                raise ReviewValidationError(
                    f"correction document id {correction_key} does not match {key}"
                )
            _require_sha256(
                corrections.sha256,
                context=f"document {key} correction source",
            )
            if not isinstance(reviewed, ReviewedDocument):
                raise ReviewValidationError(
                    f"document {key}: invalid reviewed output type"
                )
            reviewed_key = _validate_reviewed_metadata(reviewed)
            if reviewed_key != key:
                raise ReviewValidationError(
                    f"reviewed document id {reviewed_key} does not match {key}"
                )
            if corrections.sha256 != reviewed.sha256:
                raise ReviewValidationError(
                    f"document {key}: source SHA-256 mismatch between corrections "
                    "and reviewed output"
                )
            frozen_corrections[key] = corrections
            frozen_reviewed[key] = reviewed
        object.__setattr__(
            self,
            "corrections",
            CorrectionRegistry(
                documents=MappingProxyType(frozen_corrections.copy())
            ),
        )
        object.__setattr__(
            self,
            "reviewed_documents",
            MappingProxyType(frozen_reviewed.copy()),
        )

    def manages(self, p_doc_id: str | int) -> bool:
        return self.corrections.manages(p_doc_id)

    def guard_source(self, p_doc_id: str | int, sha256: str) -> None:
        self.corrections.guard_source(p_doc_id, sha256)

    def apply_and_validate(
        self,
        session: Session,
        document: ScheduleDocument,
    ) -> CorrectionResult:
        """Atomically apply and validate inside the caller-owned transaction.

        This method never commits or rolls back the caller's outer transaction.
        Its savepoint does roll back every correction when final validation
        fails, leaving the surrounding session active for the caller.
        """
        key = _canonical_document_id(document.p_doc_id)
        corrections = self.corrections.documents.get(key)
        if corrections is None:
            return CorrectionResult()
        expected = self.reviewed_documents.get(key)
        if expected is None:  # defensive fail-closed guard after construction
            raise ReviewValidationError(
                f"document {key} has no reviewed output"
            )
        self.guard_source(key, document.sha256)
        _require_clean_session(session, context="review bundle")
        with session.begin_nested():
            result = apply_document_corrections(session, document, corrections)
            validate_reviewed_document(session, document, expected)
        return result
