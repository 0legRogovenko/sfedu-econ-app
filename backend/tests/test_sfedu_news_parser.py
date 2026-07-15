from datetime import datetime
from pathlib import Path

import pytest

from src.parsers.sfedu_news import (
    parse_article,
    parse_listing,
    parse_ru_date,
)

FIXTURES = Path(__file__).parent / "fixtures"
LIST_HTML = (FIXTURES / "sfedu_list.html").read_text(encoding="utf-8")
ARTICLE_HTML = (FIXTURES / "sfedu_article.html").read_text(encoding="utf-8")


class TestParseRuDate:
    def test_all_months(self):
        cases = {
            "1 января 2026 г.": datetime(2026, 1, 1),
            "14 февраля 2026 г.": datetime(2026, 2, 14),
            "11 марта 2026 г.": datetime(2026, 3, 11),
            "2 апреля 2026 г.": datetime(2026, 4, 2),
            "14 мая 2026 г.": datetime(2026, 5, 14),
            "15 июня 2026 г.": datetime(2026, 6, 15),
            "3 июля 2026 г.": datetime(2026, 7, 3),
            "20 августа 2026 г.": datetime(2026, 8, 20),
            "5 сентября 2026 г.": datetime(2026, 9, 5),
            "9 октября 2026 г.": datetime(2026, 10, 9),
            "7 ноября 2026 г.": datetime(2026, 11, 7),
            "31 декабря 2026 г.": datetime(2026, 12, 31),
        }
        for text, expected in cases.items():
            assert parse_ru_date(text) == expected, text

    def test_tolerates_extra_whitespace(self):
        assert parse_ru_date("  15  июня  2026 г. ") == datetime(2026, 6, 15)

    def test_garbage_raises(self):
        with pytest.raises(ValueError):
            parse_ru_date("не дата")
        with pytest.raises(ValueError):
            parse_ru_date("15 брюмера 2026")


class TestParseListing:
    def test_returns_candidates(self):
        candidates = parse_listing(LIST_HTML)
        assert len(candidates) >= 3

    def test_first_candidate_fields(self):
        first = parse_listing(LIST_HTML)[0]
        assert first.url == "https://sfedu.ru/press-center/news/80662"
        assert "математическ" in first.title.lower()
        assert first.published_at == datetime(2026, 6, 15)
        assert first.snippet and first.snippet.strip()
        assert first.image_url is not None
        assert first.image_url.startswith("https://sfedu.ru/")

    def test_all_urls_absolute_and_unique(self):
        candidates = parse_listing(LIST_HTML)
        urls = [c.url for c in candidates]
        assert all(u.startswith("https://sfedu.ru/press-center/news/") for u in urls)
        assert len(urls) == len(set(urls))

    def test_candidate_without_snippet_or_image(self):
        # второй элемент листинга (div.new без img/prev_text) должен распарситься
        candidates = parse_listing(LIST_HTML)
        second = candidates[1]
        assert second.title
        assert second.url.startswith("https://sfedu.ru/")


class TestParseArticle:
    def test_extracts_clean_text(self):
        text = parse_article(ARTICLE_HTML)
        assert "Занятия школы проходят" in text
        assert "<p" not in text
        assert "font-family" not in text
        assert "&nbsp;" not in text

    def test_includes_short_description(self):
        text = parse_article(ARTICLE_HTML)
        assert "стартовали занятия" in text.lower()

    def test_paragraphs_separated(self):
        text = parse_article(ARTICLE_HTML)
        assert "\n\n" in text

    def test_empty_content_returns_empty_string(self):
        assert parse_article("<html><body><h3>Заголовок</h3></body></html>") == ""
