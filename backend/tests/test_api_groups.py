from datetime import time

from src.models import DocType, EducationLevel, Group, Lesson, ScheduleDocument


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
        "program": None,
        "level": "bachelor",
        "subgroup_count": 1,
    }


def test_groups_sorted_by_level_course_then_number_or_program(client, db_session):
    """Детерминированный порядок: уровень → курс → номер/программа.

    Бакалавры (level 'bachelor') идут раньше магистров ('master'); внутри курса
    бакалавров разводит номер группы, магистров — каноническая программа. Список
    не перемешан и стабилен между запросами независимо от порядка вставки.
    """
    db_session.add_all(
        [
            Group(
                course=2,
                number=None,
                program="Экономическая аналитика",
                level=EducationLevel.MASTER,
            ),
            Group(course=1, number="1.2"),
            Group(
                course=1,
                number=None,
                program="Корпоративные финансы",
                level=EducationLevel.MASTER,
            ),
            Group(course=1, number="1.1"),
            Group(
                course=1,
                number=None,
                program="Учетные технологии и аудит",
                level=EducationLevel.MASTER,
            ),
        ]
    )
    db_session.flush()

    payload = client.get("/api/groups").json()
    order = [(g["level"], g["course"], g["number"], g["program"]) for g in payload]
    assert order == [
        ("bachelor", 1, "1.1", None),
        ("bachelor", 1, "1.2", None),
        ("master", 1, None, "Корпоративные финансы"),
        ("master", 1, None, "Учетные технологии и аудит"),
        ("master", 2, None, "Экономическая аналитика"),
    ]


def test_master_group_serializes_with_program_and_level(client, db_session):
    """У магистров номера группы НЕТ — их идентифицирует программа.

    Без program и level в контракте клиент получает 52 группы с number:null и
    ничем не может их различить и показать: онбординг перестаёт открываться
    у ВСЕХ, включая бакалавров.
    """
    db_session.add(
        Group(
            course=1,
            number=None,
            program="Экономика фирмы и отраслевых рынков",
            level=EducationLevel.MASTER,
        )
    )
    db_session.flush()

    response = client.get("/api/groups")

    assert response.status_code == 200
    master = response.json()[0]
    assert master["number"] is None
    assert master["program"] == "Экономика фирмы и отраслевых рынков"
    assert master["level"] == "master"


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

    second = client.get("/api/groups", headers={"If-None-Match": first.headers["etag"]})
    assert second.status_code == 200
    assert second.headers["etag"] != first.headers["etag"]


def test_imported_catalog_hides_group_without_any_schedule(client, db_session):
    """Старая группа не остаётся в выборе после замены комплекта файлов."""
    active = Group(course=3, number="3.1")
    orphan = Group(course=3, number="3.7")
    document = ScheduleDocument(
        p_doc_id=14177,
        section="Осенний семестр",
        label="3 курс",
        doc_type=DocType.SEMESTER_GRID_BACHELOR,
        sha256="a" * 64,
        source_url="https://sfedu.ru/current",
    )
    db_session.add_all([active, orphan, document])
    db_session.flush()
    db_session.add(
        Lesson(
            group_id=active.id,
            document_id=document.id,
            weekday=0,
            pair_number=1,
            starts_at=time(8),
            ends_at=time(9, 35),
            subject="Экономика",
            subgroup=0,
        )
    )
    db_session.flush()

    numbers = [item["number"] for item in client.get("/api/groups").json()]

    assert numbers == ["3.1"]
