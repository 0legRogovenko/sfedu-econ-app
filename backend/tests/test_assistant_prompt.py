from src.models import Contact, KbArticle
from src.services.assistant import build_system_prompt


def _articles():
    return [
        KbArticle(slug="stipendiya", title="Стипендия", body_md="Выплата 25 числа."),
        KbArticle(slug="peresdacha", title="Пересдача", body_md="Две попытки."),
        KbArticle(slug="spravka", title="Справка", body_md="Три рабочих дня."),
    ]


def _contacts():
    return [
        Contact(
            id=2,
            section="Деканат",
            name="Сидорова О. Н.",
            role="Методист",
            office="204",
            office_hours="Пн–Пт 9:00–17:00",
        ),
        Contact(
            id=1,
            section="Деканат",
            name="Иванова Е. П.",
            role="Декан",
            office="203",
            email="dekan.econ@sfedu.ru",
            phone="+7 863 000-00-00",
        ),
    ]


def test_prompt_contains_articles():
    prompt = build_system_prompt(_articles(), _contacts())

    for article in _articles():
        assert article.title in prompt
        assert article.body_md in prompt


def test_prompt_contains_contacts():
    prompt = build_system_prompt(_articles(), _contacts())

    assert "Иванова Е. П." in prompt
    assert "Декан" in prompt
    assert "dekan.econ@sfedu.ru" in prompt
    assert "+7 863 000-00-00" in prompt
    assert "204" in prompt
    assert "Пн–Пт 9:00–17:00" in prompt


def test_articles_sorted_by_slug_not_by_input_order():
    prompt = build_system_prompt(_articles(), _contacts())

    assert (
        prompt.index("Пересдача") < prompt.index("Справка") < prompt.index("Стипендия")
    )


def test_contacts_sorted_by_section_and_id():
    prompt = build_system_prompt(_articles(), _contacts())

    assert prompt.index("Иванова Е. П.") < prompt.index("Сидорова О. Н.")


def test_prompt_is_byte_stable():
    # Промпт кэшируется по префиксному совпадению: любая нестабильность
    # (дата, id запроса, порядок словаря) убивает кэш
    first = build_system_prompt(_articles(), _contacts())
    second = build_system_prompt(_articles(), _contacts())

    assert first == second


def test_prompt_has_instruction():
    prompt = build_system_prompt(_articles(), _contacts())

    assert "русском" in prompt
    assert "базы знаний" in prompt
    assert "деканат" in prompt.lower()


def test_prompt_forbids_markdown_formatting():
    # Приложение показывает ответ обычным Text — Markdown-разметка была бы видна
    # буквально (** вместо жирного).
    prompt = build_system_prompt(_articles(), _contacts())

    assert "Markdown" in prompt
    assert "**" in prompt  # явно называем символ, который нельзя использовать


def test_prompt_points_to_official_sources():
    prompt = build_system_prompt(_articles(), _contacts())

    assert "econ-sfedu.ru" in prompt
    assert "sfedu.ru" in prompt
