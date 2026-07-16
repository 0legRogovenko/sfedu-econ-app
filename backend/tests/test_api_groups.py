from src.models import Group


def _add_groups(db_session):
    db_session.add_all(
        [
            Group(course=2, number="2.2"),
            Group(course=1, number="1.1"),
            Group(course=2, number="2.1"),
        ]
    )
    db_session.flush()


def test_groups_sorted_by_course_and_number(client, db_session):
    _add_groups(db_session)

    response = client.get("/api/groups")

    assert response.status_code == 200
    numbers = [g["number"] for g in response.json()]
    assert numbers == ["1.1", "2.1", "2.2"]
    assert response.json()[0] == {
        "id": response.json()[0]["id"],
        "course": 1,
        "number": "1.1",
        "subgroup_count": 1,
    }


def test_groups_empty_list(client):
    response = client.get("/api/groups")
    assert response.status_code == 200
    assert response.json() == []


def test_groups_etag_304(client, db_session):
    _add_groups(db_session)

    first = client.get("/api/groups")
    etag = first.headers["etag"]

    second = client.get("/api/groups", headers={"If-None-Match": etag})
    assert second.status_code == 304
    assert second.content == b""


def test_groups_etag_changes_with_data(client, db_session):
    _add_groups(db_session)
    first = client.get("/api/groups")

    db_session.add(Group(course=3, number="3.1"))
    db_session.flush()

    second = client.get(
        "/api/groups", headers={"If-None-Match": first.headers["etag"]}
    )
    assert second.status_code == 200
    assert second.headers["etag"] != first.headers["etag"]
