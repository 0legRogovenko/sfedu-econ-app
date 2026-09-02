from datetime import date, datetime, time

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from src.models import (
    DocType,
    EducationLevel,
    ExamEvent,
    Group,
    Lesson,
    LessonKind,
    Module,
    News,
    NewsSource,
    ScheduleDocument,
    UnparsedCell,
    WeekCalendar,
    WeekType,
)


def make_lesson(group_id: int, **overrides):
    data = dict(
        group_id=group_id,
        weekday=1,
        pair_number=1,
        starts_at=time(9, 0),
        ends_at=time(10, 35),
        subject="Макроэкономика",
        week_type=None,  # NULL = каждую неделю — основной случай в файлах ЮФУ
        subgroup=0,
    )
    data.update(overrides)
    return Lesson(**data)


def make_news(**overrides):
    data = dict(
        title="Тест",
        body="Текст",
        source=NewsSource.SFEDU,
        url="https://sfedu.ru/news/1",
        published_at=datetime(2026, 7, 13, 12, 0),
    )
    data.update(overrides)
    return News(**data)


def _make_group(db_session) -> int:
    group = Group(course=2, number="2.1")
    db_session.add(group)
    db_session.flush()
    return group.id


def _make_document(db_session, p_doc_id: int = 13469) -> int:
    doc = ScheduleDocument(
        p_doc_id=p_doc_id,
        section="Осенний семестр",
        label="1 курс",
        doc_type=DocType.SEMESTER_GRID_BACHELOR,
        sha256="a" * 64,
        source_url=f"https://sfedu.ru/www/sched_files.f_download?p_doc_id={p_doc_id}",
    )
    db_session.add(doc)
    db_session.flush()
    return doc.id


def test_duplicate_lesson_slot_rejected(db_session):
    gid = _make_group(db_session)
    db_session.add(make_lesson(gid))
    db_session.flush()

    db_session.add(make_lesson(gid))  # тот же слот и тот же предмет — дубль
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_parallel_lessons_in_one_slot_allowed(db_session):
    """Два занятия в одном слоте — не дубль, а параллель: 13472 p3 кладёт в
    ОДНУ ячейку 'Иностранный язык (с) Онлайн' и 'Русский язык для иностранных
    студентов (с) …'. Ключ без предмета стёр бы второе молча."""
    gid = _make_group(db_session)
    db_session.add(make_lesson(gid, subject="Иностранный язык"))
    db_session.add(make_lesson(gid, subject="Русский язык для иностранных студентов"))
    db_session.flush()  # не должно упасть


def test_same_slot_different_date_constraint_allowed(db_session):
    """13469: 'До 17.12 История менеджмента (л) …' и '24.12 Основы … (с)' —
    одна ячейка, один слот, разные даты. Это две пары, а не одна."""
    gid = _make_group(db_session)
    db_session.add(
        make_lesson(gid, subject="История менеджмента", date_constraint_raw="До 17.12")
    )
    db_session.add(
        make_lesson(gid, subject="История менеджмента", date_constraint_raw="24.12")
    )
    db_session.flush()  # не должно упасть


def test_same_slot_different_document_allowed(db_session):
    """Осень и весна одной группы — разные файлы с одинаковыми (день, пара).
    Без document_id в ключе импорт весны падал на уникальности осени."""
    gid = _make_group(db_session)
    autumn = _make_document(db_session, p_doc_id=13469)
    spring = _make_document(db_session, p_doc_id=13820)
    db_session.add(make_lesson(gid, document_id=autumn))
    db_session.add(make_lesson(gid, document_id=spring))
    db_session.flush()  # не должно упасть


def test_same_slot_different_week_type_allowed(db_session):
    gid = _make_group(db_session)
    db_session.add(make_lesson(gid, week_type=WeekType.UPPER))
    db_session.add(make_lesson(gid, week_type=WeekType.LOWER))
    db_session.flush()  # не должно упасть


def test_same_slot_different_subgroup_allowed(db_session):
    gid = _make_group(db_session)
    db_session.add(make_lesson(gid, subgroup=1))
    db_session.add(make_lesson(gid, subgroup=2))
    db_session.flush()  # не должно упасть


def test_duplicate_news_url_rejected(db_session):
    db_session.add(make_news())
    db_session.flush()

    db_session.add(make_news(title="Другой заголовок"))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_duplicate_group_rejected(db_session):
    db_session.add(Group(course=2, number="2.1"))
    db_session.flush()

    db_session.add(Group(course=2, number="2.1"))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_duplicate_kb_slug_rejected(db_session):
    from src.models import KbArticle

    db_session.add(KbArticle(slug="spravka", title="Справка", body_md="…"))
    db_session.flush()

    db_session.add(KbArticle(slug="spravka", title="Другая", body_md="…"))
    with pytest.raises(IntegrityError):
        db_session.flush()


# --- Enum'ы пишутся в БД ЗНАЧЕНИЯМИ, а не именами ------------------------
# Грабли, на которые проект уже наступал: без values_callable SQLAlchemy
# кладёт в VARCHAR имя члена ('UPPER'), а API и клиент ждут значение
# ('upper'). Ловится только сырым SQL — ORM подменяет обратно и молчит.


def _raw(db_session, sql: str):
    return db_session.execute(text(sql)).scalars().all()


def test_week_type_stored_as_value_not_name(db_session):
    gid = _make_group(db_session)
    db_session.add(make_lesson(gid, week_type=WeekType.UPPER))
    db_session.add(make_lesson(gid, pair_number=2, week_type=WeekType.LOWER))
    db_session.flush()

    stored = _raw(db_session, "select week_type from lessons order by pair_number")
    assert stored == ["upper", "lower"]


def test_education_level_stored_as_value_not_name(db_session):
    db_session.add(Group(course=1, number="1.1", level=EducationLevel.BACHELOR))
    db_session.flush()

    assert _raw(db_session, "select level from groups") == ["bachelor"]


def test_lesson_kind_stored_as_value_not_name(db_session):
    gid = _make_group(db_session)
    db_session.add(make_lesson(gid, lesson_kind=LessonKind.LECTURE))
    db_session.flush()

    assert _raw(db_session, "select lesson_kind from lessons") == ["lecture"]


def test_doc_type_stored_as_value_not_name(db_session):
    _make_document(db_session)

    assert _raw(db_session, "select doc_type from schedule_documents") == [
        "semester_grid_bachelor"
    ]


# --- Group: у магистров номера группы НЕТ, есть программа -----------------


def test_master_group_has_program_and_no_number(db_session):
    db_session.add(
        Group(
            course=1,
            number=None,
            level=EducationLevel.MASTER,
            program="Экономика, управление и право",
        )
    )
    db_session.flush()  # не должно упасть: number nullable


def test_group_level_defaults_to_bachelor(db_session):
    group = Group(course=2, number="2.1")
    db_session.add(group)
    db_session.flush()

    assert group.level is EducationLevel.BACHELOR


def test_duplicate_master_program_rejected(db_session):
    def master():
        return Group(
            course=1,
            number=None,
            level=EducationLevel.MASTER,
            program="Экономика, управление и право",
        )

    db_session.add(master())
    db_session.flush()

    # NULL-номер не должен превращать уникальность в фикцию:
    # (course, number) с NULL'ами в SQL не конфликтует сам с собой
    db_session.add(master())
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_same_program_different_course_allowed(db_session):
    for course in (1, 2):
        db_session.add(
            Group(
                course=course,
                number=None,
                level=EducationLevel.MASTER,
                program="Экономика, управление и право",
            )
        )
    db_session.flush()  # не должно упасть


# --- Lesson: модули, вид занятия, сырьё ----------------------------------


def test_same_slot_different_module_allowed(db_session):
    gid = _make_group(db_session)
    did = _make_document(db_session)
    modules = [
        Module(
            document_id=did,
            name="I модуль",
            date_from=date(2025, 9, 1),
            date_to=date(2025, 11, 2),
        ),
        Module(
            document_id=did,
            name="2 модуль",
            date_from=date(2025, 11, 3),
            date_to=date(2025, 11, 23),
        ),
    ]
    db_session.add_all(modules)
    db_session.flush()

    # Один и тот же слот в разных модулях — разные пары, а не дубль
    db_session.add(make_lesson(gid, module_id=modules[0].id))
    db_session.add(make_lesson(gid, module_id=modules[1].id, subject="Статистика"))
    db_session.flush()  # не должно упасть


def test_duplicate_slot_within_module_rejected(db_session):
    gid = _make_group(db_session)
    did = _make_document(db_session)
    module = Module(
        document_id=did,
        name="I модуль",
        date_from=date(2025, 9, 1),
        date_to=date(2025, 11, 2),
    )
    db_session.add(module)
    db_session.flush()

    db_session.add(make_lesson(gid, module_id=module.id))
    db_session.flush()

    db_session.add(make_lesson(gid, module_id=module.id))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_lesson_keeps_cell_raw_and_date_constraint(db_session):
    gid = _make_group(db_session)
    lesson = make_lesson(
        gid,
        subject="Анализ данных",
        lesson_kind=LessonKind.LECTURE,
        date_constraint_raw="До 14.05",
        cell_raw="До 14.05Анализ данных (л) Шаль А.В.  ауд.118",
    )
    db_session.add(lesson)
    db_session.flush()
    db_session.expire_all()

    stored = db_session.get(Lesson, lesson.id)
    assert stored.cell_raw == "До 14.05Анализ данных (л) Шаль А.В.  ауд.118"
    assert stored.date_constraint_raw == "До 14.05"
    assert stored.week_type is None  # каждую неделю


# --- Новые сущности импорта ----------------------------------------------


def test_duplicate_p_doc_id_rejected(db_session):
    _make_document(db_session, p_doc_id=13469)

    _make_document_dup = ScheduleDocument(
        p_doc_id=13469,
        section="Весенний семестр",
        label="1 курс",
        doc_type=DocType.SEMESTER_GRID_BACHELOR,
        sha256="b" * 64,
        source_url="https://sfedu.ru/www/sched_files.f_download?p_doc_id=13469",
    )
    db_session.add(_make_document_dup)
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_week_calendar_row(db_session):
    did = _make_document(db_session)
    row = WeekCalendar(
        document_id=did,
        date_from=date(2025, 9, 1),
        date_to=date(2025, 9, 7),
        week_type=WeekType.UPPER,
    )
    db_session.add(row)
    db_session.flush()

    assert _raw(db_session, "select week_type from week_calendars") == ["upper"]


def test_unparsed_cell_row(db_session):
    did = _make_document(db_session)
    db_session.add(
        UnparsedCell(
            document_id=did,
            page=3,
            raw_text="800- 1025",
            reason="время вне сетки пар",
        )
    )
    db_session.flush()  # не должно упасть


def test_exam_event_row(db_session):
    gid = _make_group(db_session)
    exam = ExamEvent(
        group_id=gid,
        subject="Экосистема современной организации",
        teacher="Чернова О.А.",
        consultation_at=datetime(2026, 4, 8, 11, 0),
        exam_at=datetime(2026, 4, 9, 9, 0),
        room="214",
        kind="устный",
        cell_raw="09.04.26\n09.00-13.30\nустный\nауд.214",
    )
    db_session.add(exam)
    db_session.flush()
    db_session.expire_all()

    assert db_session.get(ExamEvent, exam.id).kind == "устный"
