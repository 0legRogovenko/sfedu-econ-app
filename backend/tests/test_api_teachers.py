from src.models import Teacher


def _add_teachers(db_session):
    db_session.add_all(
        [
            Teacher(full_name="Ласкова Т.С."),
            Teacher(full_name="Бутова С.В. / Писанка С.А."),
            Teacher(full_name="Аверин А.В."),
        ]
    )
    db_session.flush()


def test_teachers_sorted_by_full_name(client, db_session):
    _add_teachers(db_session)

    response = client.get("/api/teachers")

    assert response.status_code == 200
    names = [t["full_name"] for t in response.json()]
    # Просто по строке, локале-независимо; сдвоенное ФИО — одна запись как есть
    assert names == ["Аверин А.В.", "Бутова С.В. / Писанка С.А.", "Ласкова Т.С."]


def test_teachers_field_contract(client, db_session):
    """Плоский массив ровно из {id, full_name} — без department/email и прочего.

    Клиент фильтрует локально по full_name; лишние поля из модели (кабинет,
    почта) в списке не нужны и не должны утекать.
    """
    db_session.add(
        Teacher(
            full_name="Ласкова Т.С.",
            department="Кафедра экономики",
            email="laskova@sfedu.ru",
        )
    )
    db_session.flush()

    response = client.get("/api/teachers")

    assert response.status_code == 200
    teacher = response.json()[0]
    assert teacher == {"id": teacher["id"], "full_name": "Ласкова Т.С."}


def test_teachers_empty_list(client):
    response = client.get("/api/teachers")
    assert response.status_code == 200
    assert response.json() == []


def test_teachers_etag_304(client, db_session):
    _add_teachers(db_session)

    first = client.get("/api/teachers")
    etag = first.headers["etag"]

    second = client.get("/api/teachers", headers={"If-None-Match": etag})
    assert second.status_code == 304
    assert second.content == b""


def test_teachers_etag_changes_with_data(client, db_session):
    _add_teachers(db_session)
    first = client.get("/api/teachers")

    db_session.add(Teacher(full_name="Новиков Н.Н."))
    db_session.flush()

    second = client.get(
        "/api/teachers", headers={"If-None-Match": first.headers["etag"]}
    )
    assert second.status_code == 200
    assert second.headers["etag"] != first.headers["etag"]
