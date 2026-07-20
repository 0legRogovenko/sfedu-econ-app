"""Связывание справочника с расписанием.

Юнит-тесты на синтетике + golden-инвариант на живом корпусе. Golden обязан
падать и при РОСТЕ числа связей: внезапный скачок означает, что сравнение
кто-то ослабил, а это прямой путь к чужому расписанию в карточке.
"""

from dataclasses import dataclass

import pytest

from src.persons.linker import build_registry, link_cell, link_exams, link_lessons
from src.persons.names import key_of_full


@dataclass
class FakeContact:
    name: str


@dataclass
class FakeLesson:
    id: int
    subject: str
    cell_raw: str


@dataclass
class FakeExam:
    id: int
    teacher: str


def _registry(*names):
    registry, unparsed = build_registry([FakeContact(n) for n in names])
    assert unparsed == []
    return registry


class TestRegistryFilter:
    """Мусор из ячейки не должен превращаться в человека."""

    @pytest.mark.parametrize(
        "cell",
        [
            "Дисциплины ВПК",           # → кандидат «Дисциплины В.П.»
            "Свиридов АСУ",             # → «Свиридов А.С.», РЕАЛЬНЫЙ чужой человек
            "Погосян АКТРУ",            # → «Погосян А.К.»
            "Микроэкономика Н.Н.",      # Н.Н. — маркер нижней недели, не инициалы
            "Беликова С.А. Г-217 АКТРУ",  # прицепом даёт «Акт Р.У.»
        ],
    )
    def test_garbage_yields_no_link(self, cell):
        registry = _registry("Вольчик Вячеслав Витальевич")
        lesson = FakeLesson(1, "Предмет", cell)
        assert link_lessons([lesson], registry)[1] == set()

    def test_only_registry_keys_survive(self):
        # В ячейке два имени, но в справочнике только одно.
        registry = _registry("Вольчик Вячеслав Витальевич")
        lesson = FakeLesson(1, "Предмет", "Вольчик В.В., Абросимов Д.В.")
        assert link_lessons([lesson], registry)[1] == {
            key_of_full("Вольчик Вячеслав Витальевич")
        }


class TestNamesakes:
    def test_same_surname_different_initials_never_merge(self):
        """Ласкова Т.С. и Ласкова Д.С. — два живых человека, расстояние 1 символ."""
        registry = _registry(
            "Ласкова Татьяна Сергеевна", "Ласкова Дарья Сергеевна"
        )
        lesson = FakeLesson(1, "Предмет", "Ласкова Т.С.")

        assert link_lessons([lesson], registry)[1] == {
            key_of_full("Ласкова Татьяна Сергеевна")
        }

    def test_surname_only_is_not_a_match(self):
        """«Погосян» без инициалов не связывается, даже если Погосян один."""
        registry = _registry("Погосян Нателла Володяевна")
        lesson = FakeLesson(1, "Предмет", "Погосян")
        assert link_lessons([lesson], registry)[1] == set()


class TestSegmentation:
    def test_multi_subject_cell_splits_by_subject(self):
        """Без сегментации преподаватель получает пары чужого предмета."""
        registry = _registry(
            "Некрасова Инна Владимировна", "Крюков Сергей Владимирович"
        )
        cell = (
            "Финансовые рынки (с) Некрасова И.В. ауд.206 "
            "Теория систем и системный анализ (с) Крюков С.В. ауд.405"
        )
        lessons = [
            FakeLesson(1, "Финансовые рынки", cell),
            FakeLesson(2, "Теория систем и системный анализ", cell),
        ]

        links = link_cell(cell, lessons, registry)

        assert links[1] == {key_of_full("Некрасова Инна Владимировна")}
        assert links[2] == {key_of_full("Крюков Сергей Владимирович")}

    def test_single_subject_cell_gives_everyone(self):
        """Один предмет — все преподаватели ячейки ведут его вместе."""
        registry = _registry(
            "Полховская Татьяна Юрьевна", "Шевченко Анна Андреевна"
        )
        cell = "МСФО (л)/(с) Полховская Т.Ю., Шевченко А.А. ауд.310"
        lessons = [FakeLesson(1, "МСФО", cell)]

        assert link_cell(cell, lessons, registry)[1] == {
            key_of_full("Полховская Татьяна Юрьевна"),
            key_of_full("Шевченко Анна Андреевна"),
        }

    def test_subject_not_found_in_cell_links_nobody(self):
        """Резать наугад нельзя: лучше не связать, чем связать не с тем."""
        registry = _registry("Некрасова Инна Владимировна")
        cell = "Некрасова И.В. ауд.206"
        lessons = [
            FakeLesson(1, "Предмет которого в тексте нет", cell),
            FakeLesson(2, "И этого тоже", cell),
        ]

        links = link_cell(cell, lessons, registry)
        assert links[1] == set() and links[2] == set()


class TestExams:
    def test_two_teachers_without_trailing_dot(self):
        registry = _registry(
            "Туманян Юрий Рафаелович", "Погосян Нателла Володяевна"
        )
        exam = FakeExam(1, "Туманян Ю.Р, Погосян Н.В.")

        assert link_exams([exam], registry)[1] == {
            key_of_full("Туманян Юрий Рафаелович"),
            key_of_full("Погосян Нателла Володяевна"),
        }


class TestGoldenLiveCorpus:
    """Инвариант на живой базе. Падает и при росте связей — см. докстринг."""

    @pytest.fixture()
    def live(self):
        # В обход conftest: он подменяет DATABASE_URL на sqlite:// ДО импорта
        # src.config, поэтому настоящий адрес читаем из .env сами (тот же
        # приём, что в test_person_names.py).
        from pathlib import Path

        from sqlalchemy import create_engine, select
        from sqlalchemy.exc import OperationalError
        from sqlalchemy.orm import Session

        url = "postgresql+psycopg2://sfedu:sfedu@localhost:5433/sfedu_econ"
        env_file = Path(__file__).resolve().parents[1] / ".env"
        if env_file.exists():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                key, sep, value = line.partition("=")
                if sep and key.strip() == "DATABASE_URL":
                    url = value.strip()

        engine = create_engine(url)
        try:
            with Session(engine) as session:
                session.execute(select(1))
                yield session
        except OperationalError as exc:
            pytest.skip(f"живая БД недоступна, инвариант не проверен: {exc.orig}")
        finally:
            engine.dispose()

    def test_golden_numbers(self, live):
        from sqlalchemy import select

        from src.models import Contact, ExamEvent, Lesson

        contacts = live.scalars(select(Contact)).all()
        registry, unparsed = build_registry(contacts)
        lessons = live.scalars(select(Lesson)).all()
        exams = live.scalars(select(ExamEvent)).all()

        lesson_links = link_lessons(lessons, registry)
        exam_links = link_exams(exams, registry)

        people = set()
        for keys in lesson_links.values():
            people |= keys
        for keys in exam_links.values():
            people |= keys

        assert unparsed == [], "ФИО контактов перестали разбираться"
        assert len(registry.by_key) == 77, "изменился состав справочника"
        assert sum(1 for k in lesson_links.values() if k) == 1450
        assert sum(1 for k in exam_links.values() if k) == 224
        assert len(people) == 60

    def test_namesakes_stay_apart_on_live_data(self, live):
        from sqlalchemy import select

        from src.models import Contact, Lesson

        contacts = live.scalars(select(Contact)).all()
        registry, _ = build_registry(contacts)
        links = link_lessons(live.scalars(select(Lesson)).all(), registry)

        def pairs(fio):
            key = key_of_full(fio)
            return sum(1 for keys in links.values() if key in keys)

        # Разные люди с разным числом пар: склейка сразу видна по числам.
        assert pairs("Ласкова Татьяна Сергеевна") == 48
        assert pairs("Ласкова Дарья Сергеевна") == 18

    def test_person_missing_from_teachers_table_is_still_linked(self, live):
        """Ради этого линкер и читает cell_raw, а не таблицу teachers."""
        from sqlalchemy import select

        from src.models import Contact, Lesson, Teacher

        assert (
            live.scalars(
                select(Teacher).where(Teacher.full_name.like("%Погорелова%"))
            ).all()
            == []
        ), "появилась строка teachers — тест потерял смысл, проверить линкер"

        contacts = live.scalars(select(Contact)).all()
        registry, _ = build_registry(contacts)
        links = link_lessons(live.scalars(select(Lesson)).all(), registry)

        key = key_of_full("Погорелова Татьяна Геннадьевна")
        assert sum(1 for keys in links.values() if key in keys) == 20
