from src.models import Contact


def test_contacts_sorted_by_section_and_order(client, db_session):
    db_session.add_all(
        [
            Contact(section="Кафедра экономики", name="Петров А. С.", sort_order=1),
            Contact(section="Деканат", name="Иванова Е. П.", sort_order=2),
            Contact(section="Деканат", name="Сидорова О. Н.", sort_order=1),
        ]
    )
    db_session.flush()

    response = client.get("/api/contacts")

    assert response.status_code == 200
    items = response.json()
    assert [(c["section"], c["name"]) for c in items] == [
        ("Деканат", "Сидорова О. Н."),
        ("Деканат", "Иванова Е. П."),
        ("Кафедра экономики", "Петров А. С."),
    ]


def test_contacts_etag_304(client, db_session):
    db_session.add(Contact(section="Деканат", name="Иванова Е. П."))
    db_session.flush()

    first = client.get("/api/contacts")
    second = client.get(
        "/api/contacts", headers={"If-None-Match": first.headers["etag"]}
    )
    assert second.status_code == 304


def test_deanery_first_then_alphabetical(client, db_session):
    """Деканат закреплён первым, остальные секции — по алфавиту.

    Иначе справочник открывался на «Бухгалтерском учете и аудите»: студенту
    в первую очередь нужен деканат, а не первая по алфавиту кафедра.
    """
    db_session.add_all(
        [
            Contact(section="Экономическая теория", name="Я", sort_order=1),
            Contact(section="Бухгалтерский учет и аудит", name="Б", sort_order=1),
            Contact(section="Деканат", name="Д", sort_order=1),
            Contact(section="Мировая экономика", name="М", sort_order=1),
        ]
    )
    db_session.flush()

    sections = [c["section"] for c in client.get("/api/contacts").json()]

    assert sections == [
        "Деканат",
        "Бухгалтерский учет и аудит",
        "Мировая экономика",
        "Экономическая теория",
    ]


def test_order_inside_section_keeps_sort_order(client, db_session):
    """Внутри кафедры первым идёт заведующий — это задаёт sort_order."""
    db_session.add_all(
        [
            Contact(section="Кафедра", name="Доцент", sort_order=2),
            Contact(section="Кафедра", name="Заведующий", sort_order=1),
        ]
    )
    db_session.flush()

    names = [c["name"] for c in client.get("/api/contacts").json()]

    assert names == ["Заведующий", "Доцент"]
