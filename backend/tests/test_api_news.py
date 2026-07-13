from datetime import datetime, timedelta

from src.models import News, NewsSource


def _add_news(db_session, count: int):
    base = datetime(2026, 7, 13, 12, 0)
    for i in range(count):
        db_session.add(
            News(
                title=f"Новость {i}",
                body="Текст",
                source=NewsSource.SFEDU,
                url=f"https://sfedu.ru/news/{i}",
                published_at=base - timedelta(hours=i),
            )
        )
    db_session.flush()


def test_news_sorted_desc_default_limit(client, db_session):
    _add_news(db_session, 25)

    response = client.get("/api/news")

    assert response.status_code == 200
    items = response.json()
    assert len(items) == 20  # дефолтный лимит
    assert items[0]["title"] == "Новость 0"  # самая свежая
    assert items[0]["source"] == "sfedu"


def test_news_before_pagination(client, db_session):
    _add_news(db_session, 25)

    first_page = client.get("/api/news?limit=10").json()
    last = first_page[-1]

    second_page = client.get(
        f"/api/news?before={last['published_at']}&before_id={last['id']}&limit=10"
    ).json()

    assert len(second_page) == 10
    assert second_page[0]["title"] == "Новость 10"
    first_ids = {n["id"] for n in first_page}
    assert first_ids.isdisjoint({n["id"] for n in second_page})


def test_news_tied_timestamps_not_skipped(client, db_session):
    # Три новости с одинаковым published_at — курсор по паре (дата, id)
    # не должен терять записи
    ts = datetime(2026, 7, 13, 12, 0)
    for i in range(3):
        db_session.add(
            News(
                title=f"Одновременная {i}",
                body="Текст",
                source=NewsSource.SFEDU,
                url=f"https://sfedu.ru/news/tied-{i}",
                published_at=ts,
            )
        )
    db_session.flush()

    first_page = client.get("/api/news?limit=2").json()
    last = first_page[-1]
    second_page = client.get(
        f"/api/news?before={last['published_at']}&before_id={last['id']}&limit=2"
    ).json()

    seen = {n["id"] for n in first_page} | {n["id"] for n in second_page}
    assert len(seen) == 3  # ничего не потеряно и не задублировано


def test_news_lone_cursor_param_rejected(client):
    assert client.get("/api/news?before=2026-07-13T12:00:00").status_code == 422
    assert client.get("/api/news?before_id=1").status_code == 422


def test_news_limit_bounds(client):
    assert client.get("/api/news?limit=0").status_code == 422
    assert client.get("/api/news?limit=51").status_code == 422


def test_news_etag_304(client, db_session):
    _add_news(db_session, 3)

    first = client.get("/api/news")
    second = client.get(
        "/api/news", headers={"If-None-Match": first.headers["etag"]}
    )
    assert second.status_code == 304
