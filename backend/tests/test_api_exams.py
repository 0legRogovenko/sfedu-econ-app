from datetime import datetime

from src.models import ExamEvent, Group


def _seed_exams(db_session):
    group = Group(course=4, number="4.1")
    other = Group(course=4, number="4.2")
    db_session.add_all([group, other])
    db_session.flush()

    db_session.add_all(
        [
            ExamEvent(
                group_id=group.id,
                subject="Эконометрика",
                teacher="Шаль А.В.",
                consultation_at=datetime(2026, 4, 14, 11, 0),
                exam_at=datetime(2026, 4, 15, 9, 0),
                room="118",
                kind="письменный",
            ),
            ExamEvent(
                group_id=group.id,
                subject="Экосистема современной организации",
                teacher="Чернова О.А.",
                consultation_at=datetime(2026, 4, 8, 11, 0),
                exam_at=datetime(2026, 4, 9, 9, 0),
                room="214",
                kind="устный",
            ),
            # Дыра источника: дата экзамена не разобралась — None, не выдумываем
            ExamEvent(
                group_id=group.id,
                subject="Философия",
                teacher=None,
                consultation_at=None,
                exam_at=None,
                room=None,
                kind=None,
            ),
            ExamEvent(
                group_id=other.id,
                subject="Чужой экзамен",
                exam_at=datetime(2026, 4, 1, 9, 0),
            ),
        ]
    )
    db_session.flush()
    return group, other


def test_exams_sorted_by_exam_at_nulls_last(client, db_session):
    group, _ = _seed_exams(db_session)

    response = client.get(f"/api/exams?group_id={group.id}")

    assert response.status_code == 200
    exams = response.json()
    assert [item["subject"] for item in exams] == [
        "Экосистема современной организации",
        "Эконометрика",
        "Философия",  # exam_at=None — в конец, а не в начало (дефолт SQLite)
    ]


def test_exams_contract_fields(client, db_session):
    group, _ = _seed_exams(db_session)

    exams = client.get(f"/api/exams?group_id={group.id}").json()

    assert exams[0] == {
        "id": exams[0]["id"],
        "group_id": group.id,
        "subject": "Экосистема современной организации",
        "teacher": "Чернова О.А.",
        "consultation_at": "2026-04-08T11:00:00",
        "exam_at": "2026-04-09T09:00:00",
        "room": "214",
        "kind": "устный",
    }
    unparsed = exams[2]
    assert unparsed["teacher"] is None
    assert unparsed["consultation_at"] is None
    assert unparsed["exam_at"] is None
    assert unparsed["room"] is None
    assert unparsed["kind"] is None


def test_exams_only_requested_group(client, db_session):
    group, _ = _seed_exams(db_session)

    exams = client.get(f"/api/exams?group_id={group.id}").json()

    assert "Чужой экзамен" not in [item["subject"] for item in exams]


def test_exams_empty_list_for_group_without_exams(client, db_session):
    group = Group(course=1, number="1.1")
    db_session.add(group)
    db_session.flush()

    response = client.get(f"/api/exams?group_id={group.id}")

    assert response.status_code == 200
    assert response.json() == []


def test_exams_unknown_group_404(client):
    assert client.get("/api/exams?group_id=99999").status_code == 404


def test_exams_requires_group_id(client):
    assert client.get("/api/exams").status_code == 422


def test_exams_etag_304(client, db_session):
    group, _ = _seed_exams(db_session)

    first = client.get(f"/api/exams?group_id={group.id}")
    second = client.get(
        f"/api/exams?group_id={group.id}",
        headers={"If-None-Match": first.headers["etag"]},
    )
    assert second.status_code == 304
