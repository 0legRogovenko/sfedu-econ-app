"""AI-помощник: сборка системного промпта и вызов Claude.

Вызов модели изолирован за протоколом AssistantClient — тесты ходят
на фейке, без сети и без ключа.
"""

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

import anthropic

from src.config import settings
from src.models import Contact, KbArticle

logger = logging.getLogger(__name__)

DEANERY_SECTION = "Деканат"

FALLBACK_PREFIX = "Сейчас не могу ответить. Обратитесь в деканат"

INSTRUCTION = """\
Ты — помощник экономического факультета ЮФУ. Отвечай студентам на русском \
языке, кратко и по делу.

Правила:
- Отвечай только по фактам из базы знаний и справочника контактов ниже. \
Ничего не додумывай.
- Если ответа в базе знаний нет — честно скажи об этом и отправь в деканат, \
дав его контакты из справочника.
- На вопросы, не касающиеся факультета и учёбы, вежливо откажись отвечать.

Проверка фактов и официальные источники:
- Единственный источник правды по учёбе — официальные сайты: экономический \
факультет econ-sfedu.ru и университет sfedu.ru. Доступа в интернет у тебя нет, \
поэтому не выдумывай то, чего нет в базе знаний, и не выдавай предположение за \
факт.
- Сведения, которые часто меняются (расписание, даты и время сессии, приказы, \
сроки подачи документов, состав кафедр), советуй перепроверить на официальном \
сайте или в деканате — данные в приложении могут отставать от первоисточника.
- Не придумывай ссылки. Направляй только на econ-sfedu.ru, sfedu.ru или в \
деканат из справочника.

Формат ответа:
- Пиши обычным текстом, без Markdown-разметки. Не используй ** для жирного \
шрифта, * и # для заголовков и списков: приложение показывает ответ как есть, \
и эти символы будут видны буквально.
- Если нужен список — начинай пункты с тире (—) или с «1.», «2.» и разделяй их \
переносами строк.
"""


def _contact_line(contact: Contact) -> str:
    parts = [contact.name]
    for label, value in (
        ("роль", contact.role),
        ("кабинет", contact.office),
        ("email", contact.email),
        ("телефон", contact.phone),
        ("часы приёма", contact.office_hours),
    ):
        if value:
            parts.append(f"{label}: {value}")
    return "- " + "; ".join(parts)


def build_system_prompt(
    articles: Sequence[KbArticle], contacts: Sequence[Contact]
) -> str:
    """Собирает системный промпт. Чистая функция: одинаковый вход — байт-в-байт
    одинаковый выход, иначе префиксный кэш промпта не сработает никогда.
    Поэтому здесь нет ни дат, ни id запроса, а порядок задан явной сортировкой.
    """
    blocks = [INSTRUCTION, "# База знаний"]
    for article in sorted(articles, key=lambda a: a.slug):
        blocks.append(f"## {article.title}\n{article.body_md}")

    blocks.append("# Контакты факультета")
    for contact in sorted(contacts, key=lambda c: (c.section, c.id)):
        blocks.append(f"{contact.section}\n{_contact_line(contact)}")

    return "\n\n".join(blocks)


def build_fallback_answer(contacts: Sequence[Contact]) -> str:
    """Текст отказа собирается из того же справочника, что видит студент
    на вкладке «Контакты» — чтобы не разойтись с реальными данными.
    """
    deanery = [c for c in contacts if c.section == DEANERY_SECTION]
    if not deanery:
        return f"{FALLBACK_PREFIX}."

    lines = [_contact_line(c) for c in sorted(deanery, key=lambda c: c.id)]
    return f"{FALLBACK_PREFIX}:\n" + "\n".join(lines)


@dataclass(frozen=True)
class AskResult:
    """Исход вызова модели.

    Два поля, потому что «ответа нет» бывает двух разных сортов, и путать их
    нельзя: от этого зависит, списывать ли квоту.
    text  — полезный ответ студенту или None.
    billed — вызов дошёл до модели и оплачен. Отказ и пустой ответ — тоже
    оплачены, хотя text у них None.
    """

    text: str | None
    billed: bool


class AssistantClient(Protocol):
    def ask(self, system_prompt: str, question: str) -> AskResult:
        """Результат вызова: текст ответа (если есть) и был ли вызов оплачен."""
        ...


class ClaudeClient:
    def __init__(self, api_key: str) -> None:
        # Дефолты SDK (read=600s, 2 ретрая) — это до получаса на один вопрос.
        # Ручка синхронная и занимает слот общего AnyIO-threadpool на всё это
        # время: зависший Anthropic API выел бы пул, и расписание с новостями
        # перестали бы отвечать всем. Берём 20s и один ретрай на разовый
        # сетевой сбой: худший случай — 20s × 2 попытки = ~40s, и это с запасом
        # меньше 60s, которые ждёт приложение (см. assistant_providers.dart).
        # Запас нужен, чтобы студент увидел честную заглушку, а не «нужен
        # интернет» из-за того, что клиент сдался раньше сервера.
        self._client = anthropic.Anthropic(
            api_key=api_key, timeout=20.0, max_retries=1
        )

    def ask(self, system_prompt: str, question: str) -> AskResult:
        try:
            message = self._client.messages.create(
                model=settings.assistant_model,
                max_tokens=700,
                system=[
                    {
                        "type": "text",
                        "text": system_prompt,
                        # У haiku-4-5 кэш включается только с 4096 токенов, так что
                        # пока база знаний маленькая, он тихо не срабатывает.
                        # Ставим сразу — заработает сам, когда база дорастёт.
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=[{"role": "user", "content": question}],
            )
        except (anthropic.APIStatusError, anthropic.APIConnectionError):
            # Вызова не было (или он не удался) — денег он не стоил
            logger.exception("Claude API недоступен")
            return AskResult(text=None, billed=False)

        # Дальше модель уже ответила: что бы она ни сказала, вызов оплачен
        if message.stop_reason == "refusal":
            logger.warning("Claude отказался отвечать")
            return AskResult(text=None, billed=True)

        text = next(
            (b.text for b in message.content if b.type == "text"), ""
        ).strip()
        return AskResult(text=text or None, billed=True)


def build_client() -> AssistantClient | None:
    """None = ключа нет; ручка уходит в тот же graceful-путь, что и при сбое API."""
    if not settings.anthropic_api_key:
        logger.warning("ANTHROPIC_API_KEY не задан — помощник отвечает заглушкой")
        return None
    return ClaudeClient(settings.anthropic_api_key)
