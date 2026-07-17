"""Разбор индексной страницы расписания ЮФУ.

Тесты идут по сохранённой копии настоящей страницы (fixtures/schedule/index.html,
cp1251) и сверяются с manifest.json — списком, добытым разведкой
(docs/superpowers/research/2026-07-17-schedule-recon.md).
"""

import json
import re
from pathlib import Path

from src.schedule.source import (
    INDEX_URL,
    ScheduleLink,
    download_url,
    parse_index,
)

FIXTURES = Path(__file__).parent / "fixtures" / "schedule"
INDEX_HTML = (FIXTURES / "index.html").read_text(encoding="cp1251")
MANIFEST = json.loads((FIXTURES / "manifest.json").read_text(encoding="utf-8"))


class TestParseIndex:
    def test_finds_all_29_links(self):
        assert len(parse_index(INDEX_HTML)) == 29

    def test_matches_manifest_exactly(self):
        """(label, p_doc_id) сходятся с разведкой — 29 файлов, без потерь и лишнего."""
        parsed = {(link.label, link.p_doc_id) for link in parse_index(INDEX_HTML)}
        expected = {(entry["label"], entry["id"]) for entry in MANIFEST}
        assert parsed == expected

    def test_all_four_sections_with_exact_names(self):
        """Разделов четыре, а не два.

        Наивный парсер склеивал сессии в «Весенний семестр»: заголовок раздела —
        голый текст в <div> без класса и без тега-заголовка.
        """
        sections = {link.section for link in parse_index(INDEX_HTML)}
        assert sections == {
            "Осенний семестр",
            "Весенний семестр",
            "Зимняя сессия",
            "Летняя сессия",
        }

    def test_section_sizes(self):
        """9 + 9 + 6 + 5 = 29 — арифметика разведки."""
        counts: dict[str, int] = {}
        for link in parse_index(INDEX_HTML):
            counts[link.section] = counts.get(link.section, 0) + 1
        assert counts == {
            "Осенний семестр": 9,
            "Весенний семестр": 9,
            "Зимняя сессия": 6,
            "Летняя сессия": 5,
        }

    def test_reads_hidden_dcont_span(self):
        """Список живёт в скрытом <span id="Dcont_">, JS перекладывает его в #Dcont.

        В сохранённой странице #Dcont пуст (' '), поэтому парсер, нацеленный на
        него, молча вернёт ноль ссылок. Проверяем, что читаем именно #Dcont_.
        """
        assert '<div id="Dcont"> </div>' in INDEX_HTML
        assert len(parse_index(INDEX_HTML)) == 29

    def test_link_found_regardless_of_href_prefix(self):
        """Ссылки ловятся regex'ом по p_doc_id, а не по префиксу пути.

        В семестрах путь абсолютный (/pls/rsu/sched_files...), в сессиях —
        относительный (sched_files...). Привязка к префиксу теряет разделы.
        """
        by_id = {link.p_doc_id: link for link in parse_index(INDEX_HTML)}
        assert by_id["13469"].section == "Осенний семестр"  # href абсолютный
        assert by_id["13745"].section == "Зимняя сессия"  # href относительный

    def test_labels_are_clean(self):
        """Метка — без &nbsp;-отступов и без слова «скачать» из тела ссылки."""
        by_id = {link.p_doc_id: link for link in parse_index(INDEX_HTML)}
        assert by_id["13469"].label == "1 курс"
        assert by_id["13497"].label == "маг.1 курс"
        assert by_id["13613"].label == "асп.1 курс"
        for link in parse_index(INDEX_HTML):
            assert "скачать" not in link.label
            assert "\xa0" not in link.label
            assert link.label == link.label.strip()

    def test_label_may_lie_about_content(self):
        """13984 подписан «4 курс», а внутри — летняя сессия.

        Фиксируем: source отдаёт подпись как есть, тип документа определяет
        classify по содержимому (решение №2 плана).
        """
        by_id = {link.p_doc_id: link for link in parse_index(INDEX_HTML)}
        assert by_id["13984"].label == "4 курс"
        assert by_id["13984"].section == "Летняя сессия"

    def test_no_duplicate_doc_ids(self):
        ids = [link.p_doc_id for link in parse_index(INDEX_HTML)]
        assert len(ids) == len(set(ids))

    def test_returns_schedule_links(self):
        assert all(isinstance(link, ScheduleLink) for link in parse_index(INDEX_HTML))


class TestDownloadUrl:
    def test_goes_through_www(self):
        assert (
            download_url("13469")
            == "https://sfedu.ru/www/sched_files.f_download?p_doc_id=13469"
        )

    def test_never_uses_disallowed_pls_rsu(self):
        """robots.txt запрещает /pls/rsu/ — а ссылки на странице ведут именно туда.

        Тот же файл отдаётся по /www/ и robots-разрешён. Это не деталь стиля:
        ходить по ссылке со страницы напрямую нельзя.
        """
        for entry in MANIFEST:
            url = download_url(entry["id"])
            assert "/pls/rsu/" not in url
            assert url.startswith("https://sfedu.ru/www/sched_files.f_download?")

    def test_url_property_on_link_is_www(self):
        for link in parse_index(INDEX_HTML):
            assert "/pls/rsu/" not in link.download_url
            assert re.fullmatch(
                r"https://sfedu\.ru/www/sched_files\.f_download\?p_doc_id=\d+",
                link.download_url,
            )


class TestIndexUrl:
    def test_points_at_economics_faculty_full_time(self):
        """Экономфак = p_es_id 10000000000000, очная форма = p_tf_id 1."""
        assert "p_es_id=>10000000000000" in INDEX_URL
        assert "p_tf_id=>1" in INDEX_URL
        assert "/pls/rsu/" not in INDEX_URL
