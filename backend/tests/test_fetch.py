"""Скачивание файлов расписания: robots, Crawl-delay, sha256.

Сети тут нет — транспорт подменяется. Crawl-delay проверяется через
подменяемый sleep: реально спать 30 секунд в тестах незачем.
"""

import hashlib

import pytest

from src.schedule.fetch import CRAWL_DELAY_SECONDS, Fetcher
from src.sfedu_tls import SfeduTLSAdapter


class FakeTransport:
    """Подменяемый транспорт: помнит запрошенные URL, отдаёт заготовленные тела."""

    def __init__(self, bodies=None, default=b"payload"):
        self.bodies = bodies or {}
        self.default = default
        self.urls: list[str] = []

    def __call__(self, url: str) -> bytes:
        self.urls.append(url)
        return self.bodies.get(url, self.default)


class FakeClock:
    """Монотонные часы, которые двигает только наш же sleep."""

    def __init__(self):
        self.now = 0.0
        self.slept: list[float] = []

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += seconds

    def advance(self, seconds: float) -> None:
        self.now += seconds


def make_fetcher(transport=None, clock=None):
    transport = transport or FakeTransport()
    clock = clock or FakeClock()
    return (
        Fetcher(transport=transport, sleep=clock.sleep, monotonic=clock.monotonic),
        transport,
        clock,
    )


class TestFetchDocument:
    def test_downloads_through_www_not_pls_rsu(self):
        """robots.txt запрещает /pls/rsu/ — качаем только через /www/."""
        fetcher, transport, _ = make_fetcher()
        fetcher.fetch_document("13469")
        assert transport.urls == [
            "https://sfedu.ru/www/sched_files.f_download?p_doc_id=13469"
        ]
        assert not any("/pls/rsu/" in url for url in transport.urls)

    def test_returns_content_and_sha256(self):
        transport = FakeTransport(default=b"PK\x03\x04docx-body")
        fetcher, _, _ = make_fetcher(transport)
        doc = fetcher.fetch_document("13469")
        assert doc.p_doc_id == "13469"
        assert doc.content == b"PK\x03\x04docx-body"
        assert doc.sha256 == hashlib.sha256(b"PK\x03\x04docx-body").hexdigest()
        assert doc.source_url.startswith("https://sfedu.ru/www/")

    def test_sha256_is_the_only_update_signal(self):
        """У файлов нет ни Last-Modified, ни ETag; If-Modified-Since отдаёт 200.

        Проверено на живых запросах (разведка, п.1.5). Значит, единственный
        честный признак «файл поменялся» — хэш тела.
        """
        url = "https://sfedu.ru/www/sched_files.f_download?p_doc_id=13469"
        transport = FakeTransport(bodies={url: b"v1"})
        fetcher, _, clock = make_fetcher(transport)

        first = fetcher.fetch_document("13469")
        transport.bodies[url] = b"v2"
        clock.advance(CRAWL_DELAY_SECONDS)
        second = fetcher.fetch_document("13469")

        assert first.sha256 != second.sha256
        assert second.sha256 == hashlib.sha256(b"v2").hexdigest()

    def test_same_body_same_hash(self):
        fetcher, _, clock = make_fetcher()
        first = fetcher.fetch_document("13469")
        clock.advance(CRAWL_DELAY_SECONDS)
        second = fetcher.fetch_document("13470")
        assert first.sha256 == second.sha256


class TestCrawlDelay:
    def test_crawl_delay_is_30(self):
        """robots.txt ЮФУ: Crawl-delay: 30. Мы гость на публичной странице."""
        assert CRAWL_DELAY_SECONDS == 30

    def test_first_request_does_not_sleep(self):
        fetcher, _, clock = make_fetcher()
        fetcher.fetch_document("13469")
        assert clock.slept == []

    def test_second_request_waits_full_delay(self):
        fetcher, _, clock = make_fetcher()
        fetcher.fetch_document("13469")
        fetcher.fetch_document("13470")
        assert clock.slept == [pytest.approx(30)]

    def test_delay_accounts_for_time_already_spent(self):
        """Если между запросами прошло 20 с — досыпаем 10, а не 30."""
        fetcher, _, clock = make_fetcher()
        fetcher.fetch_document("13469")
        clock.advance(20)
        fetcher.fetch_document("13470")
        assert clock.slept == [pytest.approx(10)]

    def test_no_sleep_when_delay_already_elapsed(self):
        fetcher, _, clock = make_fetcher()
        fetcher.fetch_document("13469")
        clock.advance(45)
        fetcher.fetch_document("13470")
        assert clock.slept == []

    def test_delay_applies_between_index_and_documents(self):
        """Троттлинг общий на весь фетчер: индекс — такой же запрос к сайту."""
        fetcher, _, clock = make_fetcher()
        fetcher.fetch_index()
        fetcher.fetch_document("13469")
        assert clock.slept == [pytest.approx(30)]

    def test_full_cycle_of_29_files_sleeps_28_times(self):
        """29 файлов ≈ 15 минут — нормально для суточной задачи."""
        fetcher, _, clock = make_fetcher()
        for doc_id in range(13469, 13469 + 29):
            fetcher.fetch_document(str(doc_id))
        assert len(clock.slept) == 28
        assert sum(clock.slept) == pytest.approx(28 * 30)

    def test_never_sleeps_for_real_in_tests(self):
        """Страховка: sleep инжектируется, время идёт по FakeClock."""
        fetcher, _, clock = make_fetcher()
        fetcher.fetch_document("13469")
        fetcher.fetch_document("13470")
        assert clock.now == pytest.approx(30)


class TestFetchIndex:
    def test_decodes_cp1251(self):
        """Страница отдаётся в cp1251 — байты декодируем сами."""
        html = "<div>Осенний семестр</div>".encode("cp1251")
        transport = FakeTransport(default=html)
        fetcher, _, _ = make_fetcher(transport)
        assert "Осенний семестр" in fetcher.fetch_index()

    def test_requests_index_url_without_pls_rsu(self):
        fetcher, transport, _ = make_fetcher()
        fetcher.fetch_index()
        assert len(transport.urls) == 1
        assert "/pls/rsu/" not in transport.urls[0]
        assert "p_es_id=>10000000000000" in transport.urls[0]


class TestTls:
    def test_real_session_mounts_shared_sfedu_tls_adapter(self):
        session = Fetcher()._make_session()
        assert isinstance(session.adapters["https://"], SfeduTLSAdapter)
        assert "sfedu-econ-app" in session.headers["User-Agent"]
