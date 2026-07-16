from datetime import datetime, time

import pytest
from sqlalchemy.exc import IntegrityError

from src.models import Group, Lesson, News, NewsSource, WeekType


def make_lesson(group_id: int, **overrides):
    data = dict(
        group_id=group_id,
        weekday=1,
        pair_number=1,
        starts_at=time(9, 0),
        ends_at=time(10, 35),
        subject="Макроэкономика",
        week_type=WeekType.BOTH,
        subgroup=0,
    )
    data.update(overrides)
    return Lesson(**data)


def make_news(**overrides):
    data = dict(
        title="Тест",
        body="Текст",
        source=NewsSource.SFEDU,
        url="https://sfedu.ru/news/1",
        published_at=datetime(2026, 7, 13, 12, 0),
    )
    data.update(overrides)
    return News(**data)


def _make_group(db_session) -> int:
    group = Group(course=2, number="2.1")
    db_session.add(group)
    db_session.flush()
    return group.id


def test_duplicate_lesson_slot_rejected(db_session):
    gid = _make_group(db_session)
    db_session.add(make_lesson(gid))
    db_session.flush()

    db_session.add(make_lesson(gid, subject="Эконометрика"))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_same_slot_different_week_type_allowed(db_session):
    gid = _make_group(db_session)
    db_session.add(make_lesson(gid, week_type=WeekType.NUMERATOR))
    db_session.add(make_lesson(gid, week_type=WeekType.DENOMINATOR))
    db_session.flush()  # не должно упасть


def test_same_slot_different_subgroup_allowed(db_session):
    gid = _make_group(db_session)
    db_session.add(make_lesson(gid, subgroup=1))
    db_session.add(make_lesson(gid, subgroup=2))
    db_session.flush()  # не должно упасть


def test_duplicate_news_url_rejected(db_session):
    db_session.add(make_news())
    db_session.flush()

    db_session.add(make_news(title="Другой заголовок"))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_duplicate_group_rejected(db_session):
    db_session.add(Group(course=2, number="2.1"))
    db_session.flush()

    db_session.add(Group(course=2, number="2.1"))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_duplicate_kb_slug_rejected(db_session):
    from src.models import KbArticle

    db_session.add(KbArticle(slug="spravka", title="Справка", body_md="…"))
    db_session.flush()

    db_session.add(KbArticle(slug="spravka", title="Другая", body_md="…"))
    with pytest.raises(IntegrityError):
        db_session.flush()
