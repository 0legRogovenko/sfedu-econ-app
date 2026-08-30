import json
import re
from dataclasses import dataclass
from datetime import date, time
from pathlib import Path
from typing import Literal

from src.models import EducationLevel, Lesson, LessonKind, WeekType


_EMPTY_TEXT = r"\0"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_CORRECTION_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_MAX_CORRECTION_ID_LENGTH = 43  # len("manual:") + id must fit Lesson.cell_key(50)
_MAX_SOURCE_PAGE = 10_000
_MAX_SUBGROUP = 99
_MAX_COURSE = 9
_MAX_PAIR_NUMBER = 7


class ReviewValidationError(ValueError):
    """The reviewed schedule bundle is malformed or stale."""


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
    documents: dict[str, DocumentCorrections]

    def manages(self, p_doc_id: str | int) -> bool:
        return str(p_doc_id) in self.documents

    def guard_source(self, p_doc_id: str | int, sha256: str) -> None:
        document = self.documents.get(str(p_doc_id))
        if document is not None and document.sha256 != sha256:
            raise ReviewValidationError(
                f"document {p_doc_id} changed and requires review"
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
        raise ReviewValidationError(f"{context}: invalid ISO time")
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
    subject = _string(payload["subject"], context="subject", blank=False)
    return LessonState(
        p_doc_id=state_document,
        group=_parse_group(payload["group"]),
        weekday=_integer(
            payload["weekday"], context="weekday", minimum=0, maximum=5
        ),
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
        teacher=_optional_string(payload["teacher"], context="teacher"),
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
        module=_parse_module(payload["module"]),
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
    if not p_doc_id.isascii() or not p_doc_id.isdigit():
        raise ReviewValidationError(f"invalid document id {p_doc_id!r}")
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
    return CorrectionRegistry(documents=documents)
