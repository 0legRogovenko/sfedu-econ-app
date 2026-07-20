"""Проверки набора статей базы знаний (src/kb_seed.py) — без БД."""

from src.kb_seed import _all_articles


def test_slugs_unique():
    slugs = [a["slug"] for a in _all_articles()]
    assert len(slugs) == len(set(slugs)), "дублирующиеся slug в наборе KB"


def test_field_limits_match_model():
    # KbArticle: slug String(100), title String(300)
    for a in _all_articles():
        assert 0 < len(a["slug"]) <= 100, a["slug"]
        assert 0 < len(a["title"]) <= 300, a["slug"]
        assert a["body"].strip(), a["slug"]


def test_bodies_have_no_markdown_bold():
    # База знаний — обычный текст: ассистент отвечает без Markdown, и ** в теле
    # статьи и как контекст лишнее, и легко утекает в ответ буквально.
    for a in _all_articles():
        assert "**" not in a["body"], a["slug"]


def test_covers_key_student_topics():
    slugs = {a["slug"] for a in _all_articles()}
    for expected in (
        "stipendii-i-matpomoshch",
        "peresdachi-i-dobor-ballov",
        "gia",
        "praktika",
        "raspisanie-v-prilozhenii",
        "kuda-obrashchatsya",
        "spravka-ob-obuchenii",
    ):
        assert expected in slugs, f"нет статьи {expected}"
