from datetime import time

from sqlalchemy import select

from src.models import Contact, DirectoryOverride, Lesson, PersonPhoto
from src.persons.directory import build_directory, encode_id
from src.persons.photo_import import store_photos
from src.persons.photos import PhotoCandidate

KEY = ("вольчик", "в", "в")
NAME = "Вольчик Вячеслав Витальевич"
PHOTO = "https://econ.sfedu.ru/upload/iblock/photo.jpg"
SOURCE = "https://econ.sfedu.ru/kafedra-ekonomicheskoy-teorii/"


def _contact(db_session):
    db_session.add(Contact(section="Кафедра", name=NAME, email="volchik@sfedu.ru"))
    db_session.flush()


def _photo(**overrides):
    fields = dict(person_id=encode_id(KEY), full_name=NAME, photo_url=PHOTO, source_url=SOURCE)
    fields.update(overrides)
    return PersonPhoto(**fields)


def test_photo_is_optional_for_existing_people(client, db_session):
    _contact(db_session)
    person = client.get("/api/persons").json()[0]
    assert person["photo_url"] is None
    assert person["email"] == "volchik@sfedu.ru"


def test_photo_decorates_the_same_profile_and_preserves_email_and_lessons(client, db_session):
    _contact(db_session)
    db_session.add_all([
        _photo(),
        DirectoryOverride(match_name="Вольчик В.В.", email="pinned@sfedu.ru", hidden=False),
        Lesson(group_id=1, weekday=0, pair_number=1, starts_at=time(8), ends_at=time(9, 35),
               subject="Экономика", cell_raw="Экономика (л) Вольчик В.В. ауд.118", subgroup=0),
    ])
    db_session.flush()
    person = client.get("/api/persons").json()[0]
    assert person["id"] == encode_id(KEY)
    assert person["photo_url"] == PHOTO
    assert person["email"] == "pinned@sfedu.ru"
    assert person["lesson_count"] == 1
    assert len(client.get(f"/api/persons/{person['id']}/schedule").json()["lessons"]) == 1


def test_stored_photo_cannot_resurrect_hidden_or_unknown_people(client, db_session):
    _contact(db_session)
    db_session.add_all([
        _photo(),
        _photo(person_id=encode_id(("неизвестный", "а", "б")), full_name="Неизвестный Алексей Борисович"),
        DirectoryOverride(match_name="Вольчик В.В.", hidden=True),
    ])
    db_session.flush()
    assert client.get("/api/persons").json() == []


def test_stale_name_or_foreign_url_is_never_exposed(client, db_session):
    _contact(db_session)
    photo = _photo(full_name="Вольчик Виктор Владимирович")
    db_session.add(photo)
    db_session.flush()
    assert client.get("/api/persons").json()[0]["photo_url"] is None
    photo.full_name = NAME
    photo.photo_url = "https://example.com/someone.jpg"
    db_session.flush()
    assert client.get("/api/persons").json()[0]["photo_url"] is None


def test_photo_upsert_is_idempotent_and_creates_no_contacts(db_session):
    _contact(db_session)
    candidate = PhotoCandidate(NAME, PHOTO, SOURCE)
    first = store_photos(db_session, [candidate])
    second = store_photos(db_session, [candidate])
    assert first.matches == second.matches == {encode_id(KEY): candidate}
    assert len(db_session.scalars(select(PersonPhoto)).all()) == 1
    assert len(db_session.scalars(select(Contact)).all()) == 1
    assert build_directory(db_session)[0].email == "volchik@sfedu.ru"


def test_photo_import_rejects_ambiguous_names_without_replacing_existing_photo(db_session):
    _contact(db_session)
    db_session.add(_photo())
    db_session.flush()
    candidates = [PhotoCandidate(name, PHOTO + "?new=1", SOURCE) for name in [NAME, "Вольчик Виктор Владимирович"]]
    report = store_photos(db_session, candidates)
    assert report.ambiguous == [encode_id(KEY)]
    assert db_session.scalar(select(PersonPhoto)).photo_url == PHOTO
