import base64
from io import BytesIO
import hashlib
import json
from pathlib import Path

from PIL import Image
import pytest

from src.persons.photo_bundle import parse_people, validate_image, render_catalog


def _row():
    key = ("вольчик", "в", "в")
    return {"id": base64.urlsafe_b64encode("\x1f".join(key).encode()).decode().rstrip("="),
            "short_name": "Вольчик В.В.", "full_name": "Вольчик Вячеслав Витальевич"}


def test_bundle_identity_uses_the_existing_directory_id():
    row = _row()
    person = parse_people([row])[0]
    assert person.id == row["id"]
    assert person.key == ("вольчик", "в", "в")


def test_mismatched_directory_identity_is_rejected():
    row = _row()
    row["short_name"] = "Иванов И.И."
    with pytest.raises(ValueError):
        parse_people([row])


def test_valid_image_is_checked_without_transforming_original_bytes():
    out = BytesIO()
    Image.new("RGB", (2, 3)).save(out, format="PNG")
    data = out.getvalue()
    assert validate_image(data) == "png"
    assert data == out.getvalue()


@pytest.mark.parametrize("data", [b"<html>error</html>", b"\x89PNG\r\n\x1a\ntruncated", b""])
def test_non_images_and_truncated_images_are_rejected(data):
    with pytest.raises(ValueError):
        validate_image(data)


def test_catalog_escapes_values_and_keeps_full_name_identity_guard():
    rendered = render_catalog({"abc": {"directory_name": "Вольчик Вячеслав Витальевич", "asset": "assets/people/hash.png"}})
    assert 'part of' in rendered
    assert 'Вольчик Вячеслав Витальевич' in rendered
    assert 'assets/people/hash.png' in rendered


def test_excessive_image_dimensions_are_rejected(monkeypatch):
    out = BytesIO()
    Image.new("RGB", (3, 3)).save(out, format="PNG")
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 1)
    with pytest.raises(ValueError):
        validate_image(out.getvalue())


def test_truncated_jpeg_is_rejected_even_when_header_verification_succeeds():
    out = BytesIO()
    Image.new("RGB", (16, 16)).save(out, format="JPEG")
    with pytest.raises(ValueError):
        validate_image(out.getvalue()[:-2])


def test_shipped_catalog_contains_original_verified_images():
    app = Path(__file__).resolve().parents[2] / "app"
    manifest = json.loads((app / "assets/people/portraits.json").read_text())
    records = manifest["portraits"]
    aliases_path = Path(__file__).resolve().parents[1] / "data/person_photos/reviewed_aliases.json"
    assert hashlib.sha256(aliases_path.read_bytes()).hexdigest() == manifest["reviewed_aliases_sha256"]
    aliases = json.loads(aliases_path.read_text())
    assert 70 <= len(records) <= manifest["people"]
    hashes = set()
    for person_id, record in records.items():
        path = app / record["asset"]
        assert path.resolve().is_relative_to((app / "assets/people").resolve())
        data = path.read_bytes()
        assert hashlib.sha256(data).hexdigest() == record["sha256"]
        assert len(data) == record["bytes"]
        assert validate_image(data)
        if person_id in aliases:
            assert aliases[person_id]["full_name"] == record["full_name"]
            assert aliases[person_id]["source_url"] == record["source_url"]
        assert record["sha256"] not in hashes, f"Shared photograph requires review: {person_id}"
        hashes.add(record["sha256"])
    assert (app / "lib/features/people/portrait_catalog.g.dart").read_text() == render_catalog(records)
