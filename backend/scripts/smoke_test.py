"""回归探测：导入、API、情感三类、Ollama 嵌入连通。"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from fastapi.testclient import TestClient

from src.api.app import app
from src.config.device import get_device_info
from src.config.settings import DATA_DIR, settings
from src.services.normalize import lexicon_sentiment, normalize_post
from src.services.ollama_embed import OllamaEmbedder
from src.storage.db import Store


def check(name: str, cond: bool, detail: str = "") -> None:
    status = "PASS" if cond else "FAIL"
    print(f"[{status}] {name}" + (f" — {detail}" if detail else ""))
    if not cond:
        raise AssertionError(name)


def main() -> None:
    # 隔离测试库，避免污染开发库
    tmp = tempfile.TemporaryDirectory()
    db_path = Path(tmp.name) / "test.db"
    store = Store(str(db_path))
    store.initialize()

    # 规范化 + 三类情感词典
    pos = normalize_post({"id": "1", "text": "食堂很好吃，非常满意推荐"})
    neg = normalize_post({"id": "2", "text": "宿舍热水故障，差评投诉"})
    neu = normalize_post({"id": "3", "text": "图书馆今天开到九点"})
    check("normalize positive", pos["sentiment_label"] == "positive", str(pos))
    check("normalize negative", neg["sentiment_label"] == "negative", str(neg))
    check("lexicon returns triple", lexicon_sentiment("一般情况")[1] in {"positive", "neutral", "negative"})
    check("infer_topic fallback", normalize_post({"id": "4", "text": "今天天气不错"})["topic"] == "综合")

    from src.services.bilibili_collect import resolve_collect_topic

    check(
        "collect topic bv title",
        resolve_collect_topic(topic=None, keyword=None, video_titles=["一口气看完测试视频"])
        == "一口气看完测试视频",
    )
    check(
        "collect topic keyword wins",
        resolve_collect_topic(topic=None, keyword="数码评测", video_titles=["某视频标题"])
        == "数码评测",
    )
    check(
        "collect topic explicit wins",
        resolve_collect_topic(topic="口碑", keyword="数码评测", video_titles=["某视频"])
        == "口碑",
    )

    inserted = store.insert_posts("job1", [pos, neg, neu])
    check("insert posts", inserted == 3, str(inserted))
    check("count posts", store.count_posts() == 3)
    overview = store.overview()
    check("overview total", overview["total_posts"] == 3)

    # 2) HTTP API（内存 TestClient + 临时替换 get_store）
    import src.storage.db as dbmod

    original = dbmod._store
    dbmod._store = store
    try:
        client = TestClient(app)

        r = client.get("/api/v1/health/ready")
        check("health ready", r.status_code == 200 and r.json()["ok"] is True)
        check("health readiness", "readiness" in r.json()["data"])
        check(
            "readiness sentiment",
            "cached" in r.json()["data"]["readiness"]["sentiment"],
        )

        r = client.get("/api/v1/dashboard/overview")
        check("dashboard", r.status_code == 200 and r.json()["data"]["total_posts"] == 3)

        r = client.get("/api/v1/posts")
        check("posts list", r.status_code == 200 and r.json()["data"]["count"] == 3)

        r = client.get("/api/v1/alerts")
        check("alerts", r.status_code == 200 and "items" in r.json()["data"])

        r = client.get("/api/v1/trends")
        check("trends", r.status_code == 200 and isinstance(r.json()["data"]["series"], list))

        # 趋势按 fetched_at 优先：样例旧 published_at 不应压过今日入库
        from src.services.forecast import daily_volume_series
        from src.services.normalize import normalize_post as _np

        oldish = _np(
            {
                "id": "trend-old",
                "text": "旧帖差评投诉",
                "published_at": "2020-01-01T00:00:00+00:00",
            }
        )
        oldish["fetched_at"] = "2026-07-30T12:00:00+00:00"
        store.insert_posts("job-trend", [oldish])
        trend = daily_volume_series(30, use_prophet=False)
        days = {row["day"]: row["count"] for row in trend["series"] if not row.get("is_forecast")}
        check("trend prefers fetched_at", days.get("2026-07-30", 0) >= 1, str(days))
        check("trend ignores old published alone", days.get("2020-01-01", 0) == 0, str(days))

        r = client.get("/api/v1/reports/summary")
        check("reports", r.status_code == 200 and r.json()["ok"] is True)

        r = client.get("/api/v1/reports/export.csv")
        check("export csv", r.status_code == 200 and r.headers["content-type"].startswith("text/csv"))

        r = client.get("/api/v1/reports/export.pdf")
        check("export pdf", r.status_code == 200 and r.content[:4] == b"%PDF")

        # 用户文本含 <>& 时 PDF 不得解析失败
        from src.services.report import build_pdf_bytes

        nasty = {
            "generated_for": "测试 <报告>",
            "overview": {
                "total_posts": 1,
                "by_topic": [{"topic": "A<B&C", "count": 1}],
            },
            "sentiment": {
                "bert_done": 0,
                "breakdown": [{"label": "negative", "method": "lexicon", "count": 1}],
            },
            "alerts": {
                "total": 1,
                "high": 1,
                "items": [
                    {
                        "severity": "high",
                        "title": "标题 <未闭合",
                        "message": "内容 & 更多 <tag>",
                    }
                ],
            },
            "notes": ["说明 <ok>"],
            "ai_summary": "摘要 <em>x",
        }
        pdf = build_pdf_bytes(nasty)
        check("pdf escape", pdf[:4] == b"%PDF", str(len(pdf)))

        r = client.get("/api/v1/settings/alert-keywords")
        check("alert keywords get", r.status_code == 200 and isinstance(r.json()["data"]["keywords"], list))

        r = client.put("/api/v1/settings/alert-keywords", json={"keywords": ["投诉", "差评", "测试词"]})
        check("alert keywords put", r.status_code == 200 and "测试词" in r.json()["data"]["keywords"])

        r = client.post("/api/v1/analysis-jobs", json={"kind": "sentiment", "limit": 10})
        check("analysis job create", r.status_code == 200 and r.json()["ok"] is True)
        job_id = r.json()["data"]["id"]
        r = client.get(f"/api/v1/analysis-jobs/{job_id}")
        check("analysis job get", r.status_code == 200 and r.json()["data"]["id"] == job_id)

        r = client.get("/api/v1/analysis/status")
        check("analysis status", r.status_code == 200 and r.json()["ok"] is True)

        r = client.get("/api/v1/agent/status")
        check("agent status", r.status_code == 200 and "ready" in r.json()["data"])

        r = client.post("/api/v1/agent/chat", json={"question": "当前主要风险是什么？"})
        check("agent chat status", r.status_code in (200, 503), str(r.status_code))
        if r.status_code == 200:
            check("agent chat ok", r.json().get("ok") is True and bool(r.json()["data"].get("content")))
        else:
            check(
                "agent chat unavailable",
                r.json().get("ok") is False,
                (r.text or "")[:160],
            )

        # MediaCrawler 字段规范化
        mc = normalize_post(
            {
                "note_id": "n-smoke-1",
                "title": "食堂",
                "desc": "排队久差评投诉",
                "nickname": "测",
                "create_time": 1721000000,
                "liked_count": 3,
            },
            platform="xhs",
        )
        check("mc normalize platform", mc["platform"] == "xhs")
        check("mc normalize text", "排队久" in mc["text"] and mc["source_id"] == "n-smoke-1")

        # 导入 JSON
        sample = [
            {
                "id": "imp-1",
                "text": "教务系统崩溃，非常不满",
                "created_at": "2026-07-28 10:00:00",
                "topic": "教务",
            },
            {
                "id": "imp-2",
                "text": "奖学金政策很给力，点赞",
                "created_at": "2026-07-28 11:00:00",
            },
        ]
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump(sample, f, ensure_ascii=False)
            path = f.name
        with open(path, "rb") as fh:
            r = client.post(
                "/api/v1/imports",
                files={"file": ("t.json", fh, "application/json")},
                data={"topic": "文件导入", "platform": "campus"},
            )
        check("import api", r.status_code == 200 and r.json()["ok"] is True, r.text[:200])
        check("import inserted", r.json()["data"]["stats"]["inserted"] >= 1)

        # 错误体：缺文件由 FastAPI 校验（422）或业务 400
        r = client.post("/api/v1/imports", data={"topic": "x"})
        check("import missing file status", r.status_code in (400, 422), str(r.status_code))

        # 词云（不强制 BERTopic）
        r = client.get("/api/v1/analysis/topics/words")
        check("word cloud", r.status_code == 200 and r.json()["ok"] is True)

        r = client.post("/api/v1/analysis/topics/run", json={"limit": 50, "use_bertopic": False})
        check("topics tfidf", r.status_code == 200 and r.json()["ok"] is True, r.text[:200])
    finally:
        dbmod._store = original

    # 3) 设备
    info = get_device_info()
    check("torch installed", info["torch_installed"] is True, str(info))

    # 4) Ollama 嵌入（本机）
    try:
        emb = OllamaEmbedder()
        vec = emb.encode(["连通测试"])
        check("ollama embed", vec.shape[-1] > 0, str(vec.shape))
    except Exception as exc:
        print(f"[WARN] ollama embed skipped: {exc}")

    # 5) 配置路径
    check("data dir under backend", "backend" in str(DATA_DIR).replace("\\", "/"))
    check("db path under data", str(DATA_DIR) in settings.db_path or Path(settings.db_path).parent == DATA_DIR)

    # 6) MediaCrawler 夹具转换
    fixture = DATA_DIR / "samples" / "mediacrawler_xhs_fixture.json"
    if fixture.exists():
        import importlib.util

        conv_path = BACKEND / "scripts" / "convert_mediacrawler.py"
        spec = importlib.util.spec_from_file_location("convert_mediacrawler", conv_path)
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(mod)
        rows = mod._load_file(fixture)
        posts, stats = mod.convert_records(rows, platform="xhs", include_comments=False)
        check("mc convert content", stats["normalize_ok"] >= 5 and len(posts) >= 5, str(stats))
        posts_c, stats_c = mod.convert_records(rows, platform="xhs", include_comments=True)
        check(
            "mc convert with comments",
            stats_c["comments"] >= 1 and len(posts_c) > len(posts),
            str(stats_c),
        )
    else:
        print("[WARN] mediacrawler fixture missing, skip convert check")

    print("\nALL CHECKS PASSED")
    tmp.cleanup()


if __name__ == "__main__":
    main()
