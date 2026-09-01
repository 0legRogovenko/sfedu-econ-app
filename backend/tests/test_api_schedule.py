import os
from datetime import date, time
from pathlib import Path
from types import MappingProxyType

import pytest
from sqlalchemy import select

from scripts import export_reviewed_schedule as exporter

from src.models import (
    DocType,
    EducationLevel,
    Group,
    Lesson,
    Module,
    ScheduleDocument,
    Teacher,
    WeekCalendar,
    WeekType,
)
from src.schedule.importer import import_all
from src.schedule.reviewed_schedule import CorrectionRegistry


DRAFT_SNAPSHOT_DIR = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "schedule_snapshot"
    / "2026-08-30"
)


def _import_draft_document(db_session, p_doc_id):
    snapshot_dir = Path(
        os.environ.get("SFEDU_TEST_SNAPSHOT_DIR", DRAFT_SNAPSHOT_DIR)
    )
    loaded = exporter._load_export_snapshot(
        snapshot_dir.resolve(),
        allow_existing_reviewed=False,
    )
    assert loaded.corrections is not None
    source = next(
        item for item in loaded.snapshot.documents if item.link.p_doc_id == p_doc_id
    )
    corrections = CorrectionRegistry(
        documents=MappingProxyType(
            {p_doc_id: loaded.corrections.documents[p_doc_id]}
        )
    )
    report = import_all(
        db_session,
        exporter._AuthenticatedSnapshotFetcher(loaded.snapshot),
        links=[source.link],
        atomic=True,
        review_bundle=exporter._CorrectionApplyingBundle(corrections),
    )
    db_session.flush()

    assert report.failed == 0
    groups = db_session.scalars(
        select(Group).where(
            Group.level == EducationLevel.MASTER,
        )
    ).all()
    return {group.program: group.id for group in groups}


@pytest.fixture()
def imported_14159_draft(db_session):
    return _import_draft_document(db_session, "14159")


@pytest.fixture()
def imported_14160_draft(db_session):
    return _import_draft_document(db_session, "14160")


def _master_schedule(client, imported_draft, program):
    response = client.get(
        f"/api/schedule?group_id={imported_draft[program]}"
    )
    assert response.status_code == 200
    return response.json()


def _make_document(db_session, p_doc_id=13469):
    document = ScheduleDocument(
        p_doc_id=p_doc_id,
        section="Осенний семестр",
        label="2 курс",
        doc_type=DocType.SEMESTER_GRID_BACHELOR,
        sha256="a" * 64,
        source_url="https://sfedu.ru/www/sched_files.f_download?p_doc_id=13469",
    )
    db_session.add(document)
    db_session.flush()
    return document


def _seed_schedule(db_session):
    group = Group(course=2, number="2.1")
    other = Group(course=2, number="2.2")
    teacher = Teacher(full_name="Иванова Елена Петровна")
    db_session.add_all([group, other, teacher])
    db_session.flush()

    db_session.add_all(
        [
            Lesson(
                group_id=group.id,
                weekday=1,
                pair_number=2,
                starts_at=time(10, 50),
                ends_at=time(12, 25),
                subject="Эконометрика",
                week_type=None,
                subgroup=0,
            ),
            Lesson(
                group_id=group.id,
                weekday=1,
                pair_number=1,
                starts_at=time(9, 0),
                ends_at=time(10, 35),
                subject="Макроэкономика",
                teacher_id=teacher.id,
                room="220",
                week_type=WeekType.UPPER,
                subgroup=0,
            ),
            Lesson(
                group_id=other.id,
                weekday=2,
                pair_number=1,
                starts_at=time(9, 0),
                ends_at=time(10, 35),
                subject="Философия",
                teacher_id=teacher.id,
                week_type=None,
                subgroup=0,
            ),
        ]
    )
    db_session.flush()
    return group, other, teacher


def test_schedule_by_group_sorted(client, db_session):
    group, _, _ = _seed_schedule(db_session)

    response = client.get(f"/api/schedule?group_id={group.id}")

    assert response.status_code == 200
    data = response.json()
    lessons = data["lessons"]
    assert [item["subject"] for item in lessons] == ["Макроэкономика", "Эконометрика"]
    first = lessons[0]
    assert first["week_type"] == "upper"
    assert lessons[1]["week_type"] is None  # каждую неделю
    assert first["starts_at"] == "09:00:00"
    assert first["teacher"] == {
        "id": first["teacher"]["id"],
        "full_name": "Иванова Елена Петровна",
    }
    assert lessons[1]["teacher"] is None


def test_schedule_without_documents_has_empty_context(client, db_session):
    # Ручные пары / демо-сид: документов нет — модули и календарь пустые,
    # клиент трактует это как «пара действует весь семестр, каждую неделю»
    group, _, _ = _seed_schedule(db_session)

    data = client.get(f"/api/schedule?group_id={group.id}").json()

    assert data["modules"] == []
    assert data["week_calendar"] == []


def test_schedule_lesson_context_fields(client, db_session):
    # Клиент НЕ вычисляет неделю формулой (формула была перёвернута) —
    # сервер отдаёт календарь недель и модули как данные
    group = Group(course=2, number="2.1")
    db_session.add(group)
    db_session.flush()
    document = _make_document(db_session)
    module1 = Module(
        document_id=document.id,
        name="1 модуль",
        date_from=date(2025, 9, 1),
        date_to=date(2025, 10, 26),
    )
    module2 = Module(
        document_id=document.id,
        name="2 модуль",
        date_from=date(2025, 10, 27),
        date_to=date(2025, 12, 31),
    )
    db_session.add_all([module1, module2])
    db_session.flush()
    db_session.add_all(
        [
            WeekCalendar(
                document_id=document.id,
                date_from=date(2025, 9, 1),
                date_to=date(2025, 9, 7),
                week_type=WeekType.UPPER,
            ),
            WeekCalendar(
                document_id=document.id,
                date_from=date(2025, 9, 8),
                date_to=date(2025, 9, 14),
                week_type=WeekType.LOWER,
            ),
            Lesson(
                group_id=group.id,
                document_id=document.id,
                module_id=module1.id,
                weekday=0,
                pair_number=1,
                starts_at=time(8, 0),
                ends_at=time(9, 35),
                subject="История России",
                week_type=None,
                subgroup=0,
                valid_from=date(2025, 9, 1),
                valid_to=date(2025, 10, 26),
                specific_dates=["2025-09-08", "2025-09-22"],
            ),
        ]
    )
    db_session.flush()

    data = client.get(f"/api/schedule?group_id={group.id}").json()

    lesson = data["lessons"][0]
    assert lesson["module_id"] == module1.id
    assert lesson["valid_from"] == "2025-09-01"
    assert lesson["valid_to"] == "2025-10-26"
    assert lesson["specific_dates"] == ["2025-09-08", "2025-09-22"]

    # ВСЕ модули документа, а не только те, где у группы есть пары:
    # клиенту нужны границы, чтобы сказать «в этом модуле занятий нет»
    assert data["modules"] == [
        {
            "id": module1.id,
            "name": "1 модуль",
            "date_from": "2025-09-01",
            "date_to": "2025-10-26",
        },
        {
            "id": module2.id,
            "name": "2 модуль",
            "date_from": "2025-10-27",
            "date_to": "2025-12-31",
        },
    ]
    assert data["week_calendar"] == [
        {"date_from": "2025-09-01", "date_to": "2025-09-07", "week_type": "upper"},
        {"date_from": "2025-09-08", "date_to": "2025-09-14", "week_type": "lower"},
    ]


def test_schedule_context_only_from_own_documents(client, db_session):
    # Модули чужого документа (другой курс/семестр) в ответ не утекают
    group = Group(course=2, number="2.1")
    db_session.add(group)
    db_session.flush()
    own = _make_document(db_session, p_doc_id=13469)
    foreign = _make_document(db_session, p_doc_id=13470)
    db_session.add_all(
        [
            Module(
                document_id=foreign.id,
                name="чужой модуль",
                date_from=date(2025, 9, 1),
                date_to=date(2025, 12, 31),
            ),
            WeekCalendar(
                document_id=foreign.id,
                date_from=date(2025, 9, 1),
                date_to=date(2025, 9, 7),
                week_type=WeekType.UPPER,
            ),
            Lesson(
                group_id=group.id,
                document_id=own.id,
                weekday=0,
                pair_number=1,
                starts_at=time(8, 0),
                ends_at=time(9, 35),
                subject="Математика",
                subgroup=0,
            ),
        ]
    )
    db_session.flush()

    data = client.get(f"/api/schedule?group_id={group.id}").json()

    assert data["modules"] == []
    assert data["week_calendar"] == []


def test_schedule_master_group(client, db_session):
    # У магистров номера группы НЕТ — идентифицирует программа
    group = Group(
        course=1,
        number=None,
        level=EducationLevel.MASTER,
        program="Бизнес-аналитика и большие данные",
    )
    db_session.add(group)
    db_session.flush()
    db_session.add(
        Lesson(
            group_id=group.id,
            weekday=4,
            pair_number=6,
            starts_at=time(17, 35),
            ends_at=time(19, 10),
            subject="Эконометрика (продвинутый уровень)",
            subgroup=0,
        )
    )
    db_session.flush()

    response = client.get(f"/api/schedule?group_id={group.id}")

    assert response.status_code == 200
    lessons = response.json()["lessons"]
    assert [item["subject"] for item in lessons] == [
        "Эконометрика (продвинутый уровень)"
    ]


def test_reviewed_master_elective_choices_keep_exact_subject_teacher_and_room(
    client,
    imported_14159_draft,
):
    data = _master_schedule(
        client,
        imported_14159_draft,
        "Экономика, управление и право",
    )
    choices = [
        lesson
        for lesson in data["lessons"]
        if lesson["weekday"] == 1 and lesson["pair_number"] == 6
    ]

    assert {
        (
            lesson["subject"],
            lesson["teacher"]["full_name"] if lesson["teacher"] else None,
            lesson["room"],
        )
        for lesson in choices
    } == {
        ("По выбору: Договорное право", "Муравьева Е.В.", None),
        (
            "Система и основные институты гражданского права",
            "Федорова И.В.",
            None,
        ),
    }


def test_reviewed_master_blank_room_labels_do_not_pollute_teacher_names(
    client,
    imported_14159_draft,
):
    programs = (
        "Экономика, управление и право",
        "Экономическая аналитика",
        "Учетные технологии и аудит",
        "Международная экономика и бизнес",
        "Корпоративные финансы",
    )
    polluted = []
    for program in programs:
        data = _master_schedule(client, imported_14159_draft, program)
        polluted.extend(
            lesson["teacher"]["full_name"]
            for lesson in data["lessons"]
            if lesson["teacher"]
            and lesson["teacher"]["full_name"].endswith(" ауд.")
        )

    assert polluted == []


def test_reviewed_master_online_facultative_has_no_invented_subgroup(
    client,
    imported_14159_draft,
):
    data = _master_schedule(
        client,
        imported_14159_draft,
        "Учетные технологии и аудит",
    )
    lessons = [
        lesson
        for lesson in data["lessons"]
        if lesson["subject"]
        == "Факультатив: Иностранный язык для профессиональной коммуникации"
        and lesson["weekday"] == 5
        and lesson["pair_number"] == 1
    ]

    assert [(lesson["room"], lesson["subgroup"]) for lesson in lessons] == [
        ("Онлайн", 0)
    ]


def test_reviewed_corporate_finance_lessons_use_rendered_module_window(
    client,
    imported_14159_draft,
):
    data = _master_schedule(
        client,
        imported_14159_draft,
        "Корпоративные финансы",
    )
    module = next(
        item
        for item in data["modules"]
        if item["date_from"] == "2026-09-01"
        and item["date_to"] == "2026-11-01"
    )
    lessons = data["lessons"]

    assert len(lessons) == 12
    assert {lesson["module_id"] for lesson in lessons} == {module["id"]}
    assert {lesson["valid_from"] for lesson in lessons} == {"2026-09-01"}
    assert [
        lesson["subject"]
        for lesson in lessons
        if lesson["valid_to"] == "2026-10-01"
    ] == ["Методы и инструменты исследований в профессиональной деятельности"]
    assert sum(lesson["valid_to"] == "2026-11-01" for lesson in lessons) == 11


_MULTI_TEACHER_14159 = (
    (
        "Экономика, управление и право",
        4,
        6,
        "Институциональная экономика и право",
        "lecture",
        "Вольчик В.В., Ширяев И.М.",
        "118",
    ),
    (
        "Экономическая аналитика",
        1,
        6,
        "Анализ данных в R и Python",
        None,
        "Маслюкова Е.В., Головачева М.М.",
        "325",
    ),
    (
        "Экономическая аналитика",
        1,
        7,
        "Анализ данных в R и Python",
        None,
        "Маслюкова Е.В., Головачева М.М.",
        "325",
    ),
    (
        "Экономическая аналитика",
        4,
        6,
        "Институциональная экономика и право",
        "lecture",
        "Вольчик В.В., Ширяев И.М.",
        "118",
    ),
    (
        "Экономическая аналитика",
        4,
        7,
        "Институциональная экономика и право",
        "seminar",
        "Вольчик В.В., Ширяев И.М.",
        "118",
    ),
    (
        "Учетные технологии и аудит",
        0,
        5,
        "Финансовый учет (продвинутый уровень)",
        "lecture",
        "Фролова И.В., Овчаренко О.В.",
        "324",
    ),
    (
        "Учетные технологии и аудит",
        0,
        6,
        "Финансовый учет (продвинутый уровень)",
        "seminar",
        "Фролова И.В., Овчаренко О.В.",
        "324",
    ),
    (
        "Учетные технологии и аудит",
        0,
        7,
        "Финансовый учет (продвинутый уровень)",
        "seminar",
        "Фролова И.В., Овчаренко О.В.",
        "324",
    ),
    (
        "Учетные технологии и аудит",
        4,
        5,
        "Аудит (продвинутый уровень)",
        "lecture",
        "Фролова И.В., Овчаренко О.В.",
        "325",
    ),
    (
        "Учетные технологии и аудит",
        4,
        6,
        "Аудит (продвинутый уровень)",
        "seminar",
        "Фролова И.В., Овчаренко О.В.",
        "325",
    ),
    (
        "Учетные технологии и аудит",
        4,
        7,
        "Аудит (продвинутый уровень)",
        "seminar",
        "Фролова И.В., Овчаренко О.В.",
        "325",
    ),
    (
        "Корпоративные финансы",
        1,
        6,
        "Международные стандарты финансовой отчетности (продвинутый уровень)",
        "lecture",
        "Полховская Т.Ю., Палий В.П.",
        "219",
    ),
    (
        "Корпоративные финансы",
        1,
        7,
        "Международные стандарты финансовой отчетности (продвинутый уровень)",
        "seminar",
        "Полховская Т.Ю., Палий В.П.",
        None,
    ),
    (
        "Экономика труда и управление персоналом",
        2,
        7,
        "Управление персоналом: продвинутый уровень",
        "seminar",
        "Костенко Е.П., Несоленая О.В., Постникова В.П.",
        "311",
    ),
    (
        "International Economics and Analytics (Международная экономика и аналитика)",
        0,
        6,
        "Tools of Research in Professional Activity (Методы и инструменты исследований в профессиональной деятельности)",
        "lecture",
        "Цыганков С.С., Архипова К.Э.",
        "402",
    ),
    (
        "International Economics and Analytics (Международная экономика и аналитика)",
        0,
        7,
        "Tools of Research in Professional Activity (Методы и инструменты исследований в профессиональной деятельности)",
        "seminar",
        "Цыганков С.С., Архипова К.Э.",
        "402",
    ),
    (
        "Economics and Public Procurement (Экономика и государственные закупки)",
        0,
        6,
        "Tools of Research in Professional Activity (Методы и инструменты исследований в профессиональной деятельности)",
        "lecture",
        "Цыганков С.С., Архипова К.Э.",
        "402",
    ),
    (
        "Economics and Public Procurement (Экономика и государственные закупки)",
        0,
        7,
        "Tools of Research in Professional Activity (Методы и инструменты исследований в профессиональной деятельности)",
        "seminar",
        "Цыганков С.С., Архипова К.Э.",
        "402",
    ),
    (
        "Economics and Public Procurement (Экономика и государственные закупки)",
        3,
        7,
        "Law and Economics (Экономический анализ права)",
        "seminar",
        "Цыганков С.С., Маскаев А.И.",
        "402",
    ),
    (
        "Economics and Public Procurement (Экономика и государственные закупки)",
        4,
        6,
        "Law and Economics (Экономический анализ права)",
        "lecture",
        "Цыганков С.С., Маскаев А.И.",
        "402",
    ),
    (
        "Economics and Public Procurement (Экономика и государственные закупки)",
        4,
        7,
        "Law and Economics (Экономический анализ права)",
        "seminar",
        "Цыганков С.С., Маскаев А.И.",
        "402",
    ),
)


_MULTI_TEACHER_14160 = (
    (
        "Экономика, управление и право",
        0,
        6,
        "По выбору: Экономическая политика и государственное и муниципальное управление",
        "lecture",
        "Кот В.В., Стрельченко Е.А.",
        "219",
    ),
    (
        "Экономика, управление и право",
        0,
        7,
        "Экономическая политика и государственное и муниципальное управление",
        "seminar",
        "Кот В.В., Стрельченко Е.А.",
        "219",
    ),
    (
        "Экономическая аналитика",
        0,
        6,
        "Экономическая политика и государственное и муниципальное управление",
        "lecture",
        "Кот В.В., Стрельченко Е.А.",
        "219",
    ),
    (
        "Экономическая аналитика",
        0,
        7,
        "Экономическая политика и государственное и муниципальное управление",
        "seminar",
        "Кот В.В., Стрельченко Е.А.",
        "219",
    ),
    (
        "Экономика труда и управление персоналом",
        0,
        6,
        "Управление талантами",
        None,
        "Маличенко И.П., Постникова В.П., Осипова И.В.",
        "306",
    ),
    (
        "Экономика труда и управление персоналом",
        0,
        7,
        "Управление талантами",
        "seminar",
        "Маличенко И.П., Постникова В.П., Осипова И.В.",
        "306",
    ),
    (
        "Корпоративные финансы",
        1,
        5,
        "Внутрикорпоративный финансовый контроль и комплаенс",
        "lecture",
        "Давыденко И.Г., Войтенко М.С.",
        None,
    ),
    (
        "Корпоративные финансы",
        1,
        6,
        "Внутрикорпоративный финансовый контроль и комплаенс",
        "seminar",
        "Давыденко И.Г., Войтенко М.С.",
        None,
    ),
)


def _assert_source_multi_teacher_lessons(
    client,
    db_session,
    imported_draft,
    expected,
):
    expected_api = [
        (program, weekday, pair_number, subject, teacher, room)
        for (
            program,
            weekday,
            pair_number,
            subject,
            _lesson_kind,
            teacher,
            room,
        ) in expected
    ]
    expected_db = list(expected)
    actual_api = []
    actual_db = []

    for program in dict.fromkeys(item[0] for item in expected):
        program_expected = [item for item in expected if item[0] == program]
        selectors = {(item[1], item[2], item[3]) for item in program_expected}
        data = _master_schedule(client, imported_draft, program)
        api_lessons = [
            lesson
            for lesson in data["lessons"]
            if (lesson["weekday"], lesson["pair_number"], lesson["subject"])
            in selectors
        ]
        actual_api.extend(
            (
                program,
                lesson["weekday"],
                lesson["pair_number"],
                lesson["subject"],
                lesson["teacher"]["full_name"],
                lesson["room"],
            )
            for lesson in api_lessons
        )

        rows = db_session.scalars(
            select(Lesson).where(Lesson.group_id == imported_draft[program])
        ).all()
        actual_db.extend(
            (
                program,
                lesson.weekday,
                lesson.pair_number,
                lesson.subject,
                lesson.lesson_kind.value if lesson.lesson_kind else None,
                lesson.teacher.full_name,
                lesson.room,
            )
            for lesson in rows
            if (lesson.weekday, lesson.pair_number, lesson.subject) in selectors
        )

    sort_key = lambda item: repr(item)  # noqa: E731 - shared exact tuple ordering
    assert sorted(actual_api, key=sort_key) == sorted(expected_api, key=sort_key)
    assert sorted(actual_db, key=sort_key) == sorted(expected_db, key=sort_key)


def test_reviewed_first_year_master_preserves_all_source_multi_teachers(
    client,
    db_session,
    imported_14159_draft,
):
    assert len(_MULTI_TEACHER_14159) == 21
    _assert_source_multi_teacher_lessons(
        client,
        db_session,
        imported_14159_draft,
        _MULTI_TEACHER_14159,
    )


def test_reviewed_second_year_master_preserves_all_source_multi_teachers(
    client,
    db_session,
    imported_14160_draft,
):
    assert len(_MULTI_TEACHER_14160) == 8
    _assert_source_multi_teacher_lessons(
        client,
        db_session,
        imported_14160_draft,
        _MULTI_TEACHER_14160,
    )


def test_reviewed_second_year_master_keeps_full_multi_teacher_strings(
    client,
    db_session,
    imported_14160_draft,
):
    expected_policy_teacher = "Кот В.В., Стрельченко Е.А."
    policy_teachers = []
    for program in ("Экономика, управление и право", "Экономическая аналитика"):
        data = _master_schedule(client, imported_14160_draft, program)
        policy_teachers.extend(
            lesson["teacher"]["full_name"]
            for lesson in data["lessons"]
            if "Экономическая политика и государственное и муниципальное управление"
            in lesson["subject"]
        )

    labor_program = "Экономика труда и управление персоналом"
    labor = _master_schedule(client, imported_14160_draft, labor_program)
    talent = [
        lesson
        for lesson in labor["lessons"]
        if lesson["subject"] == "Управление талантами"
    ]

    assert policy_teachers == [expected_policy_teacher] * 4
    assert [lesson["teacher"]["full_name"] for lesson in talent] == [
        "Маличенко И.П., Постникова В.П., Осипова И.В.",
        "Маличенко И.П., Постникова В.П., Осипова И.В.",
    ]
    talent_rows = db_session.scalars(
        select(Lesson).where(
            Lesson.group_id == imported_14160_draft[labor_program],
            Lesson.subject == "Управление талантами",
        ).order_by(Lesson.pair_number)
    ).all()
    assert [
        (lesson.pair_number, lesson.lesson_kind.value if lesson.lesson_kind else None)
        for lesson in talent_rows
    ] == [(6, None), (7, "seminar")]


def test_reviewed_corporate_control_keeps_full_multi_teacher_string(
    client,
    db_session,
    imported_14160_draft,
):
    program = "Корпоративные финансы"
    subject = "Внутрикорпоративный финансовый контроль и комплаенс"
    data = _master_schedule(client, imported_14160_draft, program)
    lessons = [lesson for lesson in data["lessons"] if lesson["subject"] == subject]

    assert [
        (
            lesson["weekday"],
            lesson["pair_number"],
            lesson["teacher"]["full_name"],
        )
        for lesson in lessons
    ] == [
        (1, 5, "Давыденко И.Г., Войтенко М.С."),
        (1, 6, "Давыденко И.Г., Войтенко М.С."),
    ]
    rows = db_session.scalars(
        select(Lesson).where(
            Lesson.group_id == imported_14160_draft[program],
            Lesson.subject == subject,
        ).order_by(Lesson.pair_number)
    ).all()
    assert [
        (
            lesson.pair_number,
            lesson.lesson_kind.value,
            lesson.teacher.full_name,
        )
        for lesson in rows
    ] == [
        (5, "lecture", "Давыденко И.Г., Войтенко М.С."),
        (6, "seminar", "Давыденко И.Г., Войтенко М.С."),
    ]


def test_reviewed_data_science_markers_become_week_types_not_subject_text(
    client,
    imported_14160_draft,
):
    data = _master_schedule(
        client,
        imported_14160_draft,
        "Экономическая аналитика",
    )
    lessons = [
        lesson
        for lesson in data["lessons"]
        if "Инструменты Data Science" in lesson["subject"]
    ]

    assert {
        (
            lesson["pair_number"],
            lesson["starts_at"],
            lesson["ends_at"],
            lesson["subject"],
            lesson["week_type"],
            lesson["teacher"]["full_name"],
            lesson["room"],
            lesson["valid_from"],
            lesson["valid_to"],
        )
        for lesson in lessons
    } == {
        (
            6,
            "17:35:00",
            "19:10:00",
            "Инструменты Data Science",
            "upper",
            "Головачева М.М.",
            "324",
            "2026-10-15",
            "2026-11-01",
        ),
        (
            6,
            "17:35:00",
            "20:00:00",
            "Инструменты Data Science",
            "lower",
            "Маслюкова Е.В.",
            "324",
            "2026-10-08",
            "2026-11-01",
        ),
        (
            7,
            "19:15:00",
            "20:50:00",
            "Инструменты Data Science",
            "upper",
            "Головачева М.М.",
            "324",
            "2026-10-15",
            "2026-11-01",
        ),
    }


def test_reviewed_second_year_master_muam_headings_are_not_subjects(
    client,
    db_session,
    imported_14160_draft,
):
    targets = (
        ("Экономическая аналитика", 5, 1, "Теория игр и стратегии бизнеса"),
        (
            "Экономика труда и управление персоналом",
            2,
            6,
            "Имиджелогия",
        ),
        ("Корпоративные финансы", 4, 6, "Финансовый риск-менеджмент"),
    )
    for program, weekday, pair_number, subject in targets:
        data = _master_schedule(client, imported_14160_draft, program)
        matching = [
            lesson
            for lesson in data["lessons"]
            if lesson["weekday"] == weekday
            and lesson["pair_number"] == pair_number
        ]
        assert subject in {lesson["subject"] for lesson in matching}
        assert all(not lesson["subject"].startswith("МУАМ ") for lesson in matching)

    analytics_group = imported_14160_draft["Экономическая аналитика"]
    game_theory = db_session.scalars(
        select(Lesson).where(
            Lesson.group_id == analytics_group,
            Lesson.weekday == 5,
            Lesson.subject == "Теория игр и стратегии бизнеса",
        ).order_by(Lesson.pair_number)
    ).all()
    assert [
        (lesson.pair_number, lesson.lesson_kind)
        for lesson in game_theory
    ] == [(1, None), (2, None)]


def test_reviewed_second_year_master_blank_room_labels_do_not_pollute_teachers(
    client,
    db_session,
    imported_14160_draft,
):
    labor_program = "Экономика труда и управление персоналом"
    labor = _master_schedule(client, imported_14160_draft, labor_program)
    personnel = [
        lesson
        for lesson in labor["lessons"]
        if lesson["subject"] == "Персонал-технологии"
    ]
    finance = _master_schedule(
        client,
        imported_14160_draft,
        "Корпоративные финансы",
    )
    risk = [
        lesson
        for lesson in finance["lessons"]
        if "Финансовый риск-менеджмент" in lesson["subject"]
    ]

    assert {
        (lesson["teacher"]["full_name"], lesson["room"])
        for lesson in personnel
    } == {("Щетинина Д.П.", None)}
    assert {
        (lesson["teacher"]["full_name"], lesson["room"])
        for lesson in risk
    } == {("Некрасова И.В.", None)}
    personnel_rows = db_session.scalars(
        select(Lesson).where(
            Lesson.group_id == imported_14160_draft[labor_program],
            Lesson.subject == "Персонал-технологии",
        ).order_by(Lesson.pair_number)
    ).all()
    assert [
        (lesson.pair_number, lesson.lesson_kind.value if lesson.lesson_kind else None)
        for lesson in personnel_rows
    ] == [(6, None), (7, "seminar")]


def test_reviewed_law_program_has_four_exact_saturday_lessons(
    client,
    db_session,
    imported_14160_draft,
):
    program = "Экономика, управление и право"
    data = _master_schedule(client, imported_14160_draft, program)
    saturday = [lesson for lesson in data["lessons"] if lesson["weekday"] == 5]

    assert {
        (
            lesson["pair_number"],
            lesson["starts_at"],
            lesson["ends_at"],
            lesson["subject"],
            lesson["teacher"]["full_name"],
            lesson["room"],
            lesson["subgroup"],
        )
        for lesson in saturday
    } == {
        (
            1,
            "08:00:00",
            "09:35:00",
            "Теория игр и стратегии бизнеса",
            "Алехин В.В.",
            None,
            0,
        ),
        (
            1,
            "08:00:00",
            "09:35:00",
            "Права на результаты интеллектуальной деятельности и их защита",
            "Юхнова Ю.И.",
            None,
            0,
        ),
        (
            2,
            "09:50:00",
            "11:25:00",
            "Теория игр и стратегии бизнеса",
            "Алехин В.В.",
            None,
            0,
        ),
        (
            2,
            "09:50:00",
            "11:25:00",
            "Права на результаты интеллектуальной деятельности и их защита",
            "Юхнова Ю.И.",
            None,
            0,
        ),
    }
    saturday_rows = db_session.scalars(
        select(Lesson).where(
            Lesson.group_id == imported_14160_draft[program],
            Lesson.weekday == 5,
        )
    ).all()
    assert {
        (lesson.pair_number, lesson.subject, lesson.lesson_kind.value)
        for lesson in saturday_rows
    } == {
        (1, "Теория игр и стратегии бизнеса", "lecture"),
        (
            1,
            "Права на результаты интеллектуальной деятельности и их защита",
            "lecture",
        ),
        (2, "Теория игр и стратегии бизнеса", "seminar"),
        (
            2,
            "Права на результаты интеллектуальной деятельности и их защита",
            "seminar",
        ),
    }


def test_schedule_by_teacher_spans_groups(client, db_session):
    _, _, teacher = _seed_schedule(db_session)

    response = client.get(f"/api/schedule?teacher_id={teacher.id}")

    assert response.status_code == 200
    assert len(response.json()["lessons"]) == 2


def test_schedule_requires_exactly_one_param(client):
    assert client.get("/api/schedule").status_code == 422
    assert client.get("/api/schedule?group_id=1&teacher_id=1").status_code == 422


def test_schedule_unknown_group_404(client):
    response = client.get("/api/schedule?group_id=99999")
    assert response.status_code == 404


def test_schedule_unknown_teacher_404(client):
    response = client.get("/api/schedule?teacher_id=99999")
    assert response.status_code == 404


def test_schedule_etag_304(client, db_session):
    group, _, _ = _seed_schedule(db_session)

    first = client.get(f"/api/schedule?group_id={group.id}")
    second = client.get(
        f"/api/schedule?group_id={group.id}",
        headers={"If-None-Match": first.headers["etag"]},
    )
    assert second.status_code == 304
