import base64
from dataclasses import asdict
from io import BytesIO
import json

from PIL import Image
import pytest
import requests

from scripts import bundle_person_photos as cli
from src.persons.photos import PhotoCandidate


def _person(surname, given, patronymic, *, initials_only=False):
    key = (surname.lower(), given[0].lower(), patronymic[0].lower())
    short = f"{surname} {given[0]}.{patronymic[0]}."
    return {"id": base64.urlsafe_b64encode("\x1f".join(key).encode()).decode().rstrip("="),
            "short_name": short, "full_name": short if initials_only else f"{surname} {given} {patronymic}"}


def _setup(tmp_path, monkeypatch, people, candidates, *, aliases=None, failing_url=None):
    app = tmp_path / "app"
    (app / "assets/people").mkdir(parents=True)
    (app / "lib/features/people").mkdir(parents=True)
    (app / "assets/people/portraits.json").write_text('{"previous": true}')
    (app / "lib/features/people/portrait_catalog.g.dart").write_text("previous catalog\n")
    (app / "assets/people/previous.jpg").write_bytes(b"previous photograph")
    people_file, snapshot = tmp_path / "people.json", tmp_path / "snapshot.json"
    people_file.write_text(json.dumps(people))
    snapshot.write_text(json.dumps({"photos": [asdict(c) for c in candidates]}))
    args = ["bundle_person_photos", "--people-json", str(people_file), "--snapshot", str(snapshot),
            "--app-dir", str(app), "--cache-dir", str(tmp_path / "cache")]
    if aliases:
        alias_file = tmp_path / "aliases.json"
        alias_file.write_text(json.dumps(aliases))
        args.extend(["--reviewed-aliases", str(alias_file)])
    monkeypatch.setattr("sys.argv", args)
    image = BytesIO()
    Image.new("RGB", (3, 4), "navy").save(image, format="JPEG")

    class Session:
        headers = {}

        def mount(self, *args): pass

        def close(self): pass

        def get(self, url, **kwargs):
            response = requests.Response()
            response.url = url
            response.status_code = 503 if url == failing_url else 200
            response._content = image.getvalue()
            response._content_consumed = True
            return response

    monkeypatch.setattr(cli.requests, "Session", Session)
    monkeypatch.setattr(cli.time, "sleep", lambda duration: None)
    previous = {p.relative_to(app): p.read_bytes() for p in app.rglob("*") if p.is_file()}
    return app, previous


def _assert_unchanged(app, previous):
    assert {p.relative_to(app): p.read_bytes() for p in app.rglob("*") if p.is_file()} == previous


def test_failed_download_preserves_previous_catalog_and_all_assets(tmp_path, monkeypatch):
    people = [_person("Вольчик", "Вячеслав", "Витальевич"), _person("Беликов", "Александр", "Николаевич")]
    candidates = [PhotoCandidate(p["full_name"], f"https://sfedu.ru/files/{i}.jpg", f"https://sfedu.ru/s7/person/{i}")
                  for i, p in enumerate(people)]
    app, previous = _setup(tmp_path, monkeypatch, people, candidates, failing_url=candidates[1].photo_url)
    with pytest.raises(RuntimeError, match="download"):
        cli.main()
    _assert_unchanged(app, previous)


def test_initials_alias_cannot_publish_an_unreviewed_personal_profile(tmp_path, monkeypatch):
    person = _person("Вольчик", "Вячеслав", "Витальевич", initials_only=True)
    candidate = PhotoCandidate("Вольчик Вячеслав Витальевич", "https://sfedu.ru/files/wrong.jpg",
                               "https://sfedu.ru/s7/person/wrong_profile")
    aliases = {person["id"]: {"full_name": candidate.full_name, "source_url": "https://sfedu.ru/s7/person/volchik"}}
    app, previous = _setup(tmp_path, monkeypatch, [person], [candidate], aliases=aliases)
    with pytest.raises(ValueError, match="No official photographs"):
        cli.main()
    _assert_unchanged(app, previous)
