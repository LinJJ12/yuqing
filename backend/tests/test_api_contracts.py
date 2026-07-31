"""导入 / 预警 / 报告 / analysis-jobs API 回归（无 GPU、无外网）。"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path


def _bili_post(store, *, source_id: str, text: str, label: str, method: str, bvid: str):
    score = {"positive": 1, "neutral": 0, "negative": -1, "uncertain": 0}[label]
    store.insert_posts(
        "job-api",
        [
            {
                "platform": "bili",
                "source_id": source_id,
                "author": "u",
                "text": text,
                "published_at": None,
                "fetched_at": "2026-07-31T00:00:00+00:00",
                "source_url": f"https://www.bilibili.com/video/{bvid}",
                "topic": "综合",
                "sentiment": score,
                "sentiment_label": label,
                "sentiment_method": method,
                "sentiment_confidence": 0.9,
                "engagement": {},
                "raw": {"extra": {"bvid": bvid, "video_title": "对比测试视频"}},
            }
        ],
    )


def test_import_json_and_list(client):
    sample = [
        {"id": "imp-a", "text": "教务系统崩溃，非常不满", "topic": "教务"},
        {"id": "imp-b", "text": "奖学金政策很给力", "topic": "奖学金"},
    ]
    with tempfile.NamedTemporaryFile(
        "w", suffix=".json", delete=False, encoding="utf-8"
    ) as f:
        json.dump(sample, f, ensure_ascii=False)
        path = f.name
    try:
        with open(path, "rb") as fh:
            r = client.post(
                "/api/v1/imports",
                files={"file": ("t.json", fh, "application/json")},
                data={"topic": "文件导入", "platform": "campus"},
            )
    finally:
        Path(path).unlink(missing_ok=True)

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["data"]["stats"]["inserted"] >= 1
    job_id = body["data"]["id"]

    r = client.get("/api/v1/imports")
    assert r.status_code == 200
    assert any(j["id"] == job_id for j in r.json()["data"])

    r = client.get(f"/api/v1/imports/{job_id}")
    assert r.status_code == 200
    assert r.json()["data"]["id"] == job_id


def test_import_missing_file(client):
    r = client.post("/api/v1/imports", data={"topic": "x"})
    assert r.status_code in (400, 422)


def test_alert_keywords_roundtrip(client):
    r = client.get("/api/v1/settings/alert-keywords")
    assert r.status_code == 200
    assert isinstance(r.json()["data"]["keywords"], list)

    r = client.put(
        "/api/v1/settings/alert-keywords",
        json={"keywords": ["投诉", "差评", "pytest词"]},
    )
    assert r.status_code == 200
    assert "pytest词" in r.json()["data"]["keywords"]

    r = client.get("/api/v1/settings/alert-keywords")
    assert "pytest词" in r.json()["data"]["keywords"]


def test_alerts_and_trends_scope(client, store):
    _bili_post(
        store,
        source_id="alert-neg-1",
        text="太差了垃圾翻车劝退",
        label="negative",
        method="bert",
        bvid="BV1AlertScope01",
    )
    r = client.get("/api/v1/alerts", params={"bvid": "BV1AlertScope01"})
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["bvid"] == "BV1AlertScope01"
    assert isinstance(data["items"], list)
    assert any(a.get("type") == "negative_content" for a in data["items"])

    r = client.get(
        "/api/v1/trends",
        params={"days": 14, "use_prophet": False, "bvid": "BV1AlertScope01"},
    )
    assert r.status_code == 200
    assert isinstance(r.json()["data"]["series"], list)


def test_sentiment_override_clears_alert(client, store):
    _bili_post(
        store,
        source_id="alert-override-1",
        text="太差了垃圾翻车",
        label="negative",
        method="bert",
        bvid="BV1OvRide01",
    )
    pid = next(
        p["id"]
        for p in store.list_posts(limit=50)
        if p.get("source_id") == "alert-override-1"
    )
    before = client.get("/api/v1/alerts").json()["data"]["items"]
    assert any(a.get("post_id") == pid for a in before)

    r = client.patch(
        f"/api/v1/posts/{pid}/sentiment",
        json={"label": "positive", "method": "manual", "confidence": 1},
    )
    assert r.status_code == 200
    after = client.get("/api/v1/alerts").json()["data"]["items"]
    assert not any(a.get("post_id") == pid for a in after)


def test_video_report_and_list(client, store):
    bvid = "BV1VideoRep001"
    for i, (lab, txt) in enumerate(
        [
            ("negative", "差评离谱失望"),
            ("positive", "好看推荐满意"),
            ("neutral", "一般看看就行"),
        ]
    ):
        _bili_post(
            store,
            source_id=f"vr-{i}",
            text=txt,
            label=lab,
            method="lexicon",
            bvid=bvid,
        )

    r = client.get("/api/v1/reports/videos")
    assert r.status_code == 200
    items = r.json()["data"]["items"]
    assert any(v.get("bvid") == bvid for v in items)

    r = client.get("/api/v1/reports/video", params={"bvid": bvid})
    assert r.status_code == 200
    overview = r.json()["data"]["overview"]
    assert overview["total_posts"] == 3


def test_reports_summary_and_exports(client, store):
    store.create_post(text="导出用帖子", platform="campus", topic="综合")
    r = client.get("/api/v1/reports/summary")
    assert r.status_code == 200
    assert r.json()["ok"] is True
    assert "overview" in r.json()["data"]

    r = client.get("/api/v1/reports/export.csv")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert len(r.content) > 0

    r = client.get("/api/v1/reports/export.pdf")
    assert r.status_code == 200
    assert r.content[:4] == b"%PDF"


def test_analysis_job_create_and_get(client, store, monkeypatch):
    # 不真正跑后台推理，只验证入队与查询契约
    import src.services.jobs as jobs

    monkeypatch.setattr(jobs._executor, "submit", lambda *a, **k: None)
    store.create_post(text="待分析帖子内容足够长一点")
    r = client.post(
        "/api/v1/analysis-jobs",
        json={"kind": "sentiment", "limit": 10, "only_pending": True},
    )
    assert r.status_code == 200, r.text
    assert r.json()["ok"] is True
    job_id = r.json()["data"]["id"]
    assert r.json()["data"]["status"] in {"queued", "running", "succeeded", "failed"}

    r = client.get(f"/api/v1/analysis-jobs/{job_id}")
    assert r.status_code == 200
    assert r.json()["data"]["id"] == job_id

    r = client.get("/api/v1/analysis-jobs", params={"limit": 5})
    assert r.status_code == 200
    assert any(j["id"] == job_id for j in r.json()["data"]["items"])


def test_topics_words_and_tfidf(client, store):
    for i in range(6):
        store.create_post(text=f"剪辑节奏不错推荐给力好看第{i}条评论内容")
    r = client.get("/api/v1/analysis/topics/words")
    assert r.status_code == 200
    assert r.json()["ok"] is True

    r = client.post(
        "/api/v1/analysis/topics/run",
        json={"limit": 50, "use_bertopic": False},
    )
    assert r.status_code == 200, r.text
    assert r.json()["ok"] is True
    assert "word_cloud" in r.json()["data"] or "keywords" in r.json()["data"]


def test_agent_status(client):
    r = client.get("/api/v1/agent/status")
    assert r.status_code == 200
    assert "ready" in r.json()["data"]
