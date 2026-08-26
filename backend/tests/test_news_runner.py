from datetime import datetime

import pytest
from sqlalchemy import select

from src.models import News, NewsSource
from src.parsers.runner import run_news_parsers


def _listing_html(ids):
    items = "".join(
        f"""
        <div class="new">
          <div class="date">15 июня 2026 г.</div>
          <a href="/press-center/news/{i}">
            <span class="name">Новость {i}</span>
            <span class="prev_text">Сниппет {i}</span>
          </a>
        </div>
        """
        for i in ids
    )
    return f'<div class="news_list">{items}</div>'


def _article_html(text):
    return f'<div class="content"><p>{text}</p></div>'


def _econ_sitemap(*urls):
    items = "".join(
        f"<url><loc>{url.replace('&', '&amp;')}</loc>"
        "<lastmod>2026-08-24T23:08:46+00:00</lastmod></url>"
        for url in urls
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f"{items}</urlset>"
    )


def _econ_article_html(title, body):
    return f"""
      <article class="item-page">
        <h1 itemprop="headline">{title}</h1>
        <time datetime="2026-06-10T09:00:00+03:00">10 июня 2026</time>
        <div itemprop="articleBody"><p>{body}</p></div>
        <img itemprop="image" src="/images/news/prize.jpg">
      </article>
    """


class FakeFetch:
    """Отдаёт html по url; для указанных url — бросает исключение."""

    def __init__(self, pages, raise_for=None):
        self.pages = pages
        self.raise_for = raise_for or set()
        self.calls = []

    def __call__(self, url):
        self.calls.append(url)
        if url in self.raise_for:
            raise RuntimeError(f"network down for {url}")
        # Старые тесты изолируют sfedu-ветку. Новый источник всё равно должен
        # пройти цикл, поэтому по умолчанию получает честный пустой sitemap.
        if url == "https://econ-sfedu.ru/sitemap.xml" and url not in self.pages:
            return _econ_sitemap()
        return self.pages[url]


@pytest.fixture()
def session_factory(db_session):
    # runner ожидает фабрику сессий; отдаём одну и ту же тестовую сессию
    return lambda: db_session


def test_inserts_new_candidates(db_session, session_factory):
    from src.parsers.sfedu_news import LISTING_URL

    fetch = FakeFetch(
        {
            LISTING_URL: _listing_html([1, 2]),
            "https://sfedu.ru/press-center/news/1": _article_html("Полный текст 1"),
            "https://sfedu.ru/press-center/news/2": _article_html("Полный текст 2"),
        }
    )

    result = run_news_parsers(session_factory=session_factory, fetch=fetch)

    assert result == {"sfedu": {"new": 2}, "econ": {"new": 0}}
    rows = db_session.scalars(select(News).order_by(News.url)).all()
    assert len(rows) == 2
    assert all(r.source == NewsSource.SFEDU for r in rows)
    first = next(r for r in rows if r.url.endswith("/1"))
    assert first.title == "Новость 1"
    assert first.body == "Полный текст 1"
    assert first.published_at == datetime(2026, 6, 15)


def test_second_run_deduplicates(db_session, session_factory):
    from src.parsers.sfedu_news import LISTING_URL

    pages = {
        LISTING_URL: _listing_html([1]),
        "https://sfedu.ru/press-center/news/1": _article_html("Текст 1"),
    }
    run_news_parsers(session_factory=session_factory, fetch=FakeFetch(pages))
    result = run_news_parsers(session_factory=session_factory, fetch=FakeFetch(pages))

    assert result == {"sfedu": {"new": 0}, "econ": {"new": 0}}
    assert len(db_session.scalars(select(News)).all()) == 1


def test_listing_fetch_failure_isolated(db_session, session_factory):
    from src.parsers.sfedu_news import LISTING_URL

    # заранее положим одну новость (закоммичена, как в проде) — не должна пострадать
    db_session.add(
        News(
            title="Старая",
            body="текст",
            source=NewsSource.SFEDU,
            url="https://sfedu.ru/press-center/news/999",
            published_at=datetime(2026, 1, 1),
        )
    )
    db_session.commit()

    fetch = FakeFetch({}, raise_for={LISTING_URL})
    result = run_news_parsers(session_factory=session_factory, fetch=fetch)

    assert "error" in result["sfedu"]
    assert len(db_session.scalars(select(News)).all()) == 1  # не тронуто


def test_article_fetch_failure_falls_back_to_snippet(db_session, session_factory):
    from src.parsers.sfedu_news import LISTING_URL

    fetch = FakeFetch(
        {LISTING_URL: _listing_html([1])},
        raise_for={"https://sfedu.ru/press-center/news/1"},
    )

    result = run_news_parsers(session_factory=session_factory, fetch=fetch)

    assert result == {"sfedu": {"new": 1}, "econ": {"new": 0}}
    row = db_session.scalars(select(News)).one()
    assert row.body == "Сниппет 1"  # тело из сниппета листинга


def test_alert_sent_on_source_failure(db_session, session_factory, monkeypatch):
    from src.parsers import runner
    from src.parsers.sfedu_news import LISTING_URL

    calls = []
    monkeypatch.setattr(runner, "notify_admin", lambda text: calls.append(text))

    fetch = FakeFetch({}, raise_for={LISTING_URL})
    run_news_parsers(session_factory=session_factory, fetch=fetch)

    assert calls and "sfedu" in calls[0].lower()


def test_alert_on_empty_listing_parse(db_session, session_factory, monkeypatch):
    # листинг скачался, но 0 элементов распарсилось -> вероятно, сменилась
    # вёрстка: алерт, но не ошибка (данные не тронуты)
    from src.parsers import runner
    from src.parsers.sfedu_news import LISTING_URL

    calls = []
    monkeypatch.setattr(runner, "notify_admin", lambda text: calls.append(text))

    fetch = FakeFetch({LISTING_URL: "<html><body>нет новостей</body></html>"})
    result = run_news_parsers(session_factory=session_factory, fetch=fetch)

    assert result == {"sfedu": {"new": 0}, "econ": {"new": 0}}
    assert calls and "вёрстк" in calls[0].lower() or "разметк" in calls[0].lower()


def test_imports_faculty_news_from_official_sitemap(db_session, session_factory):
    """Главная econ-sfedu.ru может падать, но статический sitemap доступен."""
    from src.parsers.sfedu_news import LISTING_URL

    sitemap_url = "https://econ-sfedu.ru/sitemap.xml"
    article_url = (
        "https://econ-sfedu.ru/component/content/article/"
        "317-dotsent-ekonoma-prizer-konkursa.html?catid=15&Itemid=101"
    )
    conference_url = (
        "https://econ-sfedu.ru/component/content/article/"
        "297-vseros-2026.html?catid=19&Itemid=101"
    )
    fetch = FakeFetch(
        {
            LISTING_URL: "<div class='news_list'></div>",
            sitemap_url: _econ_sitemap(article_url, conference_url),
            article_url: _econ_article_html(
                "Доцент Эконома — призер конкурса", "Полный текст факультета"
            ),
        }
    )

    result = run_news_parsers(session_factory=session_factory, fetch=fetch)

    assert result == {"sfedu": {"new": 0}, "econ": {"new": 1}}
    row = db_session.scalar(select(News).where(News.source == NewsSource.ECON))
    assert row is not None
    assert row.title == "Доцент Эконома — призер конкурса"
    assert row.body == "Полный текст факультета"
    assert row.published_at == datetime(2026, 6, 10, 6, 0)
    assert row.image_url == "https://econ-sfedu.ru/images/news/prize.jpg"
    assert conference_url not in fetch.calls  # catid=19 — не лента новостей


def test_faculty_news_survives_temporary_article_outage(db_session, session_factory):
    """Текущий PHP fatal не должен оставлять факультетскую ленту пустой."""
    from src.parsers.sfedu_news import LISTING_URL

    sitemap_url = "https://econ-sfedu.ru/sitemap.xml"
    article_url = (
        "https://econ-sfedu.ru/component/content/article/"
        "317-dotsent-ekonoma-prizer-konkursa.html?catid=15&Itemid=101"
    )
    fetch = FakeFetch(
        {
            LISTING_URL: "<div class='news_list'></div>",
            sitemap_url: _econ_sitemap(article_url),
        },
        raise_for={article_url},
    )

    result = run_news_parsers(session_factory=session_factory, fetch=fetch)

    assert result["econ"] == {"new": 1}
    row = db_session.scalar(select(News).where(News.source == NewsSource.ECON))
    assert row is not None
    assert row.title == "Доцент Эконома призер конкурса"
    assert row.body == row.title
    assert row.published_at == datetime(2026, 8, 24, 23, 8, 46)


def test_faculty_news_second_run_deduplicates(db_session, session_factory):
    from src.parsers.sfedu_news import LISTING_URL

    sitemap_url = "https://econ-sfedu.ru/sitemap.xml"
    article_url = (
        "https://econ-sfedu.ru/component/content/article/"
        "317-dotsent-ekonoma-prizer-konkursa.html?catid=15&Itemid=101"
    )
    pages = {
        LISTING_URL: "<div class='news_list'></div>",
        sitemap_url: _econ_sitemap(article_url),
        article_url: _econ_article_html("Новость Эконома", "Текст"),
    }

    run_news_parsers(session_factory=session_factory, fetch=FakeFetch(pages))
    result = run_news_parsers(session_factory=session_factory, fetch=FakeFetch(pages))

    assert result["econ"] == {"new": 0}
    assert len(
        db_session.scalars(select(News).where(News.source == NewsSource.ECON)).all()
    ) == 1
