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

    # 1) 规范化 + 三类情感词典
    pos = normalize_post({"id": "1", "text": "食堂很好吃，非常满意推荐"})
    neg = normalize_post({"id": "2", "text": "宿舍热水故障，差评投诉"})
    neu = normalize_post({"id": "3", "text": "图书馆今天开到九点"})
    check("normalize positive", pos["sentiment_label"] == "positive", str(pos))
    check("normalize negative", neg["sentiment_label"] == "negative", str(neg))
    check("lexicon returns triple", lexicon_sentiment("一般情况")[1] in {"positive", "neutral", "negative"})

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

        r = client.get("/api/v1/dashboard/overview")
        check("dashboard", r.status_code == 200 and r.json()["data"]["total_posts"] == 3)

        r = client.get("/api/v1/posts")
        check("posts list", r.status_code == 200 and r.json()["data"]["count"] == 3)

        r = client.get("/api/v1/alerts")
        check("alerts", r.status_code == 200 and "items" in r.json()["data"])

        r = client.get("/api/v1/trends")
        check("trends", r.status_code == 200 and isinstance(r.json()["data"]["series"], list))

        r = client.get("/api/v1/reports/summary")
        check("reports", r.status_code == 200 and r.json()["ok"] is True)

        r = client.get("/api/v1/analysis/status")
        check("analysis status", r.status_code == 200 and r.json()["ok"] is True)

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

    print("\nALL CHECKS PASSED")
    tmp.cleanup()


if __name__ == "__main__":
    main()
