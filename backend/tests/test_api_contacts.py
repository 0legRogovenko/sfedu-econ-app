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
