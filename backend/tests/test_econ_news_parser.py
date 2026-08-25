import requests
import time as time_module

from src.parsers import econ_news, sfedu_news
from src.parsers.econ_news import parse_sitemap


def _sitemap(*urls: str) -> str:
    rows = "".join(
        f"<url><loc>{url.replace('&', '&amp;')}</loc>"
        "<lastmod>2026-08-24T23:08:46+00:00</lastmod></url>"
        for url in urls
    )
    return (
        '<?xml version="1.0"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f"{rows}</urlset>"
    )


def test_sitemap_fallback_titles_are_readable_during_article_outage():
    base = "https://econ-sfedu.ru/component/content/article/"
    rows = parse_sitemap(
        _sitemap(
            base
            + "328-poryadok-postupleniya-na-sluzhbu-po-spetsialnomu-kontraktu.html"
            "?catid=15&Itemid=101",
            base
            + "324-the-faculty-of-economics-will-host-another-meeting.html"
            "?catid=15&Itemid=101",
            base
            + "319-molodye-uchjonye-ekonoma-yufu-uchastniki-molodjozhnogo-dnya-"
            "pmef-2026.html?catid=15&Itemid=101",
            base
            + "318-den-otkrytykh-dverej-ekonoma-yufu-20-iyunya.html"
            "?catid=15&Itemid=101",
        )
    )

    assert [row.title for row in rows] == [
        "Порядок поступления на службу по специальному контракту",
        "The faculty of economics will host another meeting",
        "Молодые учёные Эконома ЮФУ — участники молодёжного дня ПМЭФ 2026",
        "День открытых дверей Эконома ЮФУ 20 июня",
    ]


def test_default_fetch_retries_a_transient_timeout(monkeypatch):
    class Response:
        text = "<urlset/>"

        @staticmethod
        def raise_for_status():
            return None

    class Session:
        def __init__(self):
            self.calls = 0

        def get(self, _url, timeout):
            assert timeout == 15
            self.calls += 1
            if self.calls == 1:
                raise requests.Timeout("temporary TLS timeout")
            return Response()

    session = Session()
    monkeypatch.setattr(sfedu_news, "_make_session", lambda: session)
    monkeypatch.setattr(time_module, "sleep", lambda _seconds: None)

    assert econ_news.default_fetch(econ_news.SITEMAP_URL) == "<urlset/>"
    assert session.calls == 2
