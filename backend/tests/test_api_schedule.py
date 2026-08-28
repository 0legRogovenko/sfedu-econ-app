from datetime import date, time

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
