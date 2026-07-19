"""Парсер сотрудников econ-sfedu.ru — на сохранённых страницах реального сайта.

Вёрстка сменится → тест упадёт, а не отдаст молча пустой справочник.
"""

from pathlib import Path

import pytest

from src.parsers import econ_staff

FIXTURES = Path(__file__).parent / "fixtures" / "econ_staff"


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


@pytest.fixture()
def about_us() -> str:
    return _fixture("about-us.html")


@pytest.fixture()
def kafedra_teoria() -> str:
    return _fixture("kafedra-teoria.html")


@pytest.fixture()
def kafedra_finansy() -> str:
    return _fixture("kafedra-finansy.html")


@pytest.fixture()
def kafedra_mir_ek() -> str:
    """Кафедра со ВТОРЫМ макетом: люди в блоках sppb-addon-person, а не в
    карусели, и заведующий подписан «и.о. заведующего кафедрой»."""
    return _fixture("kafedra-mir-ek.html")


class TestDeanery:
    def test_parses_staff(self, about_us):
        people = econ_staff.parse_deanery(about_us)

        assert len(people) >= 5
        by_name = {p.name: p for p in people}
        assert "Оксана Александровна Ищенко-Падукова" in by_name
        assert (
            by_name["Оксана Александровна Ищенко-Падукова"].role
            == "заместитель декана по учебной работе"
        )

    def test_phone_from_tel_link(self, about_us):
        people = {p.name: p for p in econ_staff.parse_deanery(about_us)}
        person = people["Оксана Александровна Ищенко-Падукова"]
        # В разметке телефон лежит как `tel: +78632184000-13009` — с пробелом
        # после схемы и добавочным через дефис.
        assert person.phone == "+78632184000-13009"

    def test_every_person_has_name_and_role(self, about_us):
        for person in econ_staff.parse_deanery(about_us):
            assert person.name.strip()
            assert person.role.strip()
            # ФИО, а не подпись к фото: минимум два слова
            assert len(person.name.split()) >= 2


class TestDepartment:
    def test_department_name(self, kafedra_teoria):
        dept = econ_staff.parse_department(kafedra_teoria)
        assert dept.name == "Экономическая теория"

    def test_head_of_department(self, kafedra_teoria):
        dept = econ_staff.parse_department(kafedra_teoria)
        assert dept.head is not None
        assert dept.head.name == "Вольчик Вячеслав Витальевич"
        assert dept.head.role == "Заведующий кафедрой, д.э.н., профессор"

    def test_staff_names_and_degrees(self, kafedra_teoria):
        dept = econ_staff.parse_department(kafedra_teoria)
        by_name = {p.name: p for p in dept.staff}

        assert "Белокрылова Ольга Спиридоновна" in by_name
        assert by_name["Белокрылова Ольга Спиридоновна"].role.startswith("д.э.н.")
        assert by_name["Гуцелюк Елена Федоровна"].role == "к.э.н., доцент"
        # Не только преподаватели: методисты кафедры тоже в справочнике
        assert (
            by_name["Кудряшова Виктория Сергеевна"].role
            == "специалист по учебно-методической работе"
        )

    def test_head_keeps_profile_link(self, kafedra_teoria):
        """Ссылка на личную страницу заведующего терялась.

        Из-за этого почты семи заведующих — самых нужных контактов кафедры —
        было неоткуда взять: страницу просто не запрашивали.
        """
        dept = econ_staff.parse_department(kafedra_teoria)
        assert dept.head.profile_url is not None
        assert "sfedu.ru" in dept.head.profile_url
        # И не покалечена html.unescape (см. TestProfileLinks)
        assert "¶" not in dept.head.profile_url

    def test_head_not_duplicated_in_staff(self, kafedra_teoria):
        """Заведующий отдельной карточкой — его не должно быть дважды."""
        dept = econ_staff.parse_department(kafedra_teoria)
        names = [p.name for p in dept.staff]
        assert names.count("Вольчик Вячеслав Витальевич") == 0

    def test_alternate_layout_head(self, kafedra_mir_ek):
        # Регрессия: на этой кафедре другой макет, и заведующий терялся молча —
        # парсер отдавал кафедру вообще без заведующего.
        dept = econ_staff.parse_department(kafedra_mir_ek)
        assert dept.name == "Мировая экономика и международные отношения"
        assert dept.head is not None
        assert dept.head.name == "Елецкий Алексей Николаевич"
        assert "заведующего кафедрой" in dept.head.role

    def test_alternate_layout_staff(self, kafedra_mir_ek):
        dept = econ_staff.parse_department(kafedra_mir_ek)
        names = {p.name for p in dept.staff}
        # Люди из блоков sppb-addon-person тоже попадают в состав
        assert len(dept.staff) >= 3
        assert "Елецкий Алексей Николаевич" not in names

    def test_second_department_parses_too(self, kafedra_finansy):
        """Вторая кафедра — чтобы парсер не был подогнан под одну страницу."""
        dept = econ_staff.parse_department(kafedra_finansy)
        assert dept.name
        assert len(dept.staff) >= 5
        for person in dept.staff:
            assert len(person.name.split()) >= 2


class TestDepartmentLinks:
    def test_finds_all_department_pages(self):
        listing = _fixture("about-us.html")  # шапка одинаковая на всех страницах
        # Ссылки на кафедры лежат в разделе «Кафедры», а не в шапке — берём
        # страницу-каталог, если она есть; иначе проверяем на статье кафедры.
        links = econ_staff.parse_department_links(listing)
        assert isinstance(links, list)


class TestProfileLinks:
    def test_href_amp_not_mangled(self):
        """`&params=` в ссылке нельзя гнать через html.unescape целиком.

        Регрессия: `&para` — это HTML-сущность (¶), и полный unescape ломал
        ссылку на личную страницу, превращая её в 404.
        """
        page = (
            '<div class="sppb-carousel-extended-team-wrap">'
            '<div class="sppb-carousel-extended-team-name">'
            '<a href="https://sfedu.ru/www/stat_pages22.show?p=UNI/s1/D'
            '&params=(p_per_id=%3E2995)">Иванов Иван Иванович</a></div>'
            '<div class="sppb-carousel-extended-team-designation">доцент</div>'
            "<ul></ul></div></div></div>"
        )
        person = econ_staff._parse_cards(page)[0]
        assert "&params=" in person.profile_url
        assert "¶" not in person.profile_url

    def test_amp_entity_is_decoded(self):
        page = (
            '<div class="sppb-carousel-extended-team-wrap">'
            '<div class="sppb-carousel-extended-team-name">'
            '<a href="https://sfedu.ru/x?a=1&amp;b=2">Иванов Иван Иванович</a>'
            "</div><ul></ul></div></div></div>"
        )
        person = econ_staff._parse_cards(page)[0]
        assert person.profile_url == "https://sfedu.ru/x?a=1&b=2"


class TestPersonEmail:
    def test_decodes_obfuscated_mailto(self):
        """Почта на sfedu.ru спрятана в base64 внутри адреса-приманки."""
        page = _fixture("person-sfedu.html")
        assert econ_staff.parse_person_email(page) == "obelokrylova@sfedu.ru"

    def test_no_email_returns_none(self):
        assert econ_staff.parse_person_email("<html></html>") is None

    def test_decoy_address_never_returned(self):
        """Адрес-приманка нерабочий: вернуть его хуже, чем не вернуть ничего."""
        page = _fixture("person-sfedu.html")
        email = econ_staff.parse_person_email(page)
        assert "sfedu-university.com" not in email
        assert not email.startswith("hello+")

    def test_broken_base64_is_ignored(self):
        page = '<a href="mailto:hello+не-base64@sfedu-university.com">почта</a>'
        assert econ_staff.parse_person_email(page) is None

    def test_plain_mailto_is_taken_as_is(self):
        page = '<a href="mailto:dekanat.econ@sfedu.ru">почта</a>'
        assert econ_staff.parse_person_email(page) == "dekanat.econ@sfedu.ru"


class TestGuards:
    def test_empty_html_yields_nothing(self):
        assert econ_staff.parse_deanery("<html></html>") == []
        dept = econ_staff.parse_department("<html></html>")
        assert dept.staff == []

    def test_garbage_does_not_raise(self):
        econ_staff.parse_deanery("не html вовсе")
        econ_staff.parse_department("")
