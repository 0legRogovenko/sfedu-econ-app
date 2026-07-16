"""Тесты на сам ClaudeClient: messages.create подменён, сети и ключа нет."""

import anthropic
import httpx
import pytest

from src.config import settings
from src.services.assistant import AskResult, ClaudeClient, build_client


class FakeBlock:
    def __init__(self, type_, text=""):
        self.type = type_
        self.text = text


class FakeMessage:
    def __init__(self, content, stop_reason="end_turn"):
        self.content = content
        self.stop_reason = stop_reason


class FakeMessages:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        if self.error is not None:
            raise self.error
        return self.result


def make_client(result=None, error=None):
    """Реальный ClaudeClient с подменённым messages — сам объект anthropic.Anthropic
    остаётся настоящим, поэтому его настройки (timeout/retries) проверяемы.
    """
    if result is None and error is None:
        result = FakeMessage([FakeBlock("text", "Ответ модели.")])
    client = ClaudeClient("test-key")
    fake = FakeMessages(result=result, error=error)
    client._client.messages = fake
    return client, fake


@pytest.fixture(autouse=True)
def _clear_client_cache():
    from src.api.assistant import get_assistant_client

    get_assistant_client.cache_clear()
    yield
    get_assistant_client.cache_clear()


def test_ask_returns_text_and_passes_question():
    client, fake = make_client()

    result = client.ask("system", "Как получить справку?")

    assert result == AskResult(text="Ответ модели.", billed=True)
    assert fake.kwargs["messages"] == [
        {"role": "user", "content": "Как получить справку?"}
    ]


def test_ask_marks_system_prompt_for_prompt_caching():
    client, fake = make_client()

    client.ask("system prompt", "q")

    system = fake.kwargs["system"]
    assert system[0]["text"] == "system prompt"
    assert system[0]["cache_control"] == {"type": "ephemeral"}


def test_ask_uses_model_from_settings(monkeypatch):
    monkeypatch.setattr(settings, "assistant_model", "claude-test-model")
    client, fake = make_client()

    client.ask("system", "q")

    assert fake.kwargs["model"] == "claude-test-model"


def test_ask_caps_max_tokens():
    client, fake = make_client()

    client.ask("system", "q")

    assert fake.kwargs["max_tokens"] == 700


def test_ask_reports_refusal_as_billed_without_text():
    # Модель ответила — вызов оплачен, даже если ответ бесполезен
    client, _ = make_client(
        result=FakeMessage([FakeBlock("text", "Не буду.")], stop_reason="refusal")
    )

    assert client.ask("system", "q") == AskResult(text=None, billed=True)


def test_ask_reports_empty_content_as_billed_without_text():
    client, _ = make_client(result=FakeMessage([]))

    assert client.ask("system", "q") == AskResult(text=None, billed=True)


def test_ask_reports_missing_text_block_as_billed():
    client, _ = make_client(result=FakeMessage([FakeBlock("thinking")]))

    assert client.ask("system", "q") == AskResult(text=None, billed=True)


def test_ask_reports_api_status_error_as_unbilled():
    error = anthropic.APIStatusError(
        "boom",
        response=httpx.Response(500, request=httpx.Request("POST", "http://api")),
        body=None,
    )
    client, _ = make_client(error=error)

    assert client.ask("system", "q") == AskResult(text=None, billed=False)


def test_ask_reports_connection_error_as_unbilled():
    error = anthropic.APIConnectionError(request=httpx.Request("POST", "http://api"))
    client, _ = make_client(error=error)

    assert client.ask("system", "q") == AskResult(text=None, billed=False)


def test_client_bounds_wait_time_for_the_app():
    # Ручка синхронная и живёт в общем AnyIO-threadpool: без явного лимита
    # зависший Anthropic API выедает все слоты и роняет расписание с новостями.
    # 20s × (1 попытка + 1 ретрай) = ~40s худший случай — с запасом меньше
    # 60s, которые ждёт приложение, иначе клиент сдастся раньше нас
    client = ClaudeClient("test-key")

    assert client._client.timeout == 20.0
    assert client._client.max_retries == 1


def test_build_client_without_key_returns_none(monkeypatch):
    monkeypatch.setattr(settings, "anthropic_api_key", None)

    assert build_client() is None


def test_build_client_with_key_returns_claude_client(monkeypatch):
    monkeypatch.setattr(settings, "anthropic_api_key", "test-key")

    assert isinstance(build_client(), ClaudeClient)
