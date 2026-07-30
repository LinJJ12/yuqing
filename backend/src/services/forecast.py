"""趋势与预警（滑动平均 + 校园负面规则）。"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from src.config.settings import settings
from src.storage.db import get_store

_NEG_HINTS = (
    "投诉", "差评", "故障", "不满", "恶心", "离谱", "失望",
    "崩溃", "排队久", "脏乱", "难吃", "拖延", "态度差",
)


def daily_volume_series(limit_days: int = 30) -> list[dict[str, Any]]:
    posts = get_store().list_posts(limit=5000)
    buckets: dict[str, int] = defaultdict(int)
    for post in posts:
        day = (post.get("published_at") or post.get("fetched_at") or "")[:10]
        if day:
            buckets[day] += 1
    days = sorted(buckets.keys())[-limit_days:]
    series = [{"day": d, "count": buckets[d]} for d in days]
    for i, item in enumerate(series):
        window = series[max(0, i - 2) : i + 1]
        item["rolling_mean"] = round(
            sum(x["count"] for x in window) / max(len(window), 1), 2
        )
        if i == 0:
            item["growth_rate"] = 0.0
        else:
            prev = series[i - 1]["count"] or 1
            item["growth_rate"] = round((item["count"] - prev) / prev, 4)
    return series


def detect_alerts() -> list[dict[str, Any]]:
    posts = get_store().list_posts(limit=500)
    alerts: list[dict[str, Any]] = []

    for post in posts:
        label = post.get("sentiment_label")
        text = post.get("text") or ""
        hit = [w for w in _NEG_HINTS if w in text]
        if label != "negative" and not hit:
            continue
        if label == "negative" and hit:
            severity = "high"
        elif label == "negative":
            severity = "medium"
        else:
            severity = "low"
        alerts.append(
            {
                "id": f"post-{post['id']}",
                "type": "negative_content",
                "severity": severity,
                "title": f"负面/敏感舆情 · {post.get('topic') or '未分类'}",
                "message": text[:120],
                "topic": post.get("topic"),
                "sentiment_label": label,
                "keywords": hit,
                "created_at": post.get("published_at") or post.get("fetched_at"),
                "post_id": post["id"],
            }
        )

    series = daily_volume_series(14)
    if len(series) >= 2:
        last = series[-1]
        if last.get("growth_rate", 0) >= 0.5 and last["count"] >= 5:
            alerts.append(
                {
                    "id": f"surge-{last['day']}",
                    "type": "volume_surge",
                    "severity": "medium",
                    "title": "发帖量异常上升",
                    "message": (
                        f"{last['day']} 发帖 {last['count']} 条，"
                        f"较前日增长 {round(last['growth_rate'] * 100, 1)}%"
                    ),
                    "topic": None,
                    "sentiment_label": None,
                    "keywords": [],
                    "created_at": last["day"],
                    "post_id": None,
                }
            )

    severity_rank = {"high": 0, "medium": 1, "low": 2}
    alerts.sort(
        key=lambda a: (
            severity_rank.get(a["severity"], 9),
            a.get("created_at") or "",
        )
    )
    return alerts[:50]


def build_report_summary() -> dict[str, Any]:
    store = get_store()
    overview = store.overview()
    sentiment = store.sentiment_stats()
    series = daily_volume_series(14)
    alerts = detect_alerts()
    return {
        "generated_for": "校园舆情日报（自动）",
        "school_keywords": settings.default_school_keywords,
        "overview": overview,
        "sentiment": sentiment,
        "trend": series,
        "alerts": {
            "total": len(alerts),
            "high": sum(1 for a in alerts if a["severity"] == "high"),
            "items": alerts[:10],
        },
        "notes": [
            "情感主路径为 BERT（正/中/负）；导入时词典标签仅作占位。",
            "主题向量默认使用本机 Ollama 嵌入模型。",
            "预警规则：负面情感/敏感词 + 日环比热度突增。",
        ],
    }
