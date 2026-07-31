"""帖子 CRUD / 搜索 / 批量删除 API 回归。"""

from __future__ import annotations


def test_health_ready(client):
    r = client.get("/api/v1/health/ready")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert "readiness" in body["data"]


def test_create_post_sets_sentiment_score(client):
    r = client.post(
        "/api/v1/posts",
        json={
            "text": "手工入库负面评论差评",
            "platform": "bili",
            "topic": "测试",
            "sentiment_label": "negative",
            "bvid": "BV1TestCreate001",
            "video_title": "测试视频",
        },
    )
    assert r.status_code == 201, r.text
    data = r.json()["data"]
    assert data["sentiment_label"] == "negative"
    assert data["sentiment_method"] == "manual"
    assert data["sentiment"] == -1
    assert data["sentiment_confidence"] == 1.0
    assert (data.get("raw") or {}).get("extra", {}).get("bvid") == "BV1TestCreate001"


def test_create_post_rejects_bad_label(client):
    r = client.post(
        "/api/v1/posts",
        json={"text": "x", "sentiment_label": "happy"},
    )
    assert r.status_code == 400
    assert r.json()["ok"] is False


def test_list_posts_search_q(client, store):
    store.create_post(text="食堂排队太久了", topic="食堂", author="甲")
    store.create_post(text="图书馆很安静", topic="图书馆", author="乙")
    store.create_post(text="含%百分号字面", topic="杂项", author="丙")

    r = client.get("/api/v1/posts", params={"q": "食堂"})
    assert r.status_code == 200
    body = r.json()["data"]
    assert body["total"] == 1
    assert body["count"] == 1
    assert "食堂" in body["items"][0]["text"]
    assert body["q"] == "食堂"

    # % 不得当成「匹配任意」通配符
    r = client.get("/api/v1/posts", params={"q": "%"})
    assert r.status_code == 200
    assert r.json()["data"]["total"] == 1
    assert "%" in r.json()["data"]["items"][0]["text"]


def test_get_update_delete_post(client):
    created = client.post(
        "/api/v1/posts",
        json={"text": "原始正文", "platform": "campus", "topic": "综合"},
    ).json()["data"]
    pid = created["id"]

    r = client.get(f"/api/v1/posts/{pid}")
    assert r.status_code == 200
    assert r.json()["data"]["text"] == "原始正文"

    r = client.patch(
        f"/api/v1/posts/{pid}",
        json={"text": "已修改", "clear_topic": True, "bvid": "BV1Upd0001"},
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["text"] == "已修改"
    assert data["topic"] is None
    assert data["raw"]["extra"]["bvid"] == "BV1Upd0001"

    r = client.delete(f"/api/v1/posts/{pid}")
    assert r.status_code == 200
    assert client.get(f"/api/v1/posts/{pid}").status_code == 404


def test_delete_posts_by_ids(client, store):
    a = store.create_post(text="删我1")
    b = store.create_post(text="删我2")
    keep = store.create_post(text="留下")

    r = client.post(
        "/api/v1/posts/delete",
        json={"ids": [a["id"], b["id"]], "dry_run": True},
    )
    assert r.status_code == 200
    assert r.json()["data"]["matched"] == 2
    assert r.json()["data"]["deleted"] == 0
    assert store.count_posts() == 3

    r = client.post("/api/v1/posts/delete", json={"ids": [a["id"], b["id"]]})
    assert r.status_code == 200
    assert r.json()["data"]["deleted"] == 2
    assert store.count_posts() == 1
    assert store.get_post(keep["id"]) is not None


def test_delete_requires_filter(client):
    r = client.post("/api/v1/posts/delete", json={})
    assert r.status_code == 400


def test_posts_review_not_captured_by_id_route(client):
    """确保 /posts/review 不会被 /posts/{post_id} 抢走。"""
    r = client.get("/api/v1/posts/review", params={"limit": 5})
    assert r.status_code == 200
    assert r.json()["ok"] is True
    assert "items" in r.json()["data"]


def test_dashboard_overview_empty(client):
    r = client.get("/api/v1/dashboard/overview")
    assert r.status_code == 200
    assert r.json()["data"]["total_posts"] == 0
