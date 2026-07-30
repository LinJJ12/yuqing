"""趋势与预警（滑动平均 + 可选 Prophet + 可配置敏感词）。"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from src.config.settings import settings
from src.storage.db import get_store

_DEFAULT_NEG_HINTS = (
    "投诉",
    "差评",
    "故障",
    "不满",
    "恶心",
    "离谱",
    "失望",
    "崩溃",
    "排队久",
    "脏乱",
    "难吃",
    "拖延",
    "态度差",
)


def get_alert_keywords() -> list[str]:
    store = get_store()
    saved = store.get_setting("alert_keywords")
    if isinstance(saved, list) and saved:
        return [str(x).strip() for x in saved if str(x).strip()]
    return list(settings.default_alert_keywords or _DEFAULT_NEG_HINTS)


def set_alert_keywords(keywords: list[str]) -> list[str]:
    cleaned = []
    seen: set[str] = set()
    for raw in keywords:
        word = str(raw).strip()
        if not word or word in seen:
            continue
        seen.add(word)
        cleaned.append(word)
    if not cleaned:
        cleaned = list(settings.default_alert_keywords or _DEFAULT_NEG_HINTS)
    get_store().set_setting("alert_keywords", cleaned)
    return cleaned


def _prophet_forecast(
    series: list[dict[str, Any]],
    horizon_days: int = 7,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """在历史点上填充 prophet_yhat，并追加未来预测点。"""
    meta: dict[str, Any] = {"enabled": False, "message": "", "horizon_days": horizon_days}
    if len(series) < 5:
        meta["message"] = "样本不足 5 天，跳过 Prophet"
        return series, meta
    try:
        import pandas as pd
        from prophet import Prophet

        df = pd.DataFrame(
            {
                "ds": [row["day"] for row in series],
                "y": [row["count"] for row in series],
            }
        )
        model = Prophet(
            daily_seasonality=False,
            weekly_seasonality=len(series) >= 14,
            yearly_seasonality=False,
        )
        model.fit(df)
        future = model.make_future_dataframe(periods=horizon_days, freq="D")
        forecast = model.predict(future)
        by_day = {
            row.ds.strftime("%Y-%m-%d"): float(row.yhat)
            for row in forecast.itertuples()
        }
        for row in series:
            yhat = by_day.get(row["day"])
            if yhat is not None:
                row["prophet_yhat"] = round(max(yhat, 0.0), 2)

        last_hist = series[-1]["day"]
        for day, yhat in by_day.items():
            if day <= last_hist:
                continue
            series.append(
                {
                    "day": day,
                    "count": None,
                    "rolling_mean": None,
                    "growth_rate": None,
                    "prophet_yhat": round(max(yhat, 0.0), 2),
                    "is_forecast": True,
                }
            )
        meta["enabled"] = True
        meta["message"] = "ok"
        return series, meta
    except Exception as exc:
        meta["message"] = f"Prophet 不可用: {exc}"
        return series, meta


def daily_volume_series(
    limit_days: int = 30,
    *,
    use_prophet: bool = True,
    prophet_horizon: int = 7,
) -> dict[str, Any]:
    posts = get_store().list_posts(limit=5000)
    buckets: dict[str, int] = defaultdict(int)
    for post in posts:
        # 与总览 by_day / 列表默认排序一致：优先入库时间，避免样例假发布时间主导趋势
        day = (post.get("fetched_at") or post.get("published_at") or "")[:10]
        if day:
            buckets[day] += 1
    days = sorted(buckets.keys())[-limit_days:]
    series: list[dict[str, Any]] = [{"day": d, "count": buckets[d]} for d in days]
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
        item["is_forecast"] = False

    prophet_meta = {"enabled": False, "message": "未启用", "horizon_days": prophet_horizon}
    if use_prophet:
        series, prophet_meta = _prophet_forecast(series, horizon_days=prophet_horizon)
    return {"series": series, "prophet": prophet_meta}


def detect_alerts() -> list[dict[str, Any]]:
    posts = get_store().list_posts(limit=500)
    alerts: list[dict[str, Any]] = []
    keywords = get_alert_keywords()

    for post in posts:
        label = post.get("sentiment_label")
        text = post.get("text") or ""
        hit = [w for w in keywords if w in text]
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
                "created_at": post.get("fetched_at") or post.get("published_at"),
                "post_id": post["id"],
            }
        )

    trend = daily_volume_series(14, use_prophet=False)
    series = [row for row in trend["series"] if not row.get("is_forecast")]
    if len(series) >= 2:
        last = series[-1]
        if last.get("growth_rate", 0) >= 0.5 and (last.get("count") or 0) >= 5:
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


def build_report_summary(*, with_prophet: bool = True) -> dict[str, Any]:
    store = get_store()
    overview = store.overview()
    sentiment = store.sentiment_stats()
    trend_pack = daily_volume_series(14, use_prophet=with_prophet)
    alerts = detect_alerts()
    return {
        "generated_for": "舆情日报（自动）",
        "school_keywords": settings.default_school_keywords,
        "alert_keywords": get_alert_keywords(),
        "overview": overview,
        "sentiment": sentiment,
        "trend": trend_pack["series"],
        "prophet": trend_pack["prophet"],
        "alerts": {
            "total": len(alerts),
            "high": sum(1 for a in alerts if a["severity"] == "high"),
            "items": alerts[:10],
        },
        "notes": [
            "情感主路径为 BERT（正/中/负）；导入时词典标签仅作占位。",
            "主题向量默认使用本机 Ollama 嵌入模型。",
            "预警规则：负面情感/敏感词（可在设置页配置）+ 日环比热度突增。",
            "趋势：滑动平均；样本充足时附加 Prophet 预测。",
        ],
    }
