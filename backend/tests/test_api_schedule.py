from datetime import time

from src.models import Group, Lesson, Teacher, WeekType


def _seed_schedule(db_session):
    group = Group(course=2, number="2.1")
    other = Group(course=2, number="2.2")
    teacher = Teacher(full_name="Иванова Елена Петровна")
    db_session.add_all([group, other, teacher])
    db_session.flush()

    db_session.add_all(
        [
            Lesson(
                group_id=group.id,
                weekday=1,
                pair_number=2,
                starts_at=time(10, 50),
                ends_at=time(12, 25),
                subject="Эконометрика",
                week_type=WeekType.BOTH,
                subgroup=0,
            ),
            Lesson(
                group_id=group.id,
                weekday=1,
                pair_number=1,
                starts_at=time(9, 0),
                ends_at=time(10, 35),
                subject="Макроэкономика",
                teacher_id=teacher.id,
                room="220",
                week_type=WeekType.NUMERATOR,
                subgroup=0,
            ),
            Lesson(
                group_id=other.id,
                weekday=2,
                pair_number=1,
                starts_at=time(9, 0),
                ends_at=time(10, 35),
                subject="Философия",
                teacher_id=teacher.id,
                week_type=WeekType.BOTH,
                subgroup=0,
            ),
        ]
    )
    db_session.flush()
    return group, other, teacher


def test_schedule_by_group_sorted(client, db_session):
    group, _, _ = _seed_schedule(db_session)

    response = client.get(f"/api/schedule?group_id={group.id}")

    assert response.status_code == 200
    lessons = response.json()
    assert [item["subject"] for item in lessons] == ["Макроэкономика", "Эконометрика"]
    first = lessons[0]
    assert first["week_type"] == "numerator"
    assert first["starts_at"] == "09:00:00"
    assert first["teacher"] == {
        "id": first["teacher"]["id"],
        "full_name": "Иванова Елена Петровна",
    }
    assert lessons[1]["teacher"] is None


def test_schedule_by_teacher_spans_groups(client, db_session):
    _, _, teacher = _seed_schedule(db_session)

    response = client.get(f"/api/schedule?teacher_id={teacher.id}")

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_schedule_requires_exactly_one_param(client):
    assert client.get("/api/schedule").status_code == 422
    assert client.get("/api/schedule?group_id=1&teacher_id=1").status_code == 422


def test_schedule_unknown_group_404(client):
    response = client.get("/api/schedule?group_id=99999")
    assert response.status_code == 404


def test_schedule_unknown_teacher_404(client):
    response = client.get("/api/schedule?teacher_id=99999")
    assert response.status_code == 404


def test_schedule_etag_304(client, db_session):
    group, _, _ = _seed_schedule(db_session)

    first = client.get(f"/api/schedule?group_id={group.id}")
    second = client.get(
        f"/api/schedule?group_id={group.id}",
        headers={"If-None-Match": first.headers["etag"]},
    )
    assert second.status_code == 304
