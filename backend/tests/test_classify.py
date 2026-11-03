"""Классификатор типов документов расписания — на всех 29 реальных фикстурах ЮФУ.

Главная защита от «подпись врёт»: 13984 подписан «4 курс», а внутри — расписание
летней сессии. Поверим подписи — экзамены уедут в Lesson.
"""

import json
from collections import Counter
from pathlib import Path

import pytest

from src.schedule.classify import DocType, classify, classify_text, document_text

FIXTURES = Path(__file__).parent / "fixtures" / "schedule"
MANIFEST = json.loads((FIXTURES / "manifest.json").read_text(encoding="utf-8"))

# Ожидаемый тип для каждой фикстуры. Источник — разведка по содержимому файлов
# (docs/superpowers/research/2026-07-17-schedule-recon.md), а не подписи на сайте.
EXPECTED = {
    # недельная сетка, бакалавры (8)
    "13469": DocType.SEMESTER_GRID_BACHELOR,
    "13470": DocType.SEMESTER_GRID_BACHELOR,
    "13471": DocType.SEMESTER_GRID_BACHELOR,
    "13472": DocType.SEMESTER_GRID_BACHELOR,
    "13820": DocType.SEMESTER_GRID_BACHELOR,
    "13821": DocType.SEMESTER_GRID_BACHELOR,
    "13822": DocType.SEMESTER_GRID_BACHELOR,
    "13828": DocType.SEMESTER_GRID_BACHELOR,
    # недельная сетка, магистры (4)
    "13497": DocType.SEMESTER_GRID_MASTER,
    "13498": DocType.SEMESTER_GRID_MASTER,
    "13829": DocType.SEMESTER_GRID_MASTER,
    "13830": DocType.SEMESTER_GRID_MASTER,
    # сессия (11)
    "13744": DocType.EXAM_SESSION,
    "13745": DocType.EXAM_SESSION,
    "13746": DocType.EXAM_SESSION,
    "13747": DocType.EXAM_SESSION,
    "13767": DocType.EXAM_SESSION,
    "13768": DocType.EXAM_SESSION,
    "13984": DocType.EXAM_SESSION,
    "14049": DocType.EXAM_SESSION,
    "14057": DocType.EXAM_SESSION,
    "14058": DocType.EXAM_SESSION,
    "14092": DocType.EXAM_SESSION,
    # аспирантура (6)
    "13613": DocType.POSTGRAD,
    "13619": DocType.POSTGRAD,
    "13659": DocType.POSTGRAD,
    "13823": DocType.POSTGRAD,
    "13843": DocType.POSTGRAD,
    "13844": DocType.POSTGRAD,
}


def fixture_path(entry: dict) -> Path:
    return FIXTURES / f"{entry['id']}.{entry['kind']}"


@pytest.fixture(scope="module")
def actual() -> dict[str, DocType]:
    """Тип каждой из 29 фикстур. Извлечение текста дорогое — считаем один раз."""
    return {e["id"]: classify(fixture_path(e)) for e in MANIFEST}


class TestCorpus:
    def test_manifest_has_29_files(self):
        assert len(MANIFEST) == 29
        assert set(EXPECTED) == {e["id"] for e in MANIFEST}

    def test_every_file_classified_as_expected(self, actual):
        wrong = {
            i: (actual[i], EXPECTED[i]) for i in EXPECTED if actual[i] != EXPECTED[i]
        }
        assert not wrong, f"расхождения файл → (получено, ожидалось): {wrong}"

    def test_no_unknown(self, actual):
        # unknown = источник изменился и мы этого не заметили. Падаем, а не молчим.
        unknown = [i for i, t in actual.items() if t is DocType.UNKNOWN]
        assert not unknown, f"неопознанные документы: {unknown}"

    def test_counts_by_type(self, actual):
        assert Counter(actual.values()) == {
            DocType.EXAM_SESSION: 11,
            DocType.SEMESTER_GRID_BACHELOR: 8,
            DocType.POSTGRAD: 6,
            DocType.SEMESTER_GRID_MASTER: 4,
        }


class TestLabelLies:
    def test_13984_signed_4_kurs_is_exam_session(self, actual):
        # подписан «4 курс» в разделе «Летняя сессия», внутри — сессия, а не сетка
        assert actual["13984"] is DocType.EXAM_SESSION

    def test_same_label_different_types(self, actual):
        # «маг.1 курс» — и сетка (13497), и сессия (14092): подпись типа не задаёт
        labels = {e["id"]: e["label"] for e in MANIFEST}
        assert labels["13497"] == labels["14092"] == "маг.1 курс"
        assert actual["13497"] is not actual["14092"]


class TestSignals:
    def test_exam_header_split_across_runs(self):
        # в 13984.docx шапка склеена: «Датаэкзамена» — regex не должен требовать пробел
        assert "Датаэкзамена" in document_text(FIXTURES / "13984.docx")

    def test_curriculum_pages_do_not_hide_the_grid(self, actual):
        # у 13820 и 13830 первые страницы — «ПЕРЕЧЕНЬ ПРЕДМЕТОВ», сетка начинается дальше;
        # признак учебного плана не должен перебивать признак сетки
        assert "ПЕРЕЧЕНЬ ПРЕДМЕТОВ" in document_text(FIXTURES / "13820.pdf").upper()
        assert actual["13820"] is DocType.SEMESTER_GRID_BACHELOR
        assert actual["13830"] is DocType.SEMESTER_GRID_MASTER

    def test_master_session_is_session_not_grid(self, actual):
        # 14092 содержит «Магистерская программа», но это сессия: признак сессии сильнее
        assert "агистерск" in document_text(FIXTURES / "14092.pdf")
        assert actual["14092"] is DocType.EXAM_SESSION

    def test_curriculum_only_document(self):
        assert classify_text("ПЕРЕЧЕНЬ ПРЕДМЕТОВ И ПРАКТИК") is DocType.CURRICULUM

    def test_unknown_when_no_signals(self):
        assert classify_text("Объявление о переносе занятий") is DocType.UNKNOWN
