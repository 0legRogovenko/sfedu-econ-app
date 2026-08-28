"""Кураторские переименования предметов (SubjectRename) + /api/version +
/api/persons/{id}/exams."""

from datetime import datetime, time

from src.models import Contact, ExamEvent, Group, Lesson, SubjectRename
from src.persons.directory import encode_id
from src.persons.names import key_of_full


def _group(db):
    g = Group(course=1, number="1.1", subgroup_count=2)
    db.add(g)
    db.flush()
    return g


def _lesson(group_id, subject, **kw):
    base = dict(
        group_id=group_id,
        weekday=0,
        pair_number=1,
        starts_at=time(9, 0),
        ends_at=time(10, 35),
        subject=subject,
        subgroup=0,
    )
    base.update(kw)
    return Lesson(**base)


class TestSubjectRenames:
    def test_curated_ict_alias_is_available_without_admin_seed(
        self, client, db_session
    ):
        """Очевидная аббревиатура не должна дробить один предмет в UI.

        Источник в БД остаётся дословным; каноническое имя подставляет слой
        чтения даже в свежей beta-БД, где администратор ещё не создавал
        SubjectRename вручную.
        """
        g = _group(db_session)
        db_session.add(_lesson(g.id, "ИКТ"))
        db_session.flush()

        payload = client.get(f"/api/schedule?group_id={g.id}").json()

        assert [lesson["subject"] for lesson in payload["lessons"]] == [
            "Информационно-коммуникационные технологии"
        ]
        assert db_session.query(Lesson).one().subject == "ИКТ"

    def test_curated_business_process_aliases_share_one_display_name(
        self, client, db_session
    ):
        """Сокращения одного предмета не выглядят разными дисциплинами."""
        g = _group(db_session)
        source_names = (
            "Анализ и мод. БП",
            "Анализ и моделирование БП",
            "Анализ и модел. бизнес-процессов",
        )
        for pair_number, subject in enumerate(source_names, start=1):
            db_session.add(_lesson(g.id, subject, pair_number=pair_number))
        db_session.flush()

        payload = client.get(f"/api/schedule?group_id={g.id}").json()

        assert {lesson["subject"] for lesson in payload["lessons"]} == {
            "Анализ и моделирование бизнес-процессов"
        }
        assert {lesson.subject for lesson in db_session.query(Lesson).all()} == set(
            source_names
        )

    def test_schedule_returns_display_subject(self, client, db_session):
        g = _group(db_session)
        db_session.add(_lesson(g.id, "Институциональна я экономика"))
        db_session.add(
            SubjectRename(
                match_subject="Институциональна я экономика",
                display_subject="Институциональная экономика",
            )
        )
        db_session.flush()

        subjects = [
            l["subject"]
            for l in client.get(f"/api/schedule?group_id={g.id}").json()["lessons"]
        ]
        assert subjects == ["Институциональная экономика"]

    def test_unmatched_subject_untouched(self, client, db_session):
        g = _group(db_session)
        db_session.add(_lesson(g.id, "Матанализ"))
        db_session.add(
            SubjectRename(match_subject="Другое", display_subject="Иное")
        )
        db_session.flush()

        subjects = [
            l["subject"]
            for l in client.get(f"/api/schedule?group_id={g.id}").json()["lessons"]
        ]
        assert subjects == ["Матанализ"]

    def test_exams_renamed_too(self, client, db_session):
        g = _group(db_session)
        db_session.add(
            ExamEvent(group_id=g.id, subject="Data Sciience", teacher=None)
        )
        db_session.add(
            SubjectRename(
                match_subject="Data Sciience", display_subject="Data Science"
            )
        )
        db_session.flush()

        exams = client.get(f"/api/exams?group_id={g.id}").json()
        assert [e["subject"] for e in exams] == ["Data Science"]

    def test_db_keeps_source_text(self, client, db_session):
        # Слой чтения: в БД остаётся дословный текст источника.
        g = _group(db_session)
        db_session.add(_lesson(g.id, "Институциональна я экономика"))
        db_session.add(
            SubjectRename(
                match_subject="Институциональна я экономика",
                display_subject="Институциональная экономика",
            )
        )
        db_session.flush()
        client.get(f"/api/schedule?group_id={g.id}")

        stored = db_session.query(Lesson).one().subject
        assert stored == "Институциональна я экономика"


class TestVersionGate:
    def test_version_returns_min_build(self, client):
        body = client.get("/api/version").json()
        assert body == {"min_build": 1}

    def test_min_build_configurable(self, client, monkeypatch):
        from src.config import settings

        monkeypatch.setattr(settings, "min_app_build", 5)
        assert client.get("/api/version").json() == {"min_build": 5}


class TestPersonExams:
    def test_person_exams_linked_by_teacher_text(self, client, db_session):
        g = _group(db_session)
        db_session.add(
            Contact(section="Кафедра", name="Ласкова Татьяна Сергеевна")
        )
        db_session.add(
            ExamEvent(
                group_id=g.id,
                subject="Экономика",
                teacher="Ласкова Т.С.",
                exam_at=datetime(2026, 1, 15, 10, 0),
            )
        )
        # чужой экзамен — не должен попасть
        db_session.add(
            ExamEvent(group_id=g.id, subject="Право", teacher="Иванов И.И.")
        )
        db_session.flush()

        pid = encode_id(key_of_full("Ласкова Татьяна Сергеевна"))
        exams = client.get(f"/api/persons/{pid}/exams").json()

        assert [e["subject"] for e in exams] == ["Экономика"]

    def test_person_exams_sorted_nulls_last(self, client, db_session):
        g = _group(db_session)
        db_session.add(Contact(section="Кафедра", name="Ласкова Татьяна Сергеевна"))
        db_session.add(
            ExamEvent(group_id=g.id, subject="Без даты", teacher="Ласкова Т.С.")
        )
        db_session.add(
            ExamEvent(
                group_id=g.id,
                subject="С датой",
                teacher="Ласкова Т.С.",
                exam_at=datetime(2026, 1, 20, 10, 0),
            )
        )
        db_session.flush()

        pid = encode_id(key_of_full("Ласкова Татьяна Сергеевна"))
        exams = client.get(f"/api/persons/{pid}/exams").json()
        assert [e["subject"] for e in exams] == ["С датой", "Без даты"]

    def test_bad_id_404(self, client):
        assert client.get("/api/persons/@@@bad/exams").status_code == 404
