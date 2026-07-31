"""情感 / 主题分析 API。"""

from __future__ import annotations

import time
from collections import Counter

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from src.config.device import get_device_info
from src.lib.http import err, ok
from src.services.bilibili_collect import resolve_bvid
from src.services.jobs import (
    enqueue_analysis_job,
    get_analysis_job,
    list_analysis_jobs,
)
from src.services.sentiment import (
    get_sentiment_analyzer,
    mark_sentiment_model_applied,
    should_rerun_all_sentiment,
)
from src.services.topics import get_topic_analyzer
from src.storage.db import get_store

router = APIRouter(tags=["analysis"])


class TextIn(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


class AnalyzeSentimentIn(BaseModel):
    limit: int = Field(default=2000, ge=1, le=5000)
    only_pending: bool = True
    bvid: str | None = Field(default=None, max_length=200)


class LlmReviewIn(BaseModel):
    post_id: int | None = None
    text: str | None = Field(default=None, max_length=2000)
    apply: bool = True


class AnalyzeTopicsIn(BaseModel):
    limit: int = Field(default=2000, ge=10, le=5000)
    use_bertopic: bool = True
    bvid: str | None = Field(default=None, max_length=200)


class AnalysisJobIn(BaseModel):
    kind: str = Field(description="sentiment | topics | pipeline")
    limit: int = Field(default=2000, ge=1, le=5000)
    only_pending: bool = True
    use_bertopic: bool = True
    topic_limit: int = Field(default=2000, ge=10, le=5000)
    bvid: str | None = Field(default=None, max_length=200)


def _scoped_db_topics(rows: list[dict]) -> list[dict]:
    counts = Counter((r.get("topic") or "未分类") for r in rows)
    return [{"topic": topic, "count": count} for topic, count in counts.most_common(12)]


@router.get("/analysis/status")
def analysis_status():
    from src.services.readiness import build_readiness

    sent = get_sentiment_analyzer()
    topics = get_topic_analyzer()
    return ok(
        {
            "device": get_device_info(),
            "sentiment": sent.status,
            "topics": topics.status,
            "db": get_store().sentiment_stats(),
            "readiness": build_readiness(),
        }
    )


@router.post("/analysis/sentiment/preview")
def sentiment_preview(body: TextIn):
    try:
        analyzer = get_sentiment_analyzer()
        t0 = time.perf_counter()
        result = analyzer.predict_one(body.text)
        elapsed = round((time.perf_counter() - t0) * 1000, 1)
        return ok({**result, "device": analyzer.status.get("device"), "elapsed_ms": elapsed})
    except Exception as exc:
        return err("model_load_failed", f"情感模型加载/推理失败: {exc}", status=503)


@router.post("/analysis/sentiment/llm-review")
def sentiment_llm_review(body: LlmReviewIn):
    """LLM 复判难例；默认写回库（method=llm，后续 BERT 不覆盖）。"""
    from src.services.agent import AgentUnavailableError
    from src.services.sentiment_review import llm_review_post, llm_review_text

    try:
        if body.post_id is not None:
            data = llm_review_post(body.post_id, apply=body.apply)
        elif body.text and body.text.strip():
            data = llm_review_text(body.text.strip())
        else:
            return err("invalid_request", "请提供 post_id 或 text", status=400)
        return ok(data)
    except LookupError:
        return err("not_found", "帖子不存在", status=404)
    except AgentUnavailableError as exc:
        return err("llm_unavailable", str(exc), status=503)
    except ValueError as exc:
        return err("llm_review_failed", str(exc), status=400)
    except Exception as exc:
        return err("llm_review_failed", f"LLM 复判失败: {exc}", status=500)


@router.post("/analysis/sentiment/run")
def sentiment_run(body: AnalyzeSentimentIn):
    store = get_store()
    bvid = resolve_bvid(body.bvid)
    force_all = should_rerun_all_sentiment(body.only_pending, store)
    posts = store.list_posts(
        limit=body.limit,
        offset=0,
        only_pending_bert=not force_all,
        exclude_protected=True,
        bvid=bvid,
    )
    if not posts:
        # 换模全量时若仅剩人工/LLM 保护帖或库空，仍标记模型已对齐，避免永久 stale
        if force_all and not bvid:
            mark_sentiment_model_applied(store)
        stats = store.sentiment_stats(bvid=bvid)
        if stats.get("total", 0) == 0:
            msg = "当前范围内无帖子" if bvid else "库中无帖子"
        elif force_all:
            msg = "没有可覆盖的帖子（人工/LLM 改判已保护）"
        elif body.only_pending:
            msg = "没有待分析帖子"
        else:
            msg = "没有可分析帖子"
        return ok(
            {
                "updated": 0,
                "message": msg,
                "full_rerun": force_all,
                "bvid": bvid,
                "stats": stats,
            }
        )
    try:
        analyzer = get_sentiment_analyzer()
        t0 = time.perf_counter()
        preds = analyzer.predict_batch([p["text"] for p in posts])
        updates = [
            {
                "id": post["id"],
                "sentiment": pred["sentiment"],
                "sentiment_label": pred["sentiment_label"],
                "sentiment_method": "bert",
                "sentiment_confidence": pred.get(
                    "sentiment_confidence", pred.get("confidence")
                ),
            }
            for post, pred in zip(posts, preds)
        ]
        updated = store.update_post_sentiments(updates)
        # 单视频跑批不清除全局 model_stale，避免误标整库已对齐
        if not bvid:
            mark_sentiment_model_applied(store)
        elapsed = round((time.perf_counter() - t0) * 1000, 1)
        return ok(
            {
                "updated": updated,
                "device": analyzer.status.get("device"),
                "elapsed_ms": elapsed,
                "full_rerun": force_all,
                "bvid": bvid,
                "stats": store.sentiment_stats(bvid=bvid),
                "sample": [
                    {
                        "id": posts[i]["id"],
                        "text": posts[i]["text"][:80],
                        **preds[i],
                    }
                    for i in range(min(5, len(posts)))
                ],
            }
        )
    except Exception as exc:
        return err("sentiment_failed", f"批量情感分析失败: {exc}", status=503)


@router.get("/analysis/sentiment/stats")
def sentiment_stats(bvid: str | None = Query(default=None, max_length=200)):
    return ok(get_store().sentiment_stats(bvid=resolve_bvid(bvid)))


@router.post("/analysis/topics/run")
def topics_run(body: AnalyzeTopicsIn):
    store = get_store()
    bvid = resolve_bvid(body.bvid)
    rows = store.list_post_texts(limit=body.limit, bvid=bvid)
    texts = [r["text"] for r in rows]
    if len(texts) < 5:
        scope = "该视频" if bvid else "库中"
        return err(
            "not_enough_data",
            f"{scope}帖子数量不足（需至少 5 条），请先导入或采集更多评论",
            status=400,
        )
    try:
        t0 = time.perf_counter()
        result = get_topic_analyzer().analyze(texts, use_bertopic=body.use_bertopic)
        result["elapsed_ms"] = round((time.perf_counter() - t0) * 1000, 1)
        result["bvid"] = bvid
        if bvid:
            result["db_topics"] = _scoped_db_topics(rows)
        else:
            result["db_topics"] = store.overview()["by_topic"]
        return ok(result)
    except Exception as exc:
        return err("topics_failed", f"主题分析失败: {exc}", status=500)


@router.get("/analysis/topics/words")
def topic_words(
    top_k: int = Query(default=40, ge=5, le=100),
    bvid: str | None = Query(default=None, max_length=200),
):
    key = resolve_bvid(bvid)
    rows = get_store().list_post_texts(limit=3000, bvid=key)
    words = get_topic_analyzer().word_cloud([r["text"] for r in rows], top_k=top_k)
    return ok({"word_cloud": words, "document_count": len(rows), "bvid": key})


@router.post("/analysis-jobs")
def create_analysis_job(body: AnalysisJobIn):
    try:
        job = enqueue_analysis_job(
            body.kind,
            {
                "limit": body.limit,
                "only_pending": body.only_pending,
                "use_bertopic": body.use_bertopic,
                "topic_limit": body.topic_limit,
                "bvid": resolve_bvid(body.bvid),
            },
        )
        return ok(job)
    except ValueError as exc:
        return err("invalid_job", str(exc), status=400)
    except Exception as exc:
        return err("job_enqueue_failed", f"创建任务失败: {exc}", status=500)


@router.get("/analysis-jobs")
def analysis_jobs(limit: int = Query(default=20, ge=1, le=100)):
    items = list_analysis_jobs(limit)
    return ok({"items": items, "count": len(items)})


@router.get("/analysis-jobs/{job_id}")
def analysis_job_detail(job_id: str):
    job = get_analysis_job(job_id)
    if not job:
        return err("not_found", "任务不存在", status=404)
    return ok(job)
