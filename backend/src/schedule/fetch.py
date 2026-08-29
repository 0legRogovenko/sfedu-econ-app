"""Скачивание индексной страницы и файлов расписания.

Три вещи, ради которых этот модуль существует отдельно:

* качаем только через /www/ (см. source.download_url) — /pls/rsu/ запрещён robots.txt;
* соблюдаем Crawl-delay: 30 между любыми запросами к сайту;
* считаем sha256 тела — единственный признак того, что файл обновился.

Про sha256 (проверено живыми запросами, разведка п.1.5): у файлов нет ни
Last-Modified, ни ETag, а If-Modified-Since отдаёт 200 с полным телом. Дешёвого
условного запроса не существует — только скачать и сравнить хэш.
"""

from __future__ import annotations

import hashlib
import time
from collections.abc import Callable
from dataclasses import dataclass

import requests

from src.schedule.source import INDEX_URL, download_url
from src.sfedu_tls import SfeduTLSAdapter

# robots.txt ЮФУ. Полный цикл 29 файлов ≈ 15 минут — нормально для суточной задачи.
CRAWL_DELAY_SECONDS = 30

_INDEX_ENCODING = "cp1251"


@dataclass(frozen=True)
class FetchedDocument:
    p_doc_id: str
    content: bytes
    sha256: str
    source_url: str


class Fetcher:
    """Троттлящий загрузчик. Один экземпляр на цикл импорта.

    `transport`, `sleep` и `monotonic` инжектируются: в тестах сети нет и спать
    по-настоящему 30 секунд незачем.
    """

    def __init__(
        self,
        transport: Callable[[str], bytes] | None = None,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
        crawl_delay: float = CRAWL_DELAY_SECONDS,
    ) -> None:
        self._transport = transport or self._default_transport
        self._sleep = sleep
        self._monotonic = monotonic
        self._crawl_delay = crawl_delay
        self._last_request_at: float | None = None
        self._session: requests.Session | None = None

    def fetch_index(self) -> str:
        return self._get(INDEX_URL).decode(_INDEX_ENCODING)

    def fetch_document(self, p_doc_id: str | int) -> FetchedDocument:
        url = download_url(p_doc_id)
        content = self._get(url)
        return FetchedDocument(
            p_doc_id=str(p_doc_id),
            content=content,
            sha256=hashlib.sha256(content).hexdigest(),
            source_url=url,
        )

    def _get(self, url: str) -> bytes:
        self._throttle()
        return self._transport(url)

    def _throttle(self) -> None:
        """Ждёт остаток Crawl-delay с прошлого запроса. Первый запрос не ждёт."""
        if self._last_request_at is not None:
            remaining = self._crawl_delay - (self._monotonic() - self._last_request_at)
            if remaining > 0:
                self._sleep(remaining)
        self._last_request_at = self._monotonic()

    def _make_session(self) -> requests.Session:
        session = requests.Session()
        session.mount("https://", SfeduTLSAdapter())
        session.headers["User-Agent"] = "sfedu-econ-app/1.0 (schedule importer)"
        return session

    def _default_transport(self, url: str) -> bytes:
        if self._session is None:
            self._session = self._make_session()
        response = self._session.get(url, timeout=30)
        response.raise_for_status()
        return response.content
