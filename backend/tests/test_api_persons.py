"""Единый справочник людей: /api/persons и /api/persons/{id}/schedule.

Юнит-тесты на клиенте с синтетикой + golden на живом корпусе.
"""

from datetime import date, time

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from src.models import Contact, Lesson, Teacher
from src.persons.directory import decode_id, encode_id


def _lesson(**kw):
    base = dict(
        group_id=1,
        weekday=0,
        pair_number=1,
        starts_at=time(9, 0),
        ends_at=time(10, 35),
        subject="Предмет",
        subgroup=0,
    )
    base.update(kw)
    return Lesson(**base)


class TestDirectoryEndpoint:
    def test_contact_person_has_full_and_short_name(self, client, db_session):
        db_session.add(Contact(section="Деканат", name="Вольчик Вячеслав Витальевич"))
        db_session.flush()

        people = client.get("/api/persons").json()
        volchik = next(p for p in people if p["short_name"] == "Вольчик В.В.")

        assert volchik["full_name"] == "Вольчик Вячеслав Витальевич"
        assert volchik["has_schedule"] is False

    def test_deanery_reversed_name_normalizes(self, client, db_session):
        # Деканат пишет «Имя Отчество Фамилия» — короткая форма всё равно
        # «Фамилия И.О.».
        db_session.add(
            Contact(section="Деканат", name="Оксана Александровна Ищенко-Падукова")
        )
        db_session.flush()

        people = client.get("/api/persons").json()
        assert any(p["short_name"] == "Ищенко-Падукова О.А." for p in people)

    def test_external_teacher_appears_without_email(self, client, db_session):
        # Преподаватель есть в расписании, но контакта нет — карточка всё равно
        # должна быть, иначе единый поиск потеряет его пары.
        db_session.add(Teacher(full_name="Груданова И.Ю."))
        db_session.add(
            _lesson(subject="Матан", cell_raw="Матан (л) Груданова И.Ю. ауд.1")
        )
        db_session.flush()

        people = client.get("/api/persons").json()
        grud = next(p for p in people if p["short_name"] == "Груданова И.Ю.")

        assert grud["email"] is None
        assert grud["has_schedule"] is True
        assert grud["lesson_count"] == 1

    def test_garbage_is_not_a_person(self, client, db_session):
        db_session.add(Teacher(full_name="Беликова С.А. Г-217 АКТРУ"))
        db_session.add(
            _lesson(cell_raw="Учёт (л) Беликова С.А. Г-217 АКТРУ ауд.214")
        )
        db_session.flush()

        names = {p["short_name"] for p in client.get("/api/persons").json()}
        assert "Беликова С.А." in names
        assert not any(n.startswith("Акт") for n in names)

    def test_two_sections_collapse_into_one_person(self, client, db_session):
        # Один человек в деканате и на кафедре — одна карточка, две роли.
        db_session.add_all(
            [
                Contact(
                    section="Деканат",
                    name="Елена Владимировна Фурса",
                    role="заместитель декана",
                    email="efursa@sfedu.ru",
                ),
                Contact(
                    section="Финансы и кредит",
                    name="Фурса Елена Владимировна",
                    role="доцент",
                    email="efursa@sfedu.ru",
                ),
            ]
        )
        db_session.flush()

        people = client.get("/api/persons").json()
        fursa = [p for p in people if p["short_name"] == "Фурса Е.В."]

        assert len(fursa) == 1
        assert set(fursa[0]["sections"]) == {"Деканат", "Финансы и кредит"}
        assert set(fursa[0]["roles"]) == {"заместитель декана", "доцент"}


class TestPersonSchedule:
    def test_schedule_by_person_id(self, client, db_session):
        db_session.add(Contact(section="Кафедра", name="Вольчик Вячеслав Витальевич"))
        db_session.add(
            _lesson(subject="Институты", cell_raw="Институты (л) Вольчик В.В. ауд.1")
        )
        db_session.flush()

        people = client.get("/api/persons").json()
        volchik = next(p for p in people if p["short_name"] == "Вольчик В.В.")

        schedule = client.get(f"/api/persons/{volchik['id']}/schedule").json()
        assert len(schedule["lessons"]) == 1
        assert schedule["lessons"][0]["subject"] == "Институты"

    def test_person_without_contact_in_teachers_table_still_gets_pairs(
        self, client, db_session
    ):
        # Ради этого линкер и читает cell_raw: человека НЕТ в teachers, но пары
        # есть. Через /api/schedule?teacher_id их было бы не достать.
        db_session.add(Contact(section="Кафедра", name="Погорелова Татьяна Геннадьевна"))
        db_session.add(
            _lesson(
                subject="Учёт",
                cell_raw="Учёт (с) Лебедева Н.Ю., Погорелова Т.Г. ауд.214",
            )
        )
        db_session.flush()

        people = client.get("/api/persons").json()
        pog = next(p for p in people if p["short_name"] == "Погорелова Т.Г.")

        assert (
            db_session.scalars(
                select(Teacher).where(Teacher.full_name.like("%Погорелова%"))
            ).all()
            == []
        )
        schedule = client.get(f"/api/persons/{pog['id']}/schedule").json()
        assert len(schedule["lessons"]) == 1

    def test_bad_id_is_404_not_500(self, client):
        assert client.get("/api/persons/не-валидный-id/schedule").status_code == 404

    def test_id_roundtrip(self):
        key = ("вольчик", "в", "в")
        assert decode_id(encode_id(key)) == key


class TestGoldenLiveDirectory:
    @pytest.fixture()
    def live(self):
        from pathlib import Path

        url = "postgresql+psycopg2://sfedu:sfedu@localhost:5433/sfedu_econ"
        env = Path(__file__).resolve().parents[1] / ".env"
        if env.exists():
            for line in env.read_text(encoding="utf-8").splitlines():
                k, sep, v = line.partition("=")
                if sep and k.strip() == "DATABASE_URL":
                    url = v.strip()
        engine = create_engine(url)
        try:
            with Session(engine) as session:
                session.execute(select(1))
                yield session
        except OperationalError as exc:
            pytest.skip(f"живая БД недоступна: {exc.orig}")
        finally:
            engine.dispose()

    def test_directory_shape(self, live):
        # Точные числа НЕ фиксируем: они зависят от ручных правок (скрытия),
        # а те — данные, не алгоритм. Инварианты линковки пинует
        # test_person_linker. Здесь — что справочник осмысленного размера,
        # без мусора, и что курация применена.
        from src.persons.directory import build_directory

        people = build_directory(live)
        shorts = {p.short_name for p in people}

        assert 100 <= len(people) <= 200
        assert not [p for p in people if p.short_name.startswith(("Акт ", "Дисциплины"))]
        # скрытые правкой отсутствуют
        assert "Погорелова Т.Г." not in shorts
        assert "Патракеева О.Ю." not in shorts
        # почты заведующих, вписанные правкой (их страницы отдают 404)
        by_short = {p.short_name: p for p in people}
        assert by_short["Фролова И.В."].email == "ifrolova@sfedu.ru"
        assert by_short["Маслюкова Е.В."].email == "maslyukova@sfedu.ru"

    def test_namesakes_are_two_cards(self, live):
        from src.persons.directory import build_directory

        shorts = [p.short_name for p in build_directory(live)]
        assert shorts.count("Ласкова Т.С.") == 1
        assert shorts.count("Ласкова Д.С.") == 1


class TestDirectoryOverrides:
    """Ручные правки поверх автозабора: пин почты и скрытие людей."""

    def test_hidden_person_disappears(self, client, db_session):
        from src.models import DirectoryOverride

        db_session.add(Contact(section="Кафедра", name="Погорелова Татьяна Геннадьевна"))
        db_session.add(DirectoryOverride(match_name="Погорелова Т.Г.", hidden=True))
        db_session.flush()

        names = {p["short_name"] for p in client.get("/api/persons").json()}
        assert "Погорелова Т.Г." not in names

    def test_pinned_email_appears(self, client, db_session):
        # Почта заведующего: его личная страница отдаёт 404, автозабор её не
        # добудет — вписываем правкой.
        from src.models import DirectoryOverride

        db_session.add(Contact(section="Кафедра", name="Фролова Ирина Вениаминовна"))
        db_session.add(
            DirectoryOverride(match_name="Фролова И.В.", email="ifrolova@sfedu.ru")
        )
        db_session.flush()

        person = next(
            p for p in client.get("/api/persons").json()
            if p["short_name"] == "Фролова И.В."
        )
        assert person["email"] == "ifrolova@sfedu.ru"

    def test_pinned_email_wins_over_site(self, client, db_session):
        from src.models import DirectoryOverride

        db_session.add(
            Contact(
                section="Кафедра",
                name="Вольчик Вячеслав Витальевич",
                email="site@sfedu.ru",
            )
        )
        db_session.add(
            DirectoryOverride(match_name="Вольчик В.В.", email="volchik@sfedu.ru")
        )
        db_session.flush()

        person = next(
            p for p in client.get("/api/persons").json()
            if p["short_name"] == "Вольчик В.В."
        )
        assert person["email"] == "volchik@sfedu.ru"

    def test_unparseable_override_is_ignored(self, client, db_session):
        from src.models import DirectoryOverride

        db_session.add(Contact(section="Кафедра", name="Вольчик Вячеслав Витальевич"))
        db_session.add(DirectoryOverride(match_name="мусор", hidden=True))
        db_session.flush()

        # Кривая правка не роняет справочник и никого не скрывает.
        names = {p["short_name"] for p in client.get("/api/persons").json()}
        assert "Вольчик В.В." in names
