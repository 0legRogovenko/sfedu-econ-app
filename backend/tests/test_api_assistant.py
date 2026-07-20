from datetime import timedelta

import pytest
from sqlalchemy import func, select

from src.models import AssistantLog, Contact, KbArticle
from src.services.assistant import FALLBACK_PREFIX, AskResult


class FakeClient:
    def __init__(self, answer="Справку заказывают в деканате."):
        self.answer = answer
        self.result = None
        self.calls = []

    def ask(self, system_prompt, question):
        self.calls.append((system_prompt, question))
        if self.result is not None:
            return self.result
        return AskResult(text=self.answer, billed=True)


@pytest.fixture()
def fake_client(client):
    from src.api.assistant import get_assistant_client
    from src.main import app

    fake = FakeClient()
    app.dependency_overrides[get_assistant_client] = lambda: fake
    try:
        yield fake
    finally:
        app.dependency_overrides.pop(get_assistant_client, None)


@pytest.fixture()
def no_client(client):
    from src.api.assistant import get_assistant_client
    from src.main import app

    app.dependency_overrides[get_assistant_client] = lambda: None
    try:
        yield
    finally:
        app.dependency_overrides.pop(get_assistant_client, None)


@pytest.fixture()
def kb(db_session):
    db_session.add(
        KbArticle(slug="spravka", title="Справка", body_md="Три рабочих дня.")
    )
    db_session.add(
        Contact(
            section="Деканат",
            name="Иванова Е. П.",
            role="Декан",
            office="203",
            email="dekan.econ@sfedu.ru",
        )
    )
    db_session.flush()


def _db_now(db_session):
    # Часы считаем по БД: created_at пишется её же server_default=func.now(),
    # локальное время процесса может от них отличаться
    return db_session.scalar(select(func.now()))


def _add_logs(db_session, count, device_id="device-1", age=timedelta(0)):
    created_at = _db_now(db_session) - age
    db_session.add_all(
        [
            AssistantLog(
                question="q", answer="a", device_id=device_id, created_at=created_at
            )
            for _ in range(count)
        ]
    )
    db_session.flush()


def _ask(client, question="Как получить справку?", device_id="device-1"):
    return client.post(
        "/api/assistant/ask", json={"question": question, "device_id": device_id}
    )


def test_ask_returns_model_answer_and_logs_it(client, db_session, kb, fake_client):
    response = _ask(client)

    assert response.status_code == 200
    assert response.json() == {"answer": fake_client.answer, "fallback": False}

    logs = db_session.scalars(select(AssistantLog)).all()
    assert len(logs) == 1
    assert logs[0].question == "Как получить справку?"
    assert logs[0].answer == fake_client.answer
    assert logs[0].device_id == "device-1"


def test_ask_passes_kb_in_system_prompt(client, db_session, kb, fake_client):
    _ask(client)

    system_prompt, question = fake_client.calls[0]
    assert "Три рабочих дня." in system_prompt
    assert "Иванова Е. П." in system_prompt
    assert question == "Как получить справку?"


def test_api_failure_gives_fallback_and_does_not_burn_quota(
    client, db_session, kb, fake_client
):
    fake_client.result = AskResult(text=None, billed=False)

    response = _ask(client)

    assert response.status_code == 200
    body = response.json()
    assert body["fallback"] is True
    assert body["answer"].startswith(FALLBACK_PREFIX)
    assert "dekan.econ@sfedu.ru" in body["answer"]
    # Сбой на нашей стороне не должен съедать лимит студента
    assert db_session.scalars(select(AssistantLog)).all() == []


def test_refusal_gives_fallback_but_burns_quota(client, db_session, kb, fake_client):
    # Модель ответила отказом: вызов состоялся и оплачен, лимит обязан списаться,
    # иначе отказными вопросами можно жечь бюджет бесконечно
    fake_client.result = AskResult(text=None, billed=True)

    response = _ask(client)

    assert response.status_code == 200
    body = response.json()
    assert body["fallback"] is True
    assert body["answer"].startswith(FALLBACK_PREFIX)

    logs = db_session.scalars(select(AssistantLog)).all()
    assert len(logs) == 1
    assert logs[0].question == "Как получить справку?"
    # В логе — тот же текст, что увидел студент: лог остаётся честной историей
    assert logs[0].answer == body["answer"]


def test_empty_model_answer_gives_fallback_but_burns_quota(
    client, db_session, kb, fake_client
):
    fake_client.result = AskResult(text=None, billed=True)

    response = _ask(client, question="Пустой ответ?")

    assert response.status_code == 200
    assert response.json()["fallback"] is True
    assert len(db_session.scalars(select(AssistantLog)).all()) == 1


def test_refusals_exhaust_the_daily_limit(client, db_session, kb, fake_client):
    from src.config import settings

    fake_client.result = AskResult(text=None, billed=True)

    for _ in range(settings.assistant_daily_limit):
        assert _ask(client).status_code == 200

    assert _ask(client).status_code == 429


def test_missing_api_key_gives_fallback_not_500(client, db_session, kb, no_client):
    response = _ask(client)

    assert response.status_code == 200
    assert response.json()["fallback"] is True
    assert db_session.scalars(select(AssistantLog)).all() == []


def test_rate_limit_blocks_after_daily_limit(client, db_session, kb, fake_client):
    from src.config import settings

    _add_logs(db_session, settings.assistant_daily_limit)

    response = _ask(client)

    assert response.status_code == 429
    assert "20" in response.json()["detail"]
    assert "24 часа" in response.json()["detail"]


def test_rate_limit_detail_quotes_the_configured_limit(
    client, db_session, kb, fake_client, monkeypatch
):
    # Flutter показывает detail дословно — число в тексте должно быть настоящим
    from src.config import settings

    monkeypatch.setattr(settings, "assistant_daily_limit", 5)
    _add_logs(db_session, 5)

    response = _ask(client)

    assert response.status_code == 429
    assert "5" in response.json()["detail"]


def test_logs_older_than_24h_do_not_count(client, db_session, kb, fake_client):
    from src.config import settings

    _add_logs(db_session, settings.assistant_daily_limit, age=timedelta(days=2))

    response = _ask(client)

    assert response.status_code == 200


def test_limit_is_per_device(client, db_session, kb, fake_client):
    from src.config import settings

    _add_logs(db_session, settings.assistant_daily_limit, device_id="other-device")

    response = _ask(client, device_id="device-1")

    assert response.status_code == 200


def test_global_budget_caps_rotating_device_ids(
    client, db_session, kb, fake_client, monkeypatch
):
    # Смена device_id обходит per-device лимит, но НЕ глобальный потолок бюджета:
    # иначе безлимитная генерация новых device_id жгла бы ключ ANTHROPIC.
    from src.config import settings

    monkeypatch.setattr(settings, "assistant_global_daily_limit", 3)
    # три оплаченных вызова с РАЗНЫХ устройств — глобальный потолок достигнут
    _add_logs(db_session, 1, device_id="d-1")
    _add_logs(db_session, 1, device_id="d-2")
    _add_logs(db_session, 1, device_id="d-3")

    # свежий device_id: его per-device счётчик 0, но глобальный потолок исчерпан
    response = _ask(client, device_id="brand-new-device")

    assert response.status_code == 429
    assert "перегружен" in response.json()["detail"]
    # платного вызова не было — потолок сработал до обращения к модели
    assert fake_client.calls == []


def test_global_budget_does_not_block_under_ceiling(
    client, db_session, kb, fake_client, monkeypatch
):
    # Ниже глобального потолка обычный вопрос проходит как раньше.
    from src.config import settings

    monkeypatch.setattr(settings, "assistant_global_daily_limit", 500)
    _add_logs(db_session, 3, device_id="d-1")

    response = _ask(client, device_id="brand-new-device")

    assert response.status_code == 200


@pytest.mark.parametrize(
    "payload",
    [
        {"question": "", "device_id": "device-1"},
        {"question": "я" * 1001, "device_id": "device-1"},
        {"question": "Как получить справку?", "device_id": ""},
        {"question": "Как получить справку?"},
        {"device_id": "device-1"},
        # Пробельный ввод — это платный вызов модели ни за что
        {"question": "   ", "device_id": "device-1"},
        {"question": "\n\t ", "device_id": "device-1"},
        {"question": "Как получить справку?", "device_id": " "},
    ],
)
def test_validation_errors(client, kb, fake_client, payload):
    response = client.post("/api/assistant/ask", json=payload)

    assert response.status_code == 422


def test_question_reaches_model_trimmed(client, db_session, kb, fake_client):
    response = _ask(client, question="  Как получить справку?  ")

    assert response.status_code == 200
    _, question = fake_client.calls[0]
    assert question == "Как получить справку?"
