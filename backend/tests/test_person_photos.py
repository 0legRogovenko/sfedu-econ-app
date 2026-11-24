from pathlib import Path
import os
import subprocess
import sys

import pytest

from src.persons.directory import PersonRow, encode_id
from src.persons.names import key_of_full
from src.persons.photos import PhotoCandidate, match_photos, parse_photo_page

SOURCE = "https://econ.sfedu.ru/kafedra-ekonomicheskoy-teorii/"
PHOTO = "https://econ.sfedu.ru/upload/iblock/1c5/volchik.png"


def _person(name="Вольчик Вячеслав Витальевич"):
    key = key_of_full(name)
    return PersonRow(key=key, short_name="Вольчик В.В.", full_name=name)


def test_actual_faculty_lazyload_cards_are_bound_to_their_own_names():
    page = (Path(__file__).parent / "fixtures/person_photos/faculty.html").read_text()
    candidates = parse_photo_page(page, SOURCE)
    assert [(c.full_name, c.photo_url.rsplit("/", 1)[-1]) for c in candidates] == [
        ("Вольчик Вячеслав Витальевич", "dn3s9aqdyyjadl11gsf5con82n8mtfup.png"),
        ("Белокрылова Ольга Спиридоновна", "x2lzfk69r8xdrv2cugehr2tughcbucln.jpeg"),
        ("Корытцев Максим Александрович", "r4r0632ehlrm9z881oju6773yv922q8q.jpeg"),
    ]
    assert all(c.source_url == SOURCE for c in candidates)
    assert all(c.photo_url.startswith("https://econ.sfedu.ru/upload/") for c in candidates)


def test_university_profile_uses_named_portrait_not_navigation_logo():
    page = '''<img src="/logo.png"><h1>Вольчик Вячеслав Витальевич</h1>
    <div class="img"><img src="/files/users/volchik.jpg"
    alt="Вольчик Вячеслав Витальевич"></div>'''
    candidates = parse_photo_page(page, "https://sfedu.ru/s7/person/volchik")
    assert len(candidates) == 1
    assert candidates[0].photo_url == "https://sfedu.ru/files/users/volchik.jpg"


@pytest.mark.parametrize("url", [
    "https://example.com/volchik.jpg", "//sfedu.ru.evil.test/volchik.jpg",
    "http://econ.sfedu.ru/volchik.jpg", "https://user:pass@sfedu.ru/volchik.jpg",
    "data:image/png;base64,abc", "/images/no-photo.png", "/images/logo.png",
    "https://[broken/image.jpg",
])
def test_unofficial_or_placeholder_images_are_rejected(url):
    page = f'''<div class="elem-hover-height"><div class="empl-face" data-src="{url}"></div>
    <div class="empl-name">Вольчик Вячеслав Витальевич</div></div>'''
    assert parse_photo_page(page, SOURCE) == []


def test_a_unique_exact_name_matches_without_rewriting_person_data():
    person = _person()
    candidate = PhotoCandidate(person.full_name, PHOTO, SOURCE)
    report = match_photos([person], [candidate, candidate])
    assert report.matches == {person.id: candidate}
    assert not report.missing
    assert not report.ambiguous
    assert person.email is None


def test_same_initials_but_different_full_name_cannot_receive_the_photo():
    person = _person()
    wrong = PhotoCandidate("Вольчик Виктор Владимирович", PHOTO, SOURCE)
    report = match_photos([person], [wrong])
    assert not report.matches
    assert person.id in report.missing


def test_two_official_people_with_the_same_key_remain_ambiguous():
    person = _person()
    candidates = [PhotoCandidate(name, PHOTO, SOURCE) for name in [
        person.full_name, "Вольчик Виктор Владимирович",
    ]]
    report = match_photos([person], candidates)
    assert not report.matches
    assert person.id in report.ambiguous


def test_external_teacher_can_match_only_one_official_full_name():
    key = ("груданова", "и", "ю")
    person = PersonRow(key=key, short_name="Груданова И.Ю.", full_name="Груданова И.Ю.")
    candidate = PhotoCandidate("Груданова Ирина Юрьевна", "https://sfedu.ru/files/grudanova.jpg", "https://sfedu.ru/s7/person/grudanova")
    assert match_photos([person], [candidate]).matches == {encode_id(key): candidate}


def test_different_department_photos_of_the_same_person_are_not_ambiguous():
    person = _person()
    first = PhotoCandidate(person.full_name, PHOTO, SOURCE)
    other = PhotoCandidate(person.full_name.upper(), PHOTO.replace("volchik", "another"), "https://econ.sfedu.ru/o-fakultete/")
    assert match_photos([person], [first, other]).matches == {person.id: first}


def test_public_source_parser_does_not_require_database_credentials():
    env = {k: v for k, v in os.environ.items() if k not in {"ADMIN_PASSWORD", "SECRET_KEY", "DATABASE_URL"}}
    result = subprocess.run(
        [sys.executable, "-c", "from src.persons.photos import parse_photo_page; assert parse_photo_page('', 'https://sfedu.ru/') == []"],
        capture_output=True, text=True, env=env, cwd=Path(__file__).resolve().parents[1],
    )
    assert result.returncode == 0, result.stderr


def test_canonicalizable_official_photo_url_is_returned_in_absolute_form():
    person = _person()
    candidate = PhotoCandidate(person.full_name, "/upload/photo.jpg", SOURCE)
    matched = match_photos([person], [candidate]).matches[person.id]
    assert matched.photo_url == "https://econ.sfedu.ru/upload/photo.jpg"
