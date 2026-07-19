"""Разбор ФИО — на настоящих сотрудниках экономфака ЮФУ.

Справочник приходит из двух источников с РАЗНЫМ порядком слов, а сравнение
людей между источниками идёт по ключу. Ошибка здесь не падает, а тихо
портит данные: человек либо выпадает из справочника, либо склеивается с
однофамильцем. Поэтому тесты держат оба формата, реальные фамилии на -ич,
типографские тире из Word и живой инвариант по всей таблице contacts.
"""

from pathlib import Path

import pytest

from src.persons.names import key_of_full, parse_person, person_key, short_name


class TestParseFioOrder:
    """Порядок «Фамилия Имя Отчество» — справочник кафедр."""

    def test_plain_fio(self):
        assert parse_person("Вольчик Вячеслав Витальевич") == (
            "Вольчик",
            "Вячеслав",
            "Витальевич",
        )
        assert short_name("Вольчик Вячеслав Витальевич") == "Вольчик В.В."

    def test_hyphenated_surname(self):
        assert (
            short_name("Кривошеева-Медянцева Дарья Дмитриевна")
            == "Кривошеева-Медянцева Д.Д."
        )

    def test_short_surname(self):
        # Фамилия из трёх букв не должна выглядеть «лишним инициалом».
        assert short_name("Кот Вера Витальевна") == "Кот В.В."

    def test_patronymic_suffix_ich(self):
        # «Ильич» не подходит под -ович/-евич, но это отчество.
        assert short_name("Маскаев Артём Ильич") == "Маскаев А.И."

    def test_nonstandard_evna(self):
        # «Володяевна» — редкое отчество от имени Володя, в штате есть.
        assert short_name("Погосян Нателла Володяевна") == "Погосян Н.В."


class TestParseIofOrder:
    """Порядок «Имя Отчество Фамилия» — так отдаёт страница деканата."""

    def test_deanery_order(self):
        assert parse_person("Оксана Александровна Ищенко-Падукова") == (
            "Ищенко-Падукова",
            "Оксана",
            "Александровна",
        )
        # Наивный разбор «первый токен — всегда фамилия» дал бы «Оксана А.И.»:
        # в справочнике появился бы человек по имени Оксана.
        assert (
            short_name("Оксана Александровна Ищенко-Падукова")
            == "Ищенко-Падукова О.А."
        )


class TestSurnameLooksLikePatronymic:
    """Регрессия: фамилии на -ович/-евич подходят под шаблон отчества.

    В таком ФИО кандидатов на отчество ДВА, и разбор «ровно один кандидат»
    молча отказывает. Спасает только приоритет среднего токена.
    """

    @pytest.mark.parametrize(
        "full",
        ["Рабинович Иван Петрович", "Иван Петрович Рабинович"],
    )
    def test_rabinovich_both_orders(self, full):
        assert short_name(full) == "Рабинович И.П."

    @pytest.mark.parametrize(
        "full",
        ["Гринкевич Иван Петрович", "Иван Петрович Гринкевич"],
    )
    def test_grinkevich_both_orders(self, full):
        assert short_name(full) == "Гринкевич И.П."


class TestUnparseable:
    def test_four_tokens(self):
        # Двойное имя и двойная фамилия: разложить на тройку нечем, и
        # угадывать нельзя — лучше честный None.
        assert parse_person("Бермудес Сото Хосе Грегорио") is None
        assert short_name("Бермудес Сото Хосе Грегорио") is None

    def test_two_tokens(self):
        assert parse_person("Иванов Иван") is None

    def test_no_patronymic_at_all(self):
        assert parse_person("Иванов Иван Иванов") is None

    def test_empty(self):
        assert parse_person("") is None
        assert parse_person("   ") is None


class TestWhitespace:
    def test_nbsp_between_tokens(self):
        # Вёрстка econ-sfedu.ru разделяет слова &nbsp;, и без схлопывания
        # \s+ ФИО приезжает одним токеном и не разбирается вовсе.
        assert short_name("Вольчик\xa0Вячеслав\xa0Витальевич") == "Вольчик В.В."

    def test_ragged_spacing(self):
        assert short_name("  Вольчик   Вячеслав\tВитальевич  ") == "Вольчик В.В."


class TestPersonKey:
    def test_dash_variants_are_equal(self):
        # Word автозаменяет дефис на тире: одна и та же преподавательница
        # приезжает из docx через «–», а с сайта — через «-».
        assert key_of_full("Кривошеева-Медянцева Дарья Дмитриевна") == key_of_full(
            "Кривошеева–Медянцева Дарья Дмитриевна"
        )

    def test_different_initials_are_different(self):
        # Ласкова Т.С. и Ласкова Д.С. — два живых человека на факультете.
        assert person_key("Ласкова", "Т", "С") != person_key("Ласкова", "Д", "С")

    def test_case_and_yo_folded(self):
        assert person_key("ФЁДОРОВА", "А", "Б") == person_key("Федорова", "а", "б")

    def test_key_from_full_matches_manual_key(self):
        assert key_of_full("Вольчик Вячеслав Витальевич") == person_key(
            "Вольчик", "В", "В"
        )

    def test_key_accepts_initials_with_dots(self):
        assert person_key("Ласкова", "Т.", "С.") == person_key("Ласкова", "Т", "С")

    def test_unparseable_has_no_key(self):
        assert key_of_full("Иванов Иван") is None


def _live_database_url() -> str:
    """URL настоящей базы — в обход conftest.

    conftest.py подменяет DATABASE_URL на sqlite:// ДО импорта src.config,
    поэтому settings.database_url тут показывает пустую тестовую базу.
    Читаем backend/.env сами.
    """
    env_file = Path(__file__).resolve().parents[1] / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            key, sep, value = line.partition("=")
            if sep and key.strip() == "DATABASE_URL":
                return value.strip()
    return "postgresql+psycopg2://sfedu:sfedu@localhost:5433/sfedu_econ"


@pytest.fixture()
def live_contact_names() -> list[str]:
    from sqlalchemy import create_engine, select
    from sqlalchemy.exc import OperationalError
    from sqlalchemy.orm import Session

    from src.models import Contact

    engine = create_engine(_live_database_url())
    try:
        with Session(engine) as session:
            return list(session.scalars(select(Contact.name)))
    except OperationalError as exc:
        pytest.skip(f"живая БД недоступна, инвариант не проверен: {exc.orig}")
    finally:
        engine.dispose()


class TestLiveContactsInvariant:
    """Живой инвариант: разбор обязан покрывать ВЕСЬ справочник целиком.

    Юнит-тесты выше знают только те ФИО, которые я вспомнил. Этот тест ходит
    в настоящую базу и ловит форму, которую никто не предусмотрел: новый
    сотрудник с четвёртым словом в имени или с отчеством на незнакомый
    суффикс просто выпал бы из справочника молча.
    """

    def test_every_contact_parses(self, live_contact_names):
        failed = [name for name in live_contact_names if parse_person(name) is None]

        assert not failed, "не разобрались ФИО из contacts ({}): {}".format(
            len(failed), "; ".join(repr(name) for name in failed)
        )

    def test_format_split_matches_reality(self, live_contact_names):
        fio, iof = [], []
        for name in live_contact_names:
            parsed = parse_person(name)
            if parsed is None:
                continue
            surname = parsed[0]
            # Формат определяем по тому, где оказалась фамилия: первым
            # токеном — «Фамилия Имя Отчество», последним — деканатский.
            if name.split()[0] == surname:
                fio.append(name)
            else:
                iof.append(name)

        assert (len(live_contact_names), len(fio), len(iof)) == (85, 73, 12), (
            "состав справочника разошёлся с ожиданием: всего "
            f"{len(live_contact_names)}, ФИО {len(fio)}, ИОФ {len(iof)}; "
            "если справочник правда обновился — поправьте числа, "
            "если нет — сломался разбор"
        )


class TestRobustness:
    """Дыры, найденные проверяющим агентом.

    Все они одного класса: ФИО не разбирается — человек молча выпадает из
    реестра, и ВСЕ его пары остаются без карточки. Молчаливая потеря опаснее
    отказа, потому что заметить её в интерфейсе нечем.
    """

    def test_caps_full_name(self):
        # extract.py капс терпит и нормализует («ВОЛЬЧИК В.В.» есть в корпусе),
        # а names.py его отвергал. Одна капсовая запись на сайте вычеркнула бы
        # преподавателя из реестра целиком.
        assert short_name("ВОЛЬЧИК ВЯЧЕСЛАВ ВИТАЛЬЕВИЧ") == "Вольчик В.В."

    def test_trailing_punctuation(self):
        assert short_name("Вольчик Вячеслав Витальевич,") == "Вольчик В.В."
        assert short_name("Вольчик Вячеслав Витальевич.") == "Вольчик В.В."

    def test_zero_width_space(self):
        # U+200B не входит в \s: ФИО склеивалось в один токен и отвергалось.
        # Частый артефакт копирования из вёрстки.
        assert short_name("Вольчик​Вячеслав​Витальевич") == "Вольчик В.В."

    def test_old_female_patronymics(self):
        assert short_name("Кузнецова Анна Никитишна") == "Кузнецова А.Н."
        assert short_name("Кузнецова Анна Ильинишна") == "Кузнецова А.И."

    def test_turkic_patronymics(self):
        assert short_name("Гусейнов Ислам Мамедоглы") == "Гусейнов И.М."
        assert short_name("Алиева Лейла Мамедкызы") == "Алиева Л.М."

    def test_still_rejects_garbage(self):
        # Починка не должна размывать отказ: без отчества разбирать нечем.
        assert parse_person("Иванов Иван") is None
        assert parse_person("Бермудес Сото Хосе Грегорио") is None
