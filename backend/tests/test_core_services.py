"""核心服务与规范化回归（无 GPU / 无外网）。"""

from __future__ import annotations


def test_normalize_skips_lexicon_auto_label():
    from src.services.normalize import normalize_post

    pos = normalize_post({"id": "1", "text": "食堂很好吃，非常满意推荐"})
    assert pos["sentiment_label"] is None
    assert pos["sentiment_method"] is None


def test_infer_topic_campus_vs_bili():
    from src.services.normalize import normalize_post

    assert normalize_post({"id": "4", "text": "食堂排队久"})["topic"] == "食堂"
    assert (
        normalize_post({"id": "6", "text": "食堂真好吃", "platform": "bili"})["topic"]
        == "综合"
    )


def test_alert_ignores_lexicon_keeps_bert():
    from src.services.forecast import alert_from_post

    lex_neg = {
        "id": 1,
        "text": "差评劝退离谱",
        "sentiment_label": "negative",
        "sentiment_method": "lexicon",
        "author": "x",
        "topic": "t",
    }
    assert alert_from_post(lex_neg) is None
    bert = {**lex_neg, "id": 2, "sentiment_method": "bert"}
    assert (alert_from_post(bert) or {}).get("severity") == "high"


def test_sentiment_pipeline_batch_shape():
    from src.services.sentiment import SentimentAnalyzer

    batch_top1 = [
        {"label": "positive", "score": 0.9},
        {"label": "negative", "score": 0.8},
    ]
    shaped = SentimentAnalyzer._normalize_pipeline_batch(batch_top1, 2)
    assert len(shaped) == 2
    assert shaped[0]["label"] == "positive"


def test_trend_prefers_fetched_at(store):
    from src.services.forecast import daily_volume_series
    from src.services.normalize import normalize_post
    import src.storage.db as dbmod

    # daily_volume_series 走 get_store()
    assert dbmod.get_store() is store

    oldish = normalize_post(
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
    assert days.get("2026-07-30", 0) >= 1
    assert days.get("2020-01-01", 0) == 0
