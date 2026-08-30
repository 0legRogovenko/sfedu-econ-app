"""Сквозной импорт: fetch → classify → extract → structure/cells/exams → load.

Тесты идут против 29 НАСТОЯЩИХ файлов ЮФУ из tests/fixtures/schedule. Сети нет:
фетчер подменяется на чтение фикстур — ровно так же, как это делает продовый
Fetcher, только без /www/ и без Crawl-delay.

Главный тест здесь — test_no_cell_is_lost_silently: сумма категорий по ячейкам
равна числу ячеек в документе. Он ловит худший режим отказа — молчаливую
потерю, когда студент приходит на пару, которой нет.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import replace
from datetime import date, datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.models import (
    Base,
    DocType,
    EducationLevel,
    ExamEvent,
    Group,
    ImportDiff,
    Lesson,
    LessonKind,
    Module,
    ScheduleDocument,
    UnparsedCell,
    WeekCalendar,
    WeekType,
)
from src.schedule import importer
from src.schedule.fetch import FetchedDocument
from src.schedule.reviewed_schedule import (
    CorrectionOperation,
    CorrectionRegistry,
    DocumentCorrections,
    ReviewBundle,
    ReviewedDocument,
    ReviewValidationError,
    lesson_state,
    reviewed_document_output,
    state_signature,
)
from src.schedule.source import ScheduleLink, download_url, parse_index
from src.schedule.structure import week_type_from_heading

FIXTURES = Path(__file__).parent / "fixtures" / "schedule"
INDEX_HTML = (FIXTURES / "index.html").read_text(encoding="cp1251")
MANIFEST = json.loads((FIXTURES / "manifest.json").read_text())
# rasp1.docx/rasp2.pdf — побайтовые дубли 13469/13470, в manifest их нет.
FILES = {item["id"]: FIXTURES / f"{item['id']}.{item['kind']}" for item in MANIFEST}

# Типы, которые импортёр НЕ извлекает (решение №8 плана). Список явный: «не
# считаем этот документ» обязано быть решением, записанным по типу, а не
# побочным эффектом нулевого ledger.total. Иначе любой документ, забывший
# позвать account(), сам себя исключает из проверки — ровно тот режим молчаливой
# потери, который эти тесты и ловят.
NOT_EXTRACTED_DOC_TYPES = frozenset({DocType.POSTGRAD_DATES})
POSTGRAD_FILES = 6  # 13613/13619/13659/… — аспирантура


class FakeFetcher:
    """Фетчер по фикстурам: та же поверхность, что у Fetcher, но без сети."""

    def __init__(
        self,
        index_html: str = INDEX_HTML,
        overrides: dict | None = None,
        claimed_hashes: dict | None = None,
    ):
        self.index_html = index_html
        self.overrides = overrides or {}
        self.claimed_hashes = claimed_hashes or {}
        self.requested: list[str] = []

    def fetch_index(self) -> str:
        return self.index_html

    def fetch_document(self, p_doc_id: str | int) -> FetchedDocument:
        p_doc_id = str(p_doc_id)
        self.requested.append(p_doc_id)
        content = self.overrides.get(p_doc_id)
        if content is None:
            content = FILES[p_doc_id].read_bytes()
        return FetchedDocument(
            p_doc_id=p_doc_id,
            content=content,
            sha256=self.claimed_hashes.get(p_doc_id, importer.sha256(content)),
            source_url=download_url(p_doc_id),
        )


class FailingSecondFetcher(FakeFetcher):
    """Первый файл отдаёт, второй имитирует обрыв официального сервера."""

    def fetch_document(self, p_doc_id: str | int) -> FetchedDocument:
        if str(p_doc_id) == "99999":
            raise ConnectionError("official source closed the response early")
        return super().fetch_document(p_doc_id)


def _real_cell_count(p_doc_id: str) -> int:
    """Сколько ячеек слой extract отдал по этому файлу — считаем сами, из фикстуры.

    Единственный честный знаменатель инварианта «ничего не потеряно»: он не
    зависит от того, добрался ли importer до mark() хоть раз.
    """
    grids, _ = importer._extract(FILES[p_doc_id].read_bytes())
    return sum(len(grid.cells) for grid in grids)


def _extracted_docs(corpus) -> list[tuple[str, "importer.DocumentReport"]]:
    """(p_doc_id, отчёт) по каждой фикстуре, которую импортёр обязан был прочесть.

    Идём от manifest.json, а не от report.documents: список файлов — внешний
    факт, отчёт — то, что мы проверяем. Документ, до отчёта не доехавший, здесь
    падает, а не выпадает из перебора. Пропускаем только аспирантуру и только по
    doc_type: нулевой ledger.total пропуском не является.
    """
    _, report = corpus
    by_id = {d.p_doc_id: d for d in report.documents}
    docs = []
    for item in MANIFEST:
        p_doc_id = item["id"]
        doc = by_id.get(p_doc_id)
        assert doc is not None, f"{p_doc_id}: фикстура не дошла до отчёта импорта"
        if doc.doc_type in NOT_EXTRACTED_DOC_TYPES:
            continue
        docs.append((p_doc_id, doc))
    return docs


def make_session(*, autoflush: bool = True):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=autoflush)()


@pytest.fixture(scope="module")
def corpus():
    """Один прогон всех 29 фикстур на всю группу тестов: он не быстрый."""
    session = make_session()
    report = importer.import_all(session, FakeFetcher())
    yield session, report
    session.close()


class TestCorpus:
    def test_index_gives_all_29_documents(self, corpus):
        _, report = corpus
        assert len(report.documents) == 29

    def test_no_unknown_document_type(self, corpus):
        _, report = corpus
        unknown = [d.p_doc_id for d in report.documents if d.doc_type == DocType.UNKNOWN]
        assert unknown == []

    def test_atomic_import_rolls_back_every_document_when_one_fails(self):
        session = make_session()
        links = [
            ScheduleLink("Осенний семестр", "4 курс", "14178"),
            ScheduleLink("Осенний семестр", "сломанный файл", "99999"),
        ]

        with pytest.raises(ConnectionError, match="closed the response early"):
            importer.import_all(
                session,
                FailingSecondFetcher(
                    overrides={"14178": (FIXTURES / "14178.pdf").read_bytes()}
                ),
                links=links,
                atomic=True,
            )
        session.rollback()

        assert session.scalar(select(func.count()).select_from(ScheduleDocument)) == 0
        assert session.scalar(select(func.count()).select_from(Lesson)) == 0
        session.close()

    def test_nothing_failed(self, corpus):
        _, report = corpus
        failed = [(d.p_doc_id, d.error) for d in report.documents if d.error]
        assert failed == []

    def test_postgrad_is_skipped(self, corpus):
        session, report = corpus
        postgrad = [d for d in report.documents if d.doc_type == DocType.POSTGRAD_DATES]
        assert len(postgrad) == 6
        assert all(d.status == importer.STATUS_SKIPPED for d in postgrad)
        # решение №8 плана: аспирантуру не импортируем — но и не выдумываем пары
        assert all(d.lessons == 0 and d.exams == 0 for d in postgrad)

    def test_bachelors_and_masters_both_got_lessons(self, corpus):
        session, _ = corpus
        for level in (EducationLevel.BACHELOR, EducationLevel.MASTER):
            count = session.scalar(
                select(func.count())
                .select_from(Lesson)
                .join(Group, Lesson.group_id == Group.id)
                .where(Group.level == level)
            )
            assert count > 0, f"нет пар у уровня {level}"

    def test_exam_sessions_produced_exam_events(self, corpus):
        session, _ = corpus
        assert session.scalar(select(func.count()).select_from(ExamEvent)) > 0

    def test_week_calendar_imported_for_semester_files(self, corpus):
        session, _ = corpus
        # 12 семестровых файлов × 18–20 диапазонов
        assert session.scalar(select(func.count()).select_from(WeekCalendar)) >= 200

    def test_masters_have_program_and_no_number(self, corpus):
        session, _ = corpus
        masters = session.scalars(
            select(Group).where(Group.level == EducationLevel.MASTER)
        ).all()
        assert masters
        assert all(g.number is None and g.program for g in masters)

    def test_master_programs_are_canonicalized(self, corpus):
        """Магистерские программы сведены к канону: 11 групп, не 23.

        Одна программа расщеплена между файлами — пары приходят с чистым именем
        из расписаний, экзамены с грязным (в обёртке «Магистерская программа
        «…»», с опечатками/переносами) из сессий. Без канонизации это 23 группы:
        у половины только пары, у половины только экзамены. canonical_program
        сводит оба написания в одну группу на (курс, программа): к1 — 6 программ,
        к2 — 5. Ни одно имя не остаётся в обёртке, и у каждой группы есть пары
        ИЛИ экзамены (обычно и то и другое).
        """
        session, _ = corpus
        masters = session.scalars(
            select(Group).where(Group.level == EducationLevel.MASTER)
        ).all()
        assert len(masters) == 11, (
            "магистерских групп должно быть 11 (к1:6, к2:5), а не "
            f"{len(masters)} — программы не канонизированы: "
            + ", ".join(sorted(f"к{g.course} {g.program}" for g in masters))
        )
        by_course = Counter(g.course for g in masters)
        assert by_course == Counter({1: 6, 2: 5}), by_course

        assert all("Магистерск" not in g.program for g in masters), (
            "остались имена в обёртке «Магистерская программа «…»»: "
            + ", ".join(g.program for g in masters if "Магистерск" in g.program)
        )

        # Программа, у которой не осталось ни пар, ни экзаменов, — призрак:
        # слияние должно было отдать ей и то, и другое из обоих источников.
        for group in masters:
            lessons = session.scalar(
                select(func.count()).select_from(Lesson).where(
                    Lesson.group_id == group.id
                )
            )
            exams = session.scalar(
                select(func.count()).select_from(ExamEvent).where(
                    ExamEvent.group_id == group.id
                )
            )
            assert lessons or exams, f"пустая магистерская группа: к{group.course} {group.program}"

    def test_no_master_exams_lost_to_canonicalization(self, corpus):
        """Канонизация сливает группы, но не теряет экзамены магистров.

        Слияние грязной группы (экзамены) с чистой (пары) не должно ни съесть,
        ни продублировать экзамены: их общее число у магистров остаётся тем же,
        что и в источнике (сумма по грязным именам из файлов сессий).
        """
        session, _ = corpus
        master_exams = session.scalar(
            select(func.count())
            .select_from(ExamEvent)
            .join(Group, ExamEvent.group_id == Group.id)
            .where(Group.level == EducationLevel.MASTER)
        )
        assert master_exams == 49, master_exams


    def test_muam_seminar_continuation_uses_previous_lecture_options(self):
        """13471: строка семинара продолжает МУАМ, но не повторяет заголовок.

        В официальном PDF у 3.1 в субботу две пары: лекция 08:00 и семинар
        09:50. Во второй ячейке написаны только два предмета с маркерами ``(с)``;
        без контекста предыдущей строки она уходила в UnparsedCell целиком.
        """
        session = make_session()
        fetcher = FakeFetcher()
        links = [
            link
            for link in parse_index(fetcher.fetch_index())
            if link.p_doc_id == "13471"
        ]
        importer.import_all(session, fetcher, links=links)

        group = session.scalar(select(Group).where(Group.number == "3.1"))
        document = session.scalar(
            select(ScheduleDocument).where(ScheduleDocument.p_doc_id == 13471)
        )
        muam = session.scalars(
            select(Lesson).where(
                Lesson.document_id == document.id,
                Lesson.group_id == group.id,
                Lesson.subject.like("МУАМ — %"),
            )
        ).all()

        subjects = {
            "МУАМ — Современные платформы для построения корпоративных инф. систем",
            "МУАМ — Цифровые системы интеграции и управления бизнесом",
        }
        assert {(lesson.subject, lesson.pair_number) for lesson in muam} == {
            (subject, pair) for subject in subjects for pair in (1, 2)
        }
        assert Counter(lesson.lesson_kind for lesson in muam) == Counter(
            {LessonKind.LECTURE: 4, LessonKind.SEMINAR: 4}
        )

        lost_seminars = session.scalars(
            select(UnparsedCell).where(
                UnparsedCell.document_id == document.id,
                UnparsedCell.raw_text.like("%Современные платформы%"),
            )
        ).all()
        assert lost_seminars == []
        session.close()

    def test_no_cell_is_lost_silently(self, corpus):
        """ГЛАВНЫЙ ТЕСТ ПЛАНА.

        Каждая ячейка каждого разобранного документа попадает ровно в одну
        категорию: пара / экзамен / очередь админа / пустая / заглушка /
        структура (шапки, дни, время, календарь). Сумма == числу ячеек.

        Перебор идёт по СПИСКУ ФИКСТУР, а не по report.documents: документ,
        выпавший из отчёта, обязан уронить тест, а не тихо исчезнуть из
        перебора. Знаменатель считается ЗАНОВО из слоя extract, а не
        спрашивается у Ledger. Спросить Ledger — значит сравнить mark() с
        mark(): обе величины растут только внутри него, равенство держится
        всегда, а ячейка, до mark() не дошедшая, отсутствует в обеих частях и
        исчезает бесследно. Этот тест обязан уметь краснеть — иначе он не тест,
        а тавтология.
        """
        for p_doc_id, doc in _extracted_docs(corpus):
            real = _real_cell_count(p_doc_id)
            assert doc.ledger.accounted == real, (
                f"{p_doc_id}: учтено {doc.ledger.accounted} из {real} "
                f"ячеек документа — {real - doc.ledger.accounted} потеряно молча"
            )

    def test_ledger_denominator_is_the_real_cell_count(self, corpus):
        """Знаменатель Ledger — то, что отдал extract, а не то, что он сам насчитал.

        Без этого теста можно «починить» инвариант, скормив Ledger заниженное
        число: accounted == total снова сойдётся, а ячейки продолжат пропадать.
        Нулевой total здесь не оправдание, а худший случай: документ, не
        позвавший account(), не учтён вообще.
        """
        for p_doc_id, doc in _extracted_docs(corpus):
            assert doc.ledger.total == _real_cell_count(p_doc_id), (
                f"{p_doc_id}: знаменатель Ledger ({doc.ledger.total}) разошёлся "
                f"с числом ячеек документа ({_real_cell_count(p_doc_id)})"
            )

    def test_not_extracted_documents_are_exactly_the_postgrad_six(self, corpus):
        """Исключение из учёта — по типу документа и только по нему.

        Список того, что мы намеренно не читаем, зафиксирован: 6 файлов
        аспирантуры. Появится седьмой «неучтённый» — тест покраснеет, и решение
        не считать его придётся принять явно, а не получить молча.
        """
        _, report = corpus
        not_extracted = [
            d for d in report.documents if d.doc_type in NOT_EXTRACTED_DOC_TYPES
        ]
        assert len(not_extracted) == POSTGRAD_FILES
        assert all(d.ledger.total == 0 for d in not_extracted)
        assert all(d.ledger.accounted == 0 for d in not_extracted)

    def test_every_nonempty_cell_has_a_home(self, corpus):
        docs = _extracted_docs(corpus)
        assert len(docs) == len(MANIFEST) - POSTGRAD_FILES
        real = sum(_real_cell_count(p_doc_id) for p_doc_id, _ in docs)
        assert real > 5000  # страховка от усохшего корпуса, не главный контроль
        assert sum(doc.ledger.accounted for _, doc in docs) == real

    def test_no_module_without_lessons(self, corpus):
        """Модуль, на который не легло ни одной пары, — фантом в списке.

        13497 p11 объявляет '2 модуль: 3 ноября – 15 января', но все пары этой
        страницы уехали в другой слот: остаётся период, в котором для студента
        пусто. Показывать его нечем и незачем.
        """
        session, _ = corpus
        empty = [
            (m.document_id, m.name, str(m.date_from), str(m.date_to))
            for m in session.scalars(select(Module)).all()
            if not session.scalar(
                select(func.count())
                .select_from(Lesson)
                .where(Lesson.module_id == m.id)
            )
        ]
        assert empty == [], f"модули без единой пары: {empty}"

    def test_unparsed_cells_all_have_reason_and_document(self, corpus):
        session, _ = corpus
        cells = session.scalars(select(UnparsedCell)).all()
        assert cells
        assert all(c.reason and c.raw_text.strip() and c.document_id for c in cells)


def test_current_fourth_course_pdf_corrects_mislabeled_group_37_to_47():
    """14178: страница 5 подписана 3.7, но это продолжение 4 курса — группа 4.7.

    Это отдельная актуальная регрессионная фикстура, а не часть исторического
    golden-корпуса: официальный файл появился 25.08.2026 уже после его снятия.
    В источнике опечатка в шапке, но две пары блока принадлежат 4.7 и не должны
    ни исчезать, ни попадать в каталог третьего курса.
    """
    content = (FIXTURES / "14178.pdf").read_bytes()
    session = make_session()
    try:
        report = importer.import_all(
            session,
            FakeFetcher(overrides={"14178": content}),
            links=[ScheduleLink("Осенний семестр", "4 курс", "14178")],
        )
        document = report.documents[0]
        course_four_lessons = session.scalar(
            select(func.count())
            .select_from(Lesson)
            .join(Group, Lesson.group_id == Group.id)
            .where(Group.course == 4)
        )
        reasons = session.scalars(select(UnparsedCell.reason)).all()
        lower_week_lesson = session.scalar(
            select(Lesson)
            .join(Group, Lesson.group_id == Group.id)
            .where(
                Group.number == "4.1",
                Lesson.subject == "Прикладная эконометрика",
                Lesson.weekday == 2,
                Lesson.pair_number == 3,
            )
        )

        assert document.error is None
        assert course_four_lessons >= 100
        assert document.unparsed <= 5
        assert importer.REASON_NO_PAIR not in reasons
        assert lower_week_lesson is not None
        assert lower_week_lesson.week_type is WeekType.LOWER
        group_47 = session.scalar(select(Group).where(Group.number == "4.7"))
        assert group_47 is not None
        assert session.scalars(
            select(Lesson.subject)
            .where(Lesson.group_id == group_47.id)
            .order_by(Lesson.pair_number)
        ).all() == ["Цифровая экономика", "Цифровая экономика"]
        assert session.scalar(select(Group).where(Group.number == "3.7")) is None
    finally:
        session.close()


def test_current_master_schedule_respects_since_date_for_all_evening_slots():
    """14159: ``С 09.09`` applies to every row of the three-pair block.

    Recognising the previously lost 20:05 slot must not widen the same source
    cell to the whole module.  Otherwise the app shows this class a week early.
    """
    content = (FIXTURES / "14159.pdf").read_bytes()
    session = make_session()
    try:
        report = importer.import_all(
            session,
            FakeFetcher(overrides={"14159": content}),
            links=[ScheduleLink("Осенний семестр", "маг.1 курс", "14159")],
        )
        group = session.scalar(
            select(Group).where(Group.program == "Учетные технологии и аудит")
        )
        assert group is not None
        lessons = session.scalars(
            select(Lesson)
            .where(
                Lesson.group_id == group.id,
                Lesson.subject == "Оценка инвестиционных проектов",
            )
            .order_by(Lesson.pair_number)
        ).all()

        assert report.failed == 0
        assert [lesson.pair_number for lesson in lessons] == [5, 6, 7]
        assert {lesson.valid_from for lesson in lessons} == {date(2026, 9, 9)}
        assert {lesson.valid_to for lesson in lessons} == {date(2026, 11, 1)}
    finally:
        session.close()


def test_single_schedule_date_is_kept_exact_instead_of_becoming_a_span():
    """A one-day lesson must not be visible on every same weekday in between."""
    session = make_session()
    try:
        importer.import_all(
            session,
            FakeFetcher(),
            links=[ScheduleLink("Осенний семестр", "1 курс", "13469")],
        )
        lessons = session.scalars(
            select(Lesson).where(Lesson.date_constraint_raw == "24.12")
        ).all()

        assert lessons
        assert {
            (lesson.valid_from, lesson.valid_to, tuple(lesson.specific_dates))
            for lesson in lessons
        } == {(date(2025, 12, 24), date(2025, 12, 24), ("2025-12-24",))}
    finally:
        session.close()


class TestGoldenCorpus:
    """Эталон СНАРУЖИ парсера: 23 извлекаемых документа против golden.json.

    prove() перепарсивает ячейки тем же parse_cell — мутацию самого парсера он
    не видит: соврут оба одинаково, инвариант сойдётся. Эталон — зафиксированный
    внешний факт: счётчики и полные сигнатуры пар (группа/день/пара/границы/
    предмет/преподаватель/аудитория/неделя/подгруппа/даты модуля/окно действия)
    И экзаменов (группа/предмет/преподаватель/консультация/экзамен/аудитория/
    форма). Он ловит и хирургические выпадения (−14 пар у 13497/13498 при зелёном
    ledger в атаке раунда 4), и порчу содержимого — сдвиг экзамена на сутки,
    съехавшее начало пары, схлопнутое окно модуля. Перегенерация — ТОЛЬКО
    осознанным запуском scripts/regen_golden.py, не починкой красного теста.
    """

    def test_corpus_matches_golden_reference(self, corpus):
        import difflib

        from tests import goldens

        session, _ = corpus
        golden = json.loads(goldens.GOLDEN_PATH.read_text(encoding="utf-8"))
        docs = _extracted_docs(corpus)
        assert sorted(golden) == sorted(p_doc_id for p_doc_id, _ in docs), (
            "состав извлекаемых документов разошёлся с эталоном — "
            "новый/пропавший файл требует осознанной перегенерации"
        )

        problems: list[str] = []
        for p_doc_id, _doc in docs:
            expected = golden[p_doc_id]
            # Фикстуру не правили руками: оба хэша обязаны сойтись со строками.
            assert goldens.signatures_hash(expected["signatures"]) == expected["hash"], (
                f"{p_doc_id}: golden.json внутренне противоречив — сигнатуры пар "
                "правлены в обход scripts/regen_golden.py"
            )
            assert (
                goldens.signatures_hash(expected["exam_signatures"])
                == expected["exam_hash"]
            ), (
                f"{p_doc_id}: golden.json внутренне противоречив — сигнатуры "
                "экзаменов правлены в обход scripts/regen_golden.py"
            )
            document = session.scalar(
                select(ScheduleDocument).where(
                    ScheduleDocument.p_doc_id == int(p_doc_id)
                )
            )
            actual = goldens.document_golden(session, document)
            if actual == expected:
                continue
            diff = "\n".join(
                difflib.unified_diff(
                    expected["signatures"], actual["signatures"],
                    fromfile=f"{p_doc_id}: эталон пар", tofile=f"{p_doc_id}: импорт пар",
                    lineterm="",
                )
            )
            exam_diff = "\n".join(
                difflib.unified_diff(
                    expected["exam_signatures"], actual["exam_signatures"],
                    fromfile=f"{p_doc_id}: эталон экз", tofile=f"{p_doc_id}: импорт экз",
                    lineterm="",
                )
            )
            body = "\n".join(part for part in (diff, exam_diff) if part)
            problems.append(
                f"{p_doc_id}: пар {expected['lessons']}→{actual['lessons']}, "
                f"экзаменов {expected['exams']}→{actual['exams']}, "
                f"unparsed {expected['unparsed']}→{actual['unparsed']}\n"
                f"{body or '(сигнатуры совпали — разошлись счётчики)'}"
            )
        assert not problems, (
            "импорт разошёлся с золотым эталоном:\n\n" + "\n\n".join(problems)
        )


class TestPairBounds:
    """Границы пары — внешние края её половин, а не середина.

    _pair_bounds берёт начало ПЕРВОЙ половины и конец ВТОРОЙ. Мутация,
    возвращающая конец первой половины как начало пары, сдвигает старт всех пар
    на 45 минут (08:00 → 08:45) — эталон это ловит, но прямой юнит против
    PAIR_HALVES прибивает поле к таблице напрямую, без прогона всего корпуса.
    """

    def test_pair_bounds_are_the_outer_edges_of_each_pair(self):
        from src.schedule.structure import PAIR_HALVES

        for pair_number, (first, second) in PAIR_HALVES.items():
            starts, ends = importer._pair_bounds(pair_number)
            assert starts == importer._as_time(first[0]), (
                f"пара {pair_number}: начало {starts} — не начало первой половины "
                f"{importer._as_time(first[0])}"
            )
            assert ends == importer._as_time(second[1]), (
                f"пара {pair_number}: конец {ends} — не конец второй половины "
                f"{importer._as_time(second[1])}"
            )


class TestCategoryMustBeProvenNotJustAssigned:
    """Метка категории НАЗНАЧАЕТ, но не ДОКАЗЫВАЕТ.

    Три раза подряд сторож «ни одна ячейка не теряется молча» ломался по-новому,
    и каждый раз выглядел настоящим. Третий: Ledger считал НАЛИЧИЕ метки, а не её
    ПРАВИЛЬНОСТЬ. Пометь настоящую пару заглушкой и не создай её — accounted ==
    total держится, а пара исчезает. Эти тесты требуют, чтобы у каждой категории
    был предикат, доказуемый содержимым/БД/позицией, а не одним ярлыком.
    """

    def _document(self, session):
        doc = ScheduleDocument(
            p_doc_id=1,
            section="s",
            label="l",
            doc_type=DocType.SEMESTER_GRID_BACHELOR,
            sha256="x",
            source_url="u",
        )
        session.add(doc)
        session.flush()
        return doc

    def _cell(self, text, row=5, col=3):
        from src.schedule.grid import Cell

        return Cell(row=row, col_start=col, col_end=col, text=text)

    def test_placeholder_label_on_a_real_lesson_is_not_proven(self):
        """Атака ревью дословно: непустую пару метят CELL_PLACEHOLDER.

        is_placeholder('Философия (л) …') ложно — значит категория не доказана,
        ячейка из accounted выпадает, инвариант краснеет.
        """
        session = make_session()
        doc = self._document(session)
        ledger = importer.Ledger()
        ledger._total = 1
        ledger.mark(0, self._cell("Философия (л) Иванов И.И. ауд.301"), importer.CELL_PLACEHOLDER)
        ledger.prove(session, doc)
        assert ledger.accounted == 0, "заглушка-ложь принята за учтённую ячейку"
        session.close()

    def test_lesson_label_without_a_lesson_row_is_not_proven(self):
        """Симметричная атака: настоящую заглушку метят CELL_LESSON, но Lesson
        в БД не создают. Перепарс даёт заглушку, строк с cell_key ячейки нет —
        категория недоказана."""
        session = make_session()
        doc = self._document(session)
        ledger = importer.Ledger()
        ledger._total = 1
        ledger.mark(0, self._cell("……………."), importer.CELL_LESSON)
        ledger.prove(session, doc)
        assert ledger.accounted == 0, "категория lesson без строки Lesson в БД принята"
        session.close()

    def test_structural_label_without_position_is_not_proven(self):
        """Непустую пару прячут в «структуру» голым mark(). Позиции нет —
        _positional пуст, — значит и доказательства нет."""
        session = make_session()
        doc = self._document(session)
        ledger = importer.Ledger()
        ledger._total = 1
        ledger.mark(0, self._cell("Философия (л) Иванов И.И. ауд.301"), importer.CELL_STRUCTURAL)
        ledger.prove(session, doc)
        assert ledger.accounted == 0, "структура без позиции принята за учтённую ячейку"
        session.close()

    def test_proven_categories_are_counted(self):
        """Обратная сторона: доказанные категории учитываются — иначе честный
        документ краснел бы. empty (пусто), placeholder (is_placeholder),
        unparsed (строка в БД), structural (позиция)."""
        session = make_session()
        doc = self._document(session)
        unparsed_text = "нечитаемая ячейка"
        # cell_key — координата ячейки (таблица 0, строка 3, колонка 3): очередь
        # доказывает ИМЕННО эту ячейку, а не «где-то есть такой текст».
        session.add(
            UnparsedCell(
                document_id=doc.id, page=1, raw_text=unparsed_text, reason="r",
                cell_key="0:3:3",
            )
        )
        session.flush()

        ledger = importer.Ledger()
        ledger._total = 4
        ledger.mark(0, self._cell("   ", row=1), importer.CELL_EMPTY)
        ledger.mark(0, self._cell("……………", row=2), importer.CELL_PLACEHOLDER)
        ledger.mark(0, self._cell(unparsed_text, row=3), importer.CELL_UNPARSED)
        ledger.mark_structural(0, self._cell("Понедельник", row=4))
        ledger.prove(session, doc)
        assert ledger.accounted == 4, "доказанные категории не учтены"
        session.close()

    def test_the_audit_attack_verbatim_reddens_the_invariant(self, monkeypatch):
        """Дословная атака аудита через настоящий корпус.

        Условие ревью: `parsed.lessons and any(p.subgroup == 2 …)` → ячейку
        помечают заглушкой и пару НЕ создают. Раньше 413/413 зелёные. Теперь
        prove() сверяет is_placeholder(text) — и хотя бы у одного документа
        accounted расходится с числом ячеек: инвариант краснеет.
        """
        from src.schedule.cells import CellParse

        real_parse = importer.parse_cell
        hidden: list[str] = []

        def lying_parse(text):
            result = real_parse(text)
            if result.lessons and any(p.subgroup == 2 for p in result.lessons):
                hidden.append(text)
                return CellParse(lessons=(), reason=None, is_placeholder=True)
            return result

        monkeypatch.setattr(importer, "parse_cell", lying_parse)
        session = make_session()
        report = importer.import_all(session, FakeFetcher())
        assert hidden, "атака не затронула ни одной ячейки — проверка бессмысленна"

        caught = [
            (doc.p_doc_id, doc.ledger.accounted, _real_cell_count(doc.p_doc_id))
            for doc in report.documents
            if doc.ledger.total
            and doc.ledger.accounted != _real_cell_count(doc.p_doc_id)
        ]
        assert caught, "спрятанные под заглушку пары прошли мимо инварианта молча"
        session.close()


class TestCoversWholeSemesterIsNotVacuouslyTrue:
    def test_no_calendar_means_not_the_whole_semester(self):
        """all([]) вакуумно истинно: без календаря недель КАЖДЫЙ безымянный
        модуль объявлялся бы мнимым семестром и выбрасывался. Нечем доказать —
        значит не семестр, модуль сохраняем."""
        from datetime import date as _date

        assert (
            importer._covers_whole_semester(_date(2026, 2, 9), _date(2026, 6, 26), [])
            is False
        )


class TestExamRowLedger:
    def test_row_kinds_agrees_with_parse_exams(self):
        """row_kinds считает строки с нагрузкой, parse_exams — исходы по ним.

        Это две функции об одном и том же в одном файле: разъедутся — и ledger
        начнёт врать «всё учтено», пока экзамены будут пропадать.
        """
        from src.schedule.exams import parse_exams, row_kinds
        from src.schedule.extract_pdf import extract_pdf

        for p_doc_id in ("13745", "14049", "13768"):
            grids = extract_pdf(FILES[p_doc_id].read_bytes())
            result = parse_exams(grids)
            payload = sum(1 for kind in row_kinds(grids).values() if kind == "payload")
            assert payload == result.subject_rows_seen == len(result.exams) + len(
                result.unparsed
            ), f"{p_doc_id}: строки сессии разошлись с исходами"


class TestPageHeadingIsTakenOutsideTheTable:
    """Заголовок страницы — это текст ВНЕ таблицы.

    page.extract_text() отдаёт весь текст страницы, включая ячейки. Маркер
    'Верхняя неделя' внутри ячейки относится к ОДНОЙ паре (план §A6 Step 4), но
    через page_week красил страницу целиком — и еженедельные пары исчезали у
    студента на нижней неделе.
    """

    def test_week_marker_inside_a_cell_does_not_paint_the_page(self):
        # 13820 p5: ячейка R8C2 = 'Верхняя неделя Воображение, изображение и
        # реальность (л) онлайн' — маркер одной пары, не страницы.
        texts = importer._pdf_page_texts(FILES["13820"].read_bytes())
        assert week_type_from_heading(texts[5]) is None, (
            "маркер из ячейки утёк в заголовок страницы"
        )

    def test_page_level_week_marker_is_still_read(self):
        """Обратная сторона: настоящие маркеры страницы обязаны выжить.

        Их в корпусе ровно 4, все вне таблицы. Отфильтровать таблицу «на всякий
        случай» целиком — значит потерять их и сломать 13471/13472.
        """
        expected = {
            ("13471", 10): WeekType.UPPER,   # 'ВЕРХНЯЯ НЕДЕЛЯ'
            ("13471", 11): WeekType.LOWER,   # 'НИЖНЯЯ НЕДЕЛЯ'
            ("13472", 14): WeekType.UPPER,   # 'НЕДЕЛЯ: ВЕРХНЯЯ'
            ("13472", 15): WeekType.LOWER,   # 'НЕДЕЛЯ: НИЖНЯЯ'
        }
        for (p_doc_id, page), want in expected.items():
            texts = importer._pdf_page_texts(FILES[p_doc_id].read_bytes())
            assert week_type_from_heading(texts[page]) == want, (
                f"{p_doc_id} p{page}: потерян настоящий маркер страницы"
            )

    def test_only_the_marked_pair_is_upper_the_rest_stay_weekly(self):
        """13820: 45 еженедельных пар остаются еженедельными (week_type=None)."""
        session = make_session()
        fetcher = FakeFetcher()
        links = [
            link
            for link in parse_index(fetcher.fetch_index())
            if link.p_doc_id == "13820"
        ]
        importer.import_all(session, fetcher, links=links)

        lessons = session.scalars(select(Lesson)).all()
        painted = [
            lesson
            for lesson in lessons
            if lesson.week_type is not None and "едел" not in (lesson.cell_raw or "")
        ]
        assert painted == [], (
            f"{len(painted)} пар без маркера покрашены страницей — "
            "на нижней неделе они исчезнут у студента"
        )
        # А сама маркированная пара — upper: маркер не потерян вместе с утечкой.
        # Проверяем по cell_raw, а не по названию предмета: 'Воображение…' идёт
        # ещё и семинарами в других ячейках, и те еженедельные законно.
        marked = [
            lesson
            for lesson in lessons
            if "Верхняя неделя" in (lesson.cell_raw or "")
        ]
        assert marked, "маркированная пара пропала"
        assert all(m.week_type == WeekType.UPPER for m in marked)
        assert all("Верхняя неделя" not in m.subject for m in marked), (
            "маркер уехал в название предмета"
        )
        session.close()


class TestSemesterHeadingIsNotAModule:
    """'I семестр (1 сентября – 15 января)' — подпись СЕМЕСТРА, не модуля.

    Слова «модуль» в ней нет, и фолбэк «любой диапазон дат» принимал её за
    безымянный модуль во весь семестр. Модули после этого перекрывались, а союз
    диапазонов растягивал их за срок группы.
    """

    def _modules(self, p_doc_id):
        session = make_session()
        fetcher = FakeFetcher()
        links = [
            link
            for link in parse_index(fetcher.fetch_index())
            if link.p_doc_id == p_doc_id
        ]
        importer.import_all(session, fetcher, links=links)
        modules = [
            (m.name, m.date_from.isoformat(), m.date_to.isoformat())
            for m in session.scalars(select(Module)).all()
        ]
        session.close()
        return modules

    def test_semester_caption_does_not_create_a_module(self):
        # 13471 T7 (стр.8): 'I семестр (1 сентября – 15 января)'
        modules = self._modules("13471")
        assert ("I модуль", "2025-09-01", "2025-11-02") in modules
        assert ("2 модуль", "2025-11-04", "2026-01-11") in modules
        assert len(modules) == 2, (
            f"подпись семестра стала модулем: {modules}"
        )

    def test_page_without_a_module_does_not_inherit_a_foreign_one(self):
        """13471 T7 — семестровая страница группы 3.7: модуля у неё нет.

        Своя шапка = новый блок. Унаследовав '2 модуль' (4 ноября – 11 января)
        от предыдущего блока, 35 пар группы 3.7 стали бы невидимы в сентябре и
        октябре — притом что идут они весь семестр. Нет модуля → нет и ограничения
        по датам, это честнее выдуманного срока.
        """
        session = make_session()
        fetcher = FakeFetcher()
        links = [
            link
            for link in parse_index(fetcher.fetch_index())
            if link.p_doc_id == "13471"
        ]
        importer.import_all(session, fetcher, links=links)

        group = session.scalar(select(Group).where(Group.number == "3.7"))
        lessons = session.scalars(
            select(Lesson).where(Lesson.group_id == group.id)
        ).all()
        assert lessons
        assert all(
            lesson.module_id is None
            and lesson.valid_from is None
            and lesson.valid_to is None
            for lesson in lessons
        ), "странице без модуля достался чужой срок"
        session.close()

    def test_semester_wide_range_on_its_own_line_is_not_a_module(self):
        """13822 p13: 'весенний семестр 2025-2026 учебный год' и '9 февраля –
        26 июня' стоят РАЗНЫМИ строками — фильтр «слово вплотную перед
        диапазоном» их не связывает, и в списке модулей появлялся фантом
        {name: None, 9 февраля – 26 июня} с 7 парами. Ключ не в слове, а в
        датах: диапазон накрывает ВСЕ 20 недель календаря файла. Модуль — часть
        семестра; то, что накрывает семестр целиком, и есть семестр.
        """
        modules = self._modules("13822")
        assert (None, "2026-02-09", "2026-06-26") not in modules, (
            f"весь семестр стал модулем: {modules}"
        )
        assert ("I модуль", "2026-02-09", "2026-04-12") in modules
        assert ("II модуль", "2026-04-13", "2026-06-22") in modules
        assert len(modules) == 2, modules

    def test_pages_of_the_semester_wide_block_keep_their_lessons(self):
        """Обратная сторона: фантом-семестр убираем, пары — нет.

        Модуля у настоящего семестрового блока (13822 p13) нет — и правильно:
        нет модуля → нет ограничения по датам, как на 13471 T7. Их 7 (Чт ×6 +
        восстановленный языковой блок Вт ×1). Раньше в module=None падали ещё и
        страницы-продолжения, потерявшие свой модуль (БАГ 2): их было 77. После
        переноса модуля вперёд по страницам-продолжениям module=None остаётся
        ровно у семестровых 7 — остальные вернулись к своим модулям.

        Всего пар 297: к прежним 239 подтверждённым парам добавились 58
        субботних дисциплин МУАМ, которые раньше целиком уходили в unparsed как
        «несколько занятий без границ». Две «подгруппы» на p11 по-прежнему
        исключены как фантом от съезда ячейки на 6% в колонку соседа.
        """
        session = make_session()
        fetcher = FakeFetcher()
        links = [
            link
            for link in parse_index(fetcher.fetch_index())
            if link.p_doc_id == "13822"
        ]
        importer.import_all(session, fetcher, links=links)

        lessons = session.scalars(select(Lesson)).all()
        assert len(lessons) == 297, "пары потеряны вместе с фантомом или МУАМ"
        by_module = Counter(lesson.module_id for lesson in lessons)
        assert by_module[None] == 7, (
            "module=None должен остаться только у семестрового блока p13, "
            f"а не у страниц-продолжений: {dict(by_module)}"
        )
        weekly = [lesson for lesson in lessons if lesson.module_id is None]
        assert all(
            lesson.valid_from is None and lesson.valid_to is None
            for lesson in weekly
        )
        session.close()

    def test_nameless_part_of_the_semester_survives_the_word_semester(self):
        """Запрет по слову «семестр» в заголовке убил бы настоящие модули.

        13828 p1 подписан '9 февраля – 07 апреля' в той же шапке, где стоит
        'на весенний семестр 2025-2026 учебный год'. Это модуль: он накрывает
        часть недель календаря, а не все.
        """
        assert (None, "2026-02-09", "2026-04-07") in self._modules("13828"), (
            "настоящий безымянный модуль убит словом «семестр» по соседству"
        )

    def test_nameless_module_with_real_dates_survives(self):
        """Обратная сторона: безымянный модуль с настоящими датами — модуль.

        13469 T4 подписан просто '24 ноября – 11 января', слова «модуль» там
        нет (решение №5 плана: ключ модуля — даты, а не имя). Запретить голый
        диапазон совсем — значит слить его пары со 2-м модулем и показать их
        студенту не в те даты.
        """
        modules = self._modules("13469")
        assert (None, "2025-11-24", "2026-01-11") in modules, (
            f"безымянный модуль потерян: {modules}"
        )


class TestIdempotency:
    def test_second_run_changes_nothing(self):
        session = make_session()
        fetcher = FakeFetcher()
        first = importer.import_all(session, fetcher)
        before = _snapshot(session)

        second = importer.import_all(session, fetcher)
        after = _snapshot(session)

        assert before == after, "второй прогон тех же файлов изменил данные"
        assert all(
            d.status == importer.STATUS_UNCHANGED
            for d in second.documents
            if d.doc_type
            in (DocType.SEMESTER_GRID_BACHELOR, DocType.SEMESTER_GRID_MASTER, DocType.EXAM_SESSION)
        )
        assert first.documents[0].p_doc_id == second.documents[0].p_doc_id
        session.close()


_REVIEWED_DOCUMENT_ID = "14159"
_REVIEWED_LINK = ScheduleLink(
    "Осенний семестр",
    "маг.1 курс",
    _REVIEWED_DOCUMENT_ID,
)


def _import_reviewed_master(
    session,
    *,
    review_bundle: ReviewBundle | None = None,
    content: bytes | None = None,
    atomic: bool = False,
):
    source = (
        content
        if content is not None
        else (FIXTURES / "14159.pdf").read_bytes()
    )
    return importer.import_all(
        session,
        FakeFetcher(overrides={_REVIEWED_DOCUMENT_ID: source}),
        links=[_REVIEWED_LINK],
        atomic=atomic,
        review_bundle=review_bundle,
    )


def _reviewed_document_and_states(session):
    document = session.scalar(
        select(ScheduleDocument).where(
            ScheduleDocument.p_doc_id == int(_REVIEWED_DOCUMENT_ID)
        )
    )
    assert document is not None
    lessons = session.scalars(
        select(Lesson)
        .where(Lesson.document_id == document.id)
        .order_by(Lesson.id)
    ).all()
    assert lessons
    states = tuple(
        lesson_state(lesson, p_doc_id=_REVIEWED_DOCUMENT_ID)
        for lesson in lessons
    )
    return document, lessons, states


def _reviewed_from_signatures(
    document: ScheduleDocument,
    signatures: tuple[str, ...],
) -> ReviewedDocument:
    signatures = tuple(sorted(signatures))
    payload = json.dumps(
        list(signatures),
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return ReviewedDocument(
        p_doc_id=str(document.p_doc_id),
        sha256=document.sha256,
        lesson_hash=hashlib.sha256(payload).hexdigest(),
        signatures=signatures,
    )


def _review_bundle(
    document: ScheduleDocument,
    states,
    *operations: CorrectionOperation,
) -> ReviewBundle:
    signatures = tuple(state_signature(state) for state in states)
    reviewed = _reviewed_from_signatures(document, signatures)
    corrections = DocumentCorrections(
        p_doc_id=str(document.p_doc_id),
        sha256=document.sha256,
        operations=tuple(operations),
    )
    return ReviewBundle(
        corrections=CorrectionRegistry(
            documents={str(document.p_doc_id): corrections}
        ),
        reviewed_documents={str(document.p_doc_id): reviewed},
    )


def _empty_review_bundle(*p_doc_ids: str) -> ReviewBundle:
    signatures: tuple[str, ...] = ()
    payload = json.dumps(
        list(signatures),
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    lesson_hash = hashlib.sha256(payload).hexdigest()
    corrections = {
        p_doc_id: DocumentCorrections(
            p_doc_id=p_doc_id,
            sha256="a" * 64,
            operations=(),
        )
        for p_doc_id in p_doc_ids
    }
    reviewed = {
        p_doc_id: ReviewedDocument(
            p_doc_id=p_doc_id,
            sha256="a" * 64,
            lesson_hash=lesson_hash,
            signatures=signatures,
        )
        for p_doc_id in p_doc_ids
    }
    return ReviewBundle(
        corrections=CorrectionRegistry(documents=corrections),
        reviewed_documents=reviewed,
    )


def _document_report(report, p_doc_id: str = _REVIEWED_DOCUMENT_ID):
    return next(item for item in report.documents if item.p_doc_id == p_doc_id)


class TestReviewedImporterIntegration:
    @pytest.mark.parametrize(
        ("links", "review_bundle"),
        (
            ((_REVIEWED_LINK, _REVIEWED_LINK), _empty_review_bundle("14159")),
            (
                (
                    ScheduleLink("Осенний семестр", "1 курс", "13469"),
                    ScheduleLink("Осенний семестр", "1 курс", "13469"),
                ),
                None,
            ),
            (
                (
                    ScheduleLink("Осенний семестр", "1 курс", "13469"),
                    ScheduleLink("Весенний семестр", "другая подпись", "13469"),
                ),
                None,
            ),
        ),
    )
    def test_duplicate_document_links_are_rejected_before_database_query(
        self,
        monkeypatch,
        links,
        review_bundle,
    ):
        session = make_session(autoflush=False)
        fetcher = FakeFetcher()
        original_scalars = session.scalars

        def database_query_is_too_late(*_args, **_kwargs):
            raise AssertionError("database queried before duplicate-link preflight")

        monkeypatch.setattr(session, "scalars", database_query_is_too_late)
        try:
            with pytest.raises(
                ReviewValidationError,
                match="duplicate schedule document id",
            ):
                importer.import_all(
                    session,
                    fetcher,
                    links=links,
                    review_bundle=review_bundle,
                )
        finally:
            monkeypatch.setattr(session, "scalars", original_scalars)

        assert fetcher.requested == []
        assert session.scalar(select(func.count()).select_from(ScheduleDocument)) == 0
        session.close()

    @pytest.mark.parametrize("p_doc_id", ("001", "0", "-1", "not-an-id", 0, True))
    def test_malformed_document_link_is_rejected_deterministically_before_query(
        self,
        monkeypatch,
        p_doc_id,
    ):
        session = make_session(autoflush=False)
        fetcher = FakeFetcher()
        original_scalars = session.scalars

        def database_query_is_too_late(*_args, **_kwargs):
            raise AssertionError("database queried before link-id preflight")

        monkeypatch.setattr(session, "scalars", database_query_is_too_late)
        try:
            with pytest.raises(ReviewValidationError, match="invalid link document id"):
                importer.import_all(
                    session,
                    fetcher,
                    links=[ScheduleLink("Семестр", "курс", p_doc_id)],
                )
        finally:
            monkeypatch.setattr(session, "scalars", original_scalars)

        assert fetcher.requested == []
        assert session.scalar(select(func.count()).select_from(ScheduleDocument)) == 0
        session.close()

    @pytest.mark.parametrize(
        ("links", "managed_ids", "missing_id"),
        (
            ((), ("14159",), "14159"),
            ((_REVIEWED_LINK,), ("14159", "14160"), "14160"),
        ),
    )
    def test_missing_managed_document_is_rejected_before_any_database_query(
        self,
        monkeypatch,
        links,
        managed_ids,
        missing_id,
    ):
        session = make_session(autoflush=False)
        original_scalars = session.scalars

        def database_query_is_too_late(*_args, **_kwargs):
            raise AssertionError("database queried before complete managed-set check")

        monkeypatch.setattr(session, "scalars", database_query_is_too_late)
        try:
            with pytest.raises(
                ReviewValidationError,
                match=rf"managed documents missing.*{missing_id}",
            ):
                importer.import_all(
                    session,
                    FakeFetcher(),
                    links=links,
                    review_bundle=_empty_review_bundle(*managed_ids),
                )
        finally:
            monkeypatch.setattr(session, "scalars", original_scalars)

        assert session.scalar(select(func.count()).select_from(ScheduleDocument)) == 0
        assert not session.new and not session.dirty and not session.deleted
        session.close()

    @pytest.mark.parametrize("autoflush", (False, True))
    def test_review_bundle_rejects_dirty_entry_without_flushing_or_breaking_session(
        self,
        autoflush,
    ):
        session = make_session(autoflush=autoflush)
        pending = Lesson()
        session.add(pending)
        try:
            with pytest.raises(
                ReviewValidationError,
                match="reviewed import requires a clean session boundary",
            ):
                importer.import_all(
                    session,
                    FakeFetcher(),
                    links=[],
                    review_bundle=_empty_review_bundle(),
                )

            assert pending.id is None
            assert pending in session.new
            session.expunge(pending)
            assert session.is_active
            assert session.scalar(select(func.count()).select_from(Lesson)) == 0
        finally:
            session.close()

    def test_reviewed_import_rejects_flushed_external_transaction_before_fetch(
        self,
        monkeypatch,
    ):
        session = make_session(autoflush=False)
        group = Group(
            course=9,
            number="9.8",
            program=None,
            level=EducationLevel.BACHELOR,
        )
        external = Lesson(
            group=group,
            weekday=0,
            pair_number=1,
            starts_at=datetime(2027, 9, 1, 8, 0).time(),
            ends_at=datetime(2027, 9, 1, 9, 35).time(),
            subject="External caller lesson",
            lesson_kind=LessonKind.LECTURE,
            teacher_id=None,
            room=None,
            week_type=None,
            subgroup=0,
            date_constraint_raw=None,
            cell_raw=None,
            cell_key=None,
            valid_from=None,
            valid_to=None,
            specific_dates=[],
        )
        session.add(external)
        session.flush()
        external_id = external.id
        fetcher = FakeFetcher()

        def fetch_is_too_late():
            raise AssertionError("fetch started inside caller transaction")

        monkeypatch.setattr(fetcher, "fetch_index", fetch_is_too_late)
        try:
            with pytest.raises(ReviewValidationError, match="active transaction"):
                importer.import_all(
                    session,
                    fetcher,
                    review_bundle=_empty_review_bundle(),
                )

            assert session.is_active
            assert session.in_transaction()
            assert session.get(Lesson, external_id) is external
            session.rollback()
            assert session.get(Lesson, external_id) is None
        finally:
            session.close()

    def test_reviewed_import_rejects_read_only_autobegin_before_fetch(
        self,
        monkeypatch,
    ):
        session = make_session()
        assert session.scalar(select(func.count()).select_from(Lesson)) == 0
        assert session.in_transaction()
        fetcher = FakeFetcher()

        def fetch_is_too_late():
            raise AssertionError("fetch started inside caller read transaction")

        monkeypatch.setattr(fetcher, "fetch_index", fetch_is_too_late)
        try:
            with pytest.raises(ReviewValidationError, match="active transaction"):
                importer.import_all(
                    session,
                    fetcher,
                    review_bundle=_empty_review_bundle(),
                )

            assert session.is_active
            assert session.in_transaction()
        finally:
            session.rollback()
            session.close()

    def test_reviewed_import_accepts_a_fresh_session_boundary(self):
        session = make_session()
        try:
            report = importer.import_all(
                session,
                FakeFetcher(),
                links=[],
                review_bundle=_empty_review_bundle(),
            )

            assert report.documents == []
        finally:
            session.rollback()
            session.close()

    def test_legacy_import_keeps_its_existing_session_boundary_behavior(self):
        session = make_session(autoflush=True)
        pending = Group(
            course=9,
            number="9.9",
            program=None,
            level=EducationLevel.BACHELOR,
        )
        session.add(pending)
        try:
            report = importer.import_all(session, FakeFetcher(), links=[])

            assert report.documents == []
            assert pending.id is not None
            assert session.get(Group, pending.id) is pending
        finally:
            session.rollback()
            session.close()

    def test_unmanaged_same_hash_keeps_unchanged_status_and_cache(self):
        session = make_session(autoflush=False)
        empty_bundle = ReviewBundle(
            corrections=CorrectionRegistry(documents={}),
            reviewed_documents={},
        )
        try:
            first = _import_reviewed_master(session, review_bundle=empty_bundle)
            before = _snapshot(session)
            session.rollback()
            second = _import_reviewed_master(session, review_bundle=empty_bundle)

            assert _document_report(first).status == importer.STATUS_IMPORTED
            assert _document_report(second).status == importer.STATUS_UNCHANGED
            assert _snapshot(session) == before
        finally:
            session.close()

    def test_managed_same_hash_reparses_and_repairs_corrupted_lesson(self):
        session = make_session(autoflush=False)
        try:
            _import_reviewed_master(session)
            document, lessons, states = _reviewed_document_and_states(session)
            bundle = _review_bundle(document, states)
            expected = reviewed_document_output(session, document)

            lessons[0].room = "WRONG"
            session.commit()
            report = _import_reviewed_master(session, review_bundle=bundle)

            assert _document_report(report).status == importer.STATUS_REIMPORTED
            assert reviewed_document_output(session, document) == expected
            assert _document_report(report).lessons == len(expected.signatures)
        finally:
            session.close()

    @pytest.mark.parametrize(
        ("operation_name", "delta"),
        (("add", 1), ("remove", -1)),
    )
    def test_report_lesson_count_includes_manual_add_or_remove(
        self,
        operation_name,
        delta,
    ):
        session = make_session(autoflush=False)
        try:
            _import_reviewed_master(session)
            document, _, states = _reviewed_document_and_states(session)
            before = states[0]
            if operation_name == "add":
                after = replace(
                    before,
                    subject=f"{before.subject} — ручная проверка",
                    cell_raw="Ручная проверка по официальному PDF",
                )
                expected_states = (*states, after)
                operation = CorrectionOperation(
                    id="integration-add-count",
                    operation="add",
                    page=1,
                    evidence="reviewed PDF page 1",
                    expected_before=None,
                    after=after,
                )
            else:
                expected_states = states[1:]
                operation = CorrectionOperation(
                    id="integration-remove-count",
                    operation="remove",
                    page=1,
                    evidence="reviewed PDF page 1",
                    expected_before=before,
                    after=None,
                )
            bundle = _review_bundle(document, expected_states, operation)
            session.rollback()

            report = _import_reviewed_master(session, review_bundle=bundle)
            document_report = _document_report(report)

            assert document_report.lessons == len(states) + delta
            assert reviewed_document_output(session, document) == (
                bundle.reviewed_documents[_REVIEWED_DOCUMENT_ID]
            )
        finally:
            session.close()

    def test_replace_diff_describes_final_corrected_rows_and_replay_is_stable(self):
        session = make_session(autoflush=False)
        try:
            _import_reviewed_master(session)
            document, _, states = _reviewed_document_and_states(session)
            before = states[0]
            after = replace(before, room="MANUAL-209")
            expected_states = (after, *states[1:])
            operation = CorrectionOperation(
                id="integration-replace-room",
                operation="replace",
                page=1,
                evidence="reviewed PDF page 1",
                expected_before=before,
                after=after,
            )
            bundle = _review_bundle(document, expected_states, operation)
            session.rollback()

            first = _import_reviewed_master(session, review_bundle=bundle)
            first_report = _document_report(first)
            first_output = reviewed_document_output(session, document)
            session.rollback()
            second = _import_reviewed_master(session, review_bundle=bundle)
            second_report = _document_report(second)

            assert first_report.status == importer.STATUS_REIMPORTED
            assert first_report.lessons == len(states)
            assert first_report.diff is not None
            assert any("MANUAL-209" in item for item in first_report.diff.added)
            assert first_output == bundle.reviewed_documents[_REVIEWED_DOCUMENT_ID]
            assert second_report.status == importer.STATUS_REIMPORTED
            assert second_report.diff is not None and second_report.diff.is_empty
            assert reviewed_document_output(session, document) == first_output
            assert session.scalar(
                select(func.count())
                .select_from(Lesson)
                .where(Lesson.document_id == document.id)
            ) == len(states)
        finally:
            session.close()

    def test_teacher_only_correction_produces_non_empty_final_diff(self):
        session = make_session(autoflush=False)
        try:
            _import_reviewed_master(session)
            document, _, states = _reviewed_document_and_states(session)
            before = states[0]
            after = replace(before, teacher="Ревьюер Р.Р.")
            operation = CorrectionOperation(
                id="integration-replace-teacher",
                operation="replace",
                page=1,
                evidence="reviewed PDF page 1",
                expected_before=before,
                after=after,
            )
            bundle = _review_bundle(document, (after, *states[1:]), operation)
            session.rollback()

            report = _import_reviewed_master(session, review_bundle=bundle)
            diff = _document_report(report).diff

            assert diff is not None and not diff.is_empty
            assert any("препод=Ревьюер Р.Р." in item for item in diff.added)
            assert any(
                f"препод={before.teacher or ''}" in item for item in diff.removed
            )
        finally:
            session.close()

    def test_changed_managed_pdf_is_rejected_before_classification_and_preserves_data(
        self,
        monkeypatch,
    ):
        session = make_session(autoflush=False)
        try:
            _import_reviewed_master(session)
            document, _, states = _reviewed_document_and_states(session)
            bundle = _review_bundle(document, states)
            expected = reviewed_document_output(session, document)

            def classification_must_not_run(_content):
                raise RuntimeError("classification ran before source guard")

            monkeypatch.setattr(importer, "_classify", classification_must_not_run)
            session.rollback()
            report = _import_reviewed_master(
                session,
                review_bundle=bundle,
                content=b"%PDF-1.4\nchanged-reviewed-source",
            )
            failed = _document_report(report)

            assert failed.status == importer.STATUS_FAILED
            assert "changed and requires review" in (failed.error or "")
            assert reviewed_document_output(session, document) == expected
        finally:
            session.close()

    def test_claimed_hash_cannot_hide_changed_content_in_non_atomic_import(self):
        session = make_session(autoflush=False)
        try:
            _import_reviewed_master(session)
            document, _, states = _reviewed_document_and_states(session)
            bundle = _review_bundle(document, states)
            expected = reviewed_document_output(session, document)
            fetcher = FakeFetcher(
                overrides={
                    _REVIEWED_DOCUMENT_ID: b"%PDF-1.4\nchanged-but-old-hash-claimed"
                },
                claimed_hashes={_REVIEWED_DOCUMENT_ID: document.sha256},
            )
            session.rollback()

            report = importer.import_all(
                session,
                fetcher,
                links=[_REVIEWED_LINK],
                review_bundle=bundle,
            )
            failed = _document_report(report)

            assert failed.status == importer.STATUS_FAILED
            assert _REVIEWED_DOCUMENT_ID in (failed.error or "")
            assert "fetched content SHA-256 mismatch" in (failed.error or "")
            assert reviewed_document_output(session, document) == expected
        finally:
            session.close()

    def test_claimed_hash_cannot_hide_changed_content_in_atomic_import(self):
        session = make_session(autoflush=False)
        try:
            _import_reviewed_master(session)
            document, _, states = _reviewed_document_and_states(session)
            bundle = _review_bundle(document, states)
            expected = reviewed_document_output(session, document)
            fetcher = FakeFetcher(
                overrides={
                    _REVIEWED_DOCUMENT_ID: b"%PDF-1.4\nchanged-but-old-hash-claimed"
                },
                claimed_hashes={_REVIEWED_DOCUMENT_ID: document.sha256},
            )
            session.rollback()

            with pytest.raises(
                ReviewValidationError,
                match=rf"{_REVIEWED_DOCUMENT_ID}.*fetched content SHA-256 mismatch",
            ):
                importer.import_all(
                    session,
                    fetcher,
                    links=[_REVIEWED_LINK],
                    atomic=True,
                    review_bundle=bundle,
                )
            session.rollback()

            assert reviewed_document_output(session, document) == expected
        finally:
            session.close()

    def test_atomic_managed_hash_failure_rolls_back_the_whole_snapshot(self):
        session = make_session(autoflush=False)
        try:
            _import_reviewed_master(session)
            document, _, states = _reviewed_document_and_states(session)
            bundle = _review_bundle(document, states)
            expected = reviewed_document_output(session, document)
            links = [
                ScheduleLink("Осенний семестр", "1 курс", "13469"),
                _REVIEWED_LINK,
            ]
            fetcher = FakeFetcher(
                overrides={
                    _REVIEWED_DOCUMENT_ID: b"%PDF-1.4\nchanged-reviewed-source"
                }
            )
            session.rollback()

            with pytest.raises(ReviewValidationError, match="requires review"):
                importer.import_all(
                    session,
                    fetcher,
                    links=links,
                    atomic=True,
                    review_bundle=bundle,
                )
            session.rollback()

            assert session.scalar(
                select(ScheduleDocument).where(ScheduleDocument.p_doc_id == 13469)
            ) is None
            assert reviewed_document_output(session, document) == expected
        finally:
            session.close()

    def test_managed_zero_operation_document_is_still_validated(self):
        session = make_session(autoflush=False)
        try:
            _import_reviewed_master(session)
            document, _, states = _reviewed_document_and_states(session)
            expected = reviewed_document_output(session, document)
            corrupted_signatures = list(expected.signatures)
            corrupted_signatures[0] += "-not-in-the-pdf"
            bad_expected = _reviewed_from_signatures(
                document,
                tuple(corrupted_signatures),
            )
            bundle = ReviewBundle(
                corrections=CorrectionRegistry(
                    documents={
                        _REVIEWED_DOCUMENT_ID: DocumentCorrections(
                            p_doc_id=_REVIEWED_DOCUMENT_ID,
                            sha256=document.sha256,
                            operations=(),
                        )
                    }
                ),
                reviewed_documents={_REVIEWED_DOCUMENT_ID: bad_expected},
            )
            session.rollback()

            report = _import_reviewed_master(session, review_bundle=bundle)
            failed = _document_report(report)

            assert failed.status == importer.STATUS_FAILED
            assert failed.doc_type == document.doc_type
            assert "reviewed schedule mismatch" in (failed.error or "")
            assert reviewed_document_output(session, document) == expected
            assert len(states) == len(expected.signatures)
        finally:
            session.close()

    def test_fresh_review_mismatch_reports_the_classified_document_type(self):
        session = make_session(autoflush=False)
        source = (FIXTURES / "14159.pdf").read_bytes()
        source_sha256 = hashlib.sha256(source).hexdigest()
        signatures = ("not the reviewed schedule",)
        payload = json.dumps(
            list(signatures),
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        bundle = ReviewBundle(
            corrections=CorrectionRegistry(
                documents={
                    _REVIEWED_DOCUMENT_ID: DocumentCorrections(
                        p_doc_id=_REVIEWED_DOCUMENT_ID,
                        sha256=source_sha256,
                        operations=(),
                    )
                }
            ),
            reviewed_documents={
                _REVIEWED_DOCUMENT_ID: ReviewedDocument(
                    p_doc_id=_REVIEWED_DOCUMENT_ID,
                    sha256=source_sha256,
                    lesson_hash=hashlib.sha256(payload).hexdigest(),
                    signatures=signatures,
                )
            },
        )
        try:
            report = _import_reviewed_master(session, review_bundle=bundle)
            failed = _document_report(report)

            assert failed.status == importer.STATUS_FAILED
            assert failed.doc_type == DocType.SEMESTER_GRID_MASTER
            assert "reviewed schedule mismatch" in (failed.error or "")
            assert session.scalar(
                select(func.count()).select_from(ScheduleDocument)
            ) == 0
        finally:
            session.close()

    def test_review_mismatch_rolls_back_manual_replace_and_parser_replacement(self):
        session = make_session(autoflush=False)
        try:
            _import_reviewed_master(session)
            document, _, states = _reviewed_document_and_states(session)
            expected = reviewed_document_output(session, document)
            before = states[0]
            operation = CorrectionOperation(
                id="integration-rejected-replace",
                operation="replace",
                page=1,
                evidence="reviewed PDF page 1",
                expected_before=before,
                after=replace(before, room="MUST-ROLL-BACK"),
            )
            bundle = _review_bundle(document, states, operation)
            session.rollback()

            report = _import_reviewed_master(session, review_bundle=bundle)
            failed = _document_report(report)

            assert failed.status == importer.STATUS_FAILED
            assert "reviewed schedule mismatch" in (failed.error or "")
            assert reviewed_document_output(session, document) == expected
            assert all(
                lesson.room != "MUST-ROLL-BACK"
                for lesson in session.scalars(
                    select(Lesson).where(Lesson.document_id == document.id)
                )
            )
        finally:
            session.close()


def test_import_diff_preserves_duplicate_multiplicity():
    signature = "same reviewed row"

    diff = importer._diff((signature, signature), (signature,))

    assert diff.added == ()
    assert diff.removed == (signature,)


def test_import_diff_details_are_bounded_without_losing_complete_counts():
    signature = "same\nreviewed row"
    diff = importer.DocumentDiff(
        added=(signature,) * 100_000,
        removed=("removed reviewed row",) * 7,
    )

    details = diff.details()
    lines = details.splitlines()
    emitted = sum(
        line.startswith(("+ стало: ", "− было: ")) for line in lines
    )
    summary = next(
        line for line in lines if line.startswith("… пропущено изменений: ")
    )
    omitted = int(summary.rsplit(" ", 1)[-1])

    assert len(lines) <= 42
    assert len(details.encode("utf-8")) <= 8 * 1024
    assert omitted == len(diff.added) + len(diff.removed) - emitted
    assert len(diff.added) == 100_000
    assert len(diff.removed) == 7
    assert not diff.is_empty
    assert importer.DocumentDiff(added=(), removed=()).is_empty


@pytest.mark.parametrize(
    ("separator", "escaped"),
    (
        ("\v", r"\v"),
        ("\f", r"\f"),
        ("\x1c", r"\u001c"),
        ("\x1d", r"\u001d"),
        ("\x1e", r"\u001e"),
        ("\x85", r"\u0085"),
        ("\u2028", r"\u2028"),
        ("\u2029", r"\u2029"),
    ),
)
def test_import_diff_details_escape_every_other_splitlines_separator(
    separator,
    escaped,
):
    assert f"before{separator}after".splitlines() == ["before", "after"]
    signature = f"before{separator}after"
    diff = importer.DocumentDiff(added=(signature,) * 100_000, removed=())

    details = diff.details()
    lines = details.splitlines()
    emitted = sum(line.startswith("+ стало: ") for line in lines)
    summary = next(
        line for line in lines if line.startswith("… пропущено изменений: ")
    )
    omitted = int(summary.rsplit(" ", 1)[-1])

    assert len(lines) <= 42
    assert len(details.encode("utf-8")) <= 8 * 1024
    assert omitted == len(diff.added) - emitted
    assert f"+ стало: before{escaped}after" in lines


def test_import_diff_details_keep_normal_output_unchanged():
    diff = importer.DocumentDiff(added=("new",), removed=("old",))

    assert diff.details() == "− было: old\n+ стало: new"


def test_exam_snapshot_is_complete_stable_and_preserves_duplicate_count():
    session = make_session(autoflush=False)
    try:
        document = ScheduleDocument(
            p_doc_id=90001,
            section="Сессия",
            label="2 курс",
            doc_type=DocType.EXAM_SESSION,
            sha256="a" * 64,
            source_url="https://example.test/90001.pdf",
        )
        group = Group(
            course=2,
            number="2.3",
            program=None,
            level=EducationLevel.BACHELOR,
        )
        session.add_all([document, group])
        session.flush()
        exams = [
            ExamEvent(
                group=group,
                document_id=document.id,
                subject="Финансы",
                teacher="Иванова И.И.",
                consultation_at=datetime(2027, 1, 10, 12, 0),
                exam_at=datetime(2027, 1, 11, 9, 0),
                room="214",
                kind="устный",
            )
            for _ in range(2)
        ]
        session.add_all(exams)
        session.flush()

        before = importer._snapshot(session, document)
        payload = json.loads(before[0].removeprefix("экзамен:"))
        session.delete(exams[1])
        session.flush()
        after = importer._snapshot(session, document)
        diff = importer._diff(before, after)

        assert payload == {
            "document": "90001",
            "group": {
                "course": 2,
                "level": "bachelor",
                "number": "2.3",
                "program": None,
            },
            "subject": "Финансы",
            "teacher": "Иванова И.И.",
            "consultation_at": "2027-01-10T12:00:00",
            "exam_at": "2027-01-11T09:00:00",
            "room": "214",
            "kind": "устный",
        }
        assert before == (before[0], before[0])
        assert diff.added == ()
        assert diff.removed == (before[0],)
    finally:
        session.close()


class TestChangedFile:
    def test_new_sha256_triggers_reparse_with_diff_not_silent_overwrite(self):
        session = make_session()
        # 13984.docx — сессия из 3 экзаменов, самый маленький разобранный файл
        importer.import_all(session, FakeFetcher())
        before = session.scalar(
            select(func.count()).select_from(ExamEvent)
        )

        changed = _mutated_docx(FILES["13984"].read_bytes())
        report = importer.import_all(
            session, FakeFetcher(overrides={"13984": changed})
        )

        doc = next(d for d in report.documents if d.p_doc_id == "13984")
        assert doc.status == importer.STATUS_REIMPORTED
        assert doc.diff is not None
        assert doc.diff.removed or doc.diff.added, "diff «было/стало» пуст"

        stored = session.scalars(
            select(ImportDiff).join(ScheduleDocument).where(
                ScheduleDocument.p_doc_id == 13984
            )
        ).all()
        assert len(stored) == 1, "diff не сохранён для админа"
        assert stored[0].details.strip()
        # переразбор не задваивает экзамены соседних файлов
        assert session.scalar(select(func.count()).select_from(ExamEvent)) <= before + 5
        session.close()

    def test_unchanged_files_are_not_refetched_into_new_rows(self):
        session = make_session()
        importer.import_all(session, FakeFetcher())
        docs = session.scalar(select(func.count()).select_from(ScheduleDocument))
        importer.import_all(session, FakeFetcher())
        assert session.scalar(select(func.count()).select_from(ScheduleDocument)) == docs
        session.close()


class TestVanishedFile:
    def test_missing_link_alerts_admin_and_keeps_data(self, monkeypatch):
        session = make_session()
        importer.import_all(session, FakeFetcher())
        lessons_before = session.scalar(select(func.count()).select_from(Lesson))

        alerts: list[str] = []
        monkeypatch.setattr(importer, "notify_admin", alerts.append)

        # страница без 13469: файл исчез
        html = INDEX_HTML.replace("p_doc_id=13469", "p_doc_id=99999")
        report = importer.import_all(session, FakeFetcher(index_html=html))

        assert "13469" in report.missing
        assert any("13469" in text for text in alerts), "админ не получил сигнал"
        assert session.scalar(select(func.count()).select_from(Lesson)) >= lessons_before
        assert session.scalar(
            select(func.count()).select_from(ScheduleDocument).where(
                ScheduleDocument.p_doc_id == 13469
            )
        ) == 1, "данные исчезнувшего файла удалены — так нельзя"
        session.close()


def _snapshot(session) -> dict:
    return {
        # module_id у пары законно бывает None (страница без модуля идёт весь
        # семестр) — сортировать кортежи с None и int вперемешку нельзя, поэтому
        # -1 вместо None: он сравним и от настоящего id отличается.
        "lessons": sorted(
            (
                lesson.group_id,
                lesson.weekday,
                lesson.pair_number,
                lesson.subject,
                lesson.subgroup,
                lesson.module_id if lesson.module_id is not None else -1,
            )
            for lesson in session.scalars(select(Lesson)).all()
        ),
        "exams": sorted(
            (e.group_id, e.subject, str(e.exam_at)) for e in session.scalars(select(ExamEvent)).all()
        ),
        "unparsed": sorted(
            (c.document_id, c.raw_text, c.reason)
            for c in session.scalars(select(UnparsedCell)).all()
        ),
        "modules": sorted(
            (m.document_id, str(m.date_from), str(m.date_to))
            for m in session.scalars(select(Module)).all()
        ),
    }


def _mutated_docx(content: bytes) -> bytes:
    """Тот же docx с изменённым названием дисциплины — как перезаливка ЮФУ."""
    import io
    import zipfile

    source = io.BytesIO(content)
    target = io.BytesIO()
    with zipfile.ZipFile(source) as src, zipfile.ZipFile(target, "w") as dst:
        for item in src.infolist():
            data = src.read(item.filename)
            if item.filename == "word/document.xml":
                data = data.replace(
                    "Экосистема".encode("utf-8"), "Экоситема".encode("utf-8")
                )
            dst.writestr(item, data)
    return target.getvalue()


class TestScheduleParseFixes:
    """Три системных бага разбора PDF, найденные аудитом сверки БД с файлами.

    Все три — на настоящем 13470.pdf (2 курс бакалавриата, осенний семестр,
    три модуля по страницам). Родной docx-близнец 13469 те же данные разбирает
    иначе, поэтому проверяем именно PDF-путь.
    """

    def _lessons_13470(self, session):
        doc = session.scalar(
            select(ScheduleDocument).where(ScheduleDocument.p_doc_id == 13470)
        )
        return session.scalars(
            select(Lesson).where(Lesson.document_id == doc.id)
        ).all(), doc

    def test_bug1_tuesday_language_block_is_present(self, corpus):
        """БАГ 1. Вторник — языковые блоки по 3 ак. часа ('800- 1025' и т.д.).
        Парсер отвергал их как «время вне сетки» → весь вторник у всех 6 групп
        исчезал. Теперь пары вторника есть, с предметом «Иностранный язык» и
        реальными границами из файла (08:00–10:25)."""
        from datetime import time

        session, _ = corpus
        lessons, _doc = self._lessons_13470(session)

        tuesday = [lesson for lesson in lessons if lesson.weekday == 1]
        assert tuesday, "вторник 13470 снова пуст — блоки не разобраны"

        groups_with_language = {
            lesson.group.number
            for lesson in tuesday
            if "Иностранный язык" in lesson.subject
        }
        assert groups_with_language == {"2.1", "2.2", "2.3", "2.4", "2.5", "2.6"}

        first_block = [lesson for lesson in tuesday if lesson.starts_at == time(8, 0)]
        assert first_block, "блок 08:00 не найден"
        assert all(lesson.ends_at == time(10, 25) for lesson in first_block), (
            "конец блока должен быть реальным (10:25), а не концом первой пары"
        )

    def test_bug2_continuation_pages_inherit_their_module(self, corpus):
        """БАГ 2. Заголовок модуля стоит только на ПЕРВОЙ странице модуля;
        страницы-продолжения (Ср/Чт/Пт) получали module_id=NULL → пары шли
        круглый год и три модуля сваливались в один слот. Теперь у пар Ср/Чт/Пт
        есть окно действия внутри их модуля. Текстовые ограничения «с/до/по»
        вправе сужать окно, но не выходить за границы модуля."""
        session, _ = corpus
        lessons, _doc = self._lessons_13470(session)

        continuation = [lesson for lesson in lessons if lesson.weekday in (2, 3, 4)]
        assert continuation, "Ср/Чт/Пт 13470 пусты — сверять нечего"
        without_window = [
            lesson for lesson in continuation if lesson.valid_from is None
        ]
        assert without_window == [], (
            f"{len(without_window)} пар Ср/Чт/Пт без окна действия — модуль не "
            "перенесён на страницу-продолжение"
        )
        # Продолжение обязано сохранить модуль, а датовая пометка в самой
        # ячейке может только сузить его период.
        assert all(
            lesson.module is not None
            and lesson.module.date_from <= lesson.valid_from <= lesson.valid_to
            and lesson.valid_to <= lesson.module.date_to
            for lesson in continuation
        )
        unconstrained = [
            lesson for lesson in continuation
            if lesson.date_constraint_raw is None
        ]
        assert unconstrained, "нет пар без датовых ограничений для проверки"
        assert all(
            lesson.valid_from == lesson.module.date_from
            and lesson.valid_to == lesson.module.date_to
            for lesson in unconstrained
        )

    def test_bug2_three_modules_do_not_collapse_into_one_slot(self, corpus):
        """Следствие бага 2: без модуля три параллельных модуля Ср/Чт/Пт лезли
        в один (день, пара) и половина пар уходила в очередь как «слот занят».
        13470 объявляет три разных модуля — и все три несут пары."""
        session, _ = corpus
        doc = session.scalar(
            select(ScheduleDocument).where(ScheduleDocument.p_doc_id == 13470)
        )
        modules = session.scalars(
            select(Module).where(Module.document_id == doc.id)
        ).all()
        assert len(modules) == 3, f"ожидали три модуля, получили {len(modules)}"

        taken = session.scalars(
            select(UnparsedCell).where(
                UnparsedCell.document_id == doc.id,
                UnparsedCell.reason == importer.REASON_SLOT_TAKEN,
            )
        ).all()
        assert taken == [], (
            f"{len(taken)} ячеек ушли в очередь как «слот занят» — модули всё ещё "
            "сливаются в один бакет"
        )

    def test_bug3_no_phantom_subgroup_from_column_bleed(self, corpus):
        """БАГ 3. 13470 СРЕДА пара 2: узкие семинары чуть заходили на соседнюю
        колонку, и группа 2.3 получала свой предмет (Монетарная) ПЛЮС предмет
        соседа 2.2 (Безопасность жизнедеятельности) как выдуманную подгруппу.
        Теперь у 2.3 ровно одна пара — Монетарная, целиком, без фантома."""
        session, _ = corpus
        lessons, _doc = self._lessons_13470(session)

        g23_wed2 = [
            lesson
            for lesson in lessons
            if lesson.group.number == "2.3" and lesson.weekday == 2 and lesson.pair_number == 2
        ]
        subjects = {lesson.subject for lesson in g23_wed2}
        assert not any("Безопасность" in s for s in subjects), (
            f"у 2.3 остался фантом соседа: {sorted(subjects)}"
        )
        assert any("Монетарная" in s for s in subjects), sorted(subjects)
        assert all(lesson.subgroup == 0 for lesson in g23_wed2), (
            "занятие всей группы, а не выдуманная подгруппа"
        )
