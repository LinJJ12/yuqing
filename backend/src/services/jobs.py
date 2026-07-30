"""异步分析任务（进程内线程池；不依赖 Redis）。"""

from __future__ import annotations

import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from src.services.sentiment import (
    get_sentiment_analyzer,
    mark_sentiment_model_applied,
    should_rerun_all_sentiment,
)
from src.services.topics import get_topic_analyzer
from src.storage.db import get_store

_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="analysis-job")
_lock = threading.Lock()


def _run_sentiment(limit: int, only_pending: bool) -> dict[str, Any]:
    store = get_store()
    force_all = should_rerun_all_sentiment(only_pending, store)
    posts = store.list_posts(
        limit=limit,
        offset=0,
        only_pending_bert=not force_all,
        exclude_protected=True,
    )
    if not posts:
        if force_all:
            mark_sentiment_model_applied(store)
        stats = store.sentiment_stats()
        if stats.get("total", 0) == 0:
            msg = "库中无帖子"
        elif force_all:
            msg = "没有可覆盖的帖子（人工/LLM 改判已保护）"
        elif only_pending:
            msg = "没有待分析帖子"
        else:
            msg = "没有可分析帖子"
        return {
            "updated": 0,
            "message": msg,
            "stats": stats,
            "full_rerun": force_all,
            "model_stale": False if force_all else bool(stats.get("model_stale")),
        }
    analyzer = get_sentiment_analyzer()
    t0 = time.perf_counter()
    preds = analyzer.predict_batch([p["text"] for p in posts])
    updates = [
        {
            "id": post["id"],
            "sentiment": pred["sentiment"],
            "sentiment_label": pred["sentiment_label"],
            "sentiment_method": "bert",
            "sentiment_confidence": pred.get("sentiment_confidence", pred.get("confidence")),
        }
        for post, pred in zip(posts, preds)
    ]
    updated = store.update_post_sentiments(updates)
    mark_sentiment_model_applied(store)
    return {
        "updated": updated,
        "device": analyzer.status.get("device"),
        "elapsed_ms": round((time.perf_counter() - t0) * 1000, 1),
        "stats": store.sentiment_stats(),
        "full_rerun": force_all,
    }


def enqueue_pending_sentiment(*, limit: int = 2000) -> dict:
    """采集/导入后排队跑待处理 BERT（不阻塞主流程）。"""
    return enqueue_analysis_job(
        "sentiment",
        {"limit": limit, "only_pending": True},
    )


def _run_topics(limit: int, use_bertopic: bool) -> dict[str, Any]:
    store = get_store()
    rows = store.list_post_texts(limit=limit)
    texts = [r["text"] for r in rows]
    if len(texts) < 5:
        raise ValueError("帖子数量不足，请先导入数据")
    t0 = time.perf_counter()
    result = get_topic_analyzer().analyze(texts, use_bertopic=use_bertopic)
    result["elapsed_ms"] = round((time.perf_counter() - t0) * 1000, 1)
    result["db_topics"] = store.overview()["by_topic"]
    # 主题结果较大，任务里只留摘要
    return {
        "elapsed_ms": result["elapsed_ms"],
        "method": result.get("method"),
        "topic_count": len(result.get("topics") or []),
        "word_cloud_top": (result.get("word_cloud") or [])[:15],
        "db_topics": result.get("db_topics"),
    }


def _execute_job(job_id: str) -> None:
    store = get_store()
    job = store.get_analysis_job(job_id)
    if not job:
        return
    kind = job["kind"]
    params = job.get("params") or {}
    try:
        store.update_analysis_job(job_id, status="running")
        if kind == "sentiment":
            result = _run_sentiment(
                int(params.get("limit", 2000)),
                bool(params.get("only_pending", True)),
            )
        elif kind == "topics":
            result = _run_topics(
                int(params.get("limit", 2000)),
                bool(params.get("use_bertopic", True)),
            )
        elif kind == "pipeline":
            sent = _run_sentiment(
                int(params.get("limit", 2000)),
                bool(params.get("only_pending", True)),
            )
            topics = _run_topics(
                int(params.get("topic_limit", params.get("limit", 2000))),
                bool(params.get("use_bertopic", True)),
            )
            result = {"sentiment": sent, "topics": topics}
        else:
            raise ValueError(f"未知任务类型: {kind}")
        store.update_analysis_job(job_id, status="succeeded", result=result)
    except Exception as exc:
        store.update_analysis_job(
            job_id,
            status="failed",
            error_message=f"{exc}\n{traceback.format_exc()[-800:]}",
        )


def enqueue_analysis_job(kind: str, params: dict[str, Any] | None = None) -> dict:
    if kind not in {"sentiment", "topics", "pipeline"}:
        raise ValueError("kind 必须是 sentiment / topics / pipeline")
    with _lock:
        job = get_store().create_analysis_job(kind, params or {})
        _executor.submit(_execute_job, job["id"])
    return job


def get_analysis_job(job_id: str) -> dict | None:
    return get_store().get_analysis_job(job_id)


def list_analysis_jobs(limit: int = 20) -> list[dict]:
    return get_store().list_analysis_jobs(limit=limit)
