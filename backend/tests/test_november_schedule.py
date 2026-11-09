"""Source checks for the officially published second autumn module."""

from datetime import date, time
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from src.database import Base
from src.models import Group, Lesson
from src.schedule import importer
from src.schedule.fetch import FetchedDocument
from src.schedule.source import ScheduleLink, download_url
from src.schedule.validated_snapshot import import_validated_snapshot

SNAPSHOT = Path(__file__).resolve().parents[1] / "data/schedule_snapshot/2026-11-09"


def test_numeric_module_heading_preserves_explicit_year():
    weeks = [SimpleNamespace(date_from=date(2026, 9, 1), date_to=date(2027, 1, 17))]
    assert importer._module_bounds("2 модуль (2.11.26 - 11.01.27)", weeks) == (
        "2 модуль", date(2026, 11, 2), date(2027, 1, 11)
    )


@pytest.fixture(scope="module")
def third_course():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    content = (SNAPSHOT / "14177.pdf").read_bytes()

    class Fetcher:
        def fetch_document(self, doc_id):
            return FetchedDocument(str(doc_id), content, importer.sha256(content), download_url(doc_id))

    with Session(engine) as session:
        report = importer.import_all(
            session, Fetcher(), [ScheduleLink("Осенний семестр", "3 курс", "14177")], atomic=True
        )
        assert report.failed == 0
        yield session, report


def test_third_course_second_module_has_group_specific_end_dates(third_course):
    session, _ = third_course
    for number, last_day in [("3.2", date(2026, 12, 28)), ("3.1", date(2027, 1, 10))]:
        lessons = session.scalars(
            select(Lesson).join(Group).where(Group.number == number, Lesson.valid_from == date(2026, 11, 2))
        ).all()
        assert lessons, f"{number}: missing second module"
        assert {lesson.valid_to for lesson in lessons} == {last_day}
        assert all(lesson.module.date_to == last_day for lesson in lessons)


def test_third_course_second_module_continuation_and_muam_are_present(third_course):
    session, report = third_course
    lessons = session.scalars(
        select(Lesson).join(Group).where(Group.number == "3.1", Lesson.valid_from == date(2026, 11, 2))
    ).all()
    assert any(lesson.weekday == 4 and "Python" in lesson.subject for lesson in lessons)
    assert len([lesson for lesson in lessons if lesson.weekday == 5 and lesson.subject.startswith("МУАМ")]) == 4
    assert report.documents[0].ledger.accounted == report.documents[0].ledger.total


def test_second_course_continued_thursday_keeps_its_day():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    content = (SNAPSHOT / "14176.pdf").read_bytes()

    class Fetcher:
        def fetch_document(self, doc_id):
            return FetchedDocument(str(doc_id), content, importer.sha256(content), download_url(doc_id))

    with Session(engine) as session:
        importer.import_all(session, Fetcher(), [ScheduleLink("Осенний семестр", "2 курс", "14176")], atomic=True)
        lesson = session.scalar(
            select(Lesson).join(Group).where(
                Group.number == "2.2", Lesson.weekday == 3,
                Lesson.pair_number == 4, Lesson.valid_from == date(2026, 11, 2),
                Lesson.subject == "Микроэкономика 2",
            )
        )
        assert lesson is not None


@pytest.fixture(scope="module")
def reviewed_november():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        result = import_validated_snapshot(session, SNAPSHOT)
        assert result["counts"]["groups"] == 39
        yield session


def test_every_published_group_has_second_module_lessons(reviewed_november):
    session = reviewed_november
    for group in session.scalars(select(Group)):
        lessons = session.scalars(select(Lesson).where(Lesson.group_id == group.id)).all()
        assert any(
            lesson.valid_from and lesson.valid_to
            and lesson.valid_from <= date(2026, 11, 9) <= lesson.valid_to
            for lesson in lessons
        ), group.number or group.program
        assert all(lesson.valid_from and lesson.valid_to for lesson in lessons)


def test_third_course_monday_language_has_all_three_blocks(reviewed_november):
    lessons = reviewed_november.scalars(
        select(Lesson).join(Group).where(
            Group.number == "3.1", Lesson.weekday == 0,
            Lesson.valid_from == date(2026, 11, 2),
        )
    ).all()
    english = [lesson for lesson in lessons if lesson.subject == "Иностранный язык для деловой коммуникации"]
    assert {(lesson.starts_at, lesson.ends_at) for lesson in english} == {
        (time(10, 40), time(12, 40)),
        (time(12, 45), time(14, 30)),
        (time(14, 35), time(16, 35)),
    }


def test_master_project_work_starts_on_its_published_december_date(reviewed_november):
    lessons = reviewed_november.scalars(
        select(Lesson).join(Group).where(
            Group.course == 1, Group.program == "Экономика, управление и право",
            Lesson.weekday == 3, Lesson.subject == "Модуль проектной деятельности",
            Lesson.valid_from >= date(2026, 11, 1),
        )
    ).all()
    assert {(lesson.starts_at, lesson.valid_from) for lesson in lessons} >= {
        (time(17, 35), date(2026, 12, 10)),
        (time(19, 15), date(2026, 12, 3)),
    }


def test_master_extra_late_block_keeps_exact_dates_and_time(reviewed_november):
    lessons = reviewed_november.scalars(
        select(Lesson).join(Group).where(
            Group.course == 2, Group.program == "Экономика, управление и право",
            Lesson.weekday == 0, Lesson.starts_at == time(20, 55),
        )
    ).all()
    assert len(lessons) == 3
    assert all(lesson.ends_at == time(21, 40) for lesson in lessons)
    assert [lesson.specific_dates for lesson in lessons].count(["2026-11-02", "2026-11-09"]) == 2


def test_fourth_course_seventh_group_is_preserved(reviewed_november):
    lessons = reviewed_november.scalars(
        select(Lesson).join(Group).where(
            Group.number == "4.7", Lesson.valid_from == date(2026, 11, 2),
        )
    ).all()
    assert lessons
    philosophy = next(lesson for lesson in lessons if lesson.subject == "Философия")
    assert philosophy.room == "302"
    assert all(lesson.valid_to == date(2027, 1, 11) for lesson in lessons)
