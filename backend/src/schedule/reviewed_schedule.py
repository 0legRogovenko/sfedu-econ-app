from dataclasses import dataclass
from datetime import date, time

from src.models import Lesson


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
            f"группа={group.level}/{group.course}/{group.number or ''}/"
            f"{group.program or ''}",
            f"день={state.weekday}",
            f"пара={state.pair_number}",
            f"начало={state.starts_at}",
            f"конец={state.ends_at}",
            f"предмет={state.subject}",
            f"вид={state.lesson_kind or ''}",
            f"препод={state.teacher or ''}",
            f"ауд={state.room or ''}",
            f"неделя={state.week_type or ''}",
            f"п/г={state.subgroup}",
            (
                f"модуль={module.date_from}..{module.date_to}"
                if module
                else "модуль="
            ),
            f"даты={state.date_constraint_raw or ''}",
            f"с={state.valid_from or ''}",
            f"по={state.valid_to or ''}",
            f"конкретные={specific_dates}",
        )
    )
