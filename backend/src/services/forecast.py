"""趋势与预警（滑动平均 + 可选 Prophet + 可配置敏感词）。"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from src.config.settings import settings
from src.storage.db import get_store

_DEFAULT_NEG_HINTS = (
    "劝退",
    "差评",
    "翻车",
    "塌房",
    "抄袭",
    "注水",
    "水文",
    "浪费时间",
    "看不下去",
    "尴尬",
    "离谱",
    "失望",
    "恶心",
    "投诉",
    "骗人",
    "虚假",
    "引战",
    "崩坏",
    "太烂",
    "烂尾",
)


def get_alert_keywords() -> list[str]:
    store = get_store()
    saved = store.get_setting("alert_keywords")
    if isinstance(saved, list) and saved:
        cleaned = [str(x).strip() for x in saved if str(x).strip()]
        # 旧版校园默认词表 → 自动切到口碑默认（用户自定义词不受影响）
        legacy = {
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
        }
        if cleaned and set(cleaned) <= legacy and len(cleaned) <= len(legacy):
            # 持久化迁移，避免设置页仍显示旧校园词、预警却用新默认词
            fresh = list(settings.default_alert_keywords or _DEFAULT_NEG_HINTS)
            store.set_setting("alert_keywords", fresh)
            return fresh
        return cleaned
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


def alert_from_post(
    post: dict[str, Any],
    keywords: list[str] | None = None,
    *,
    title_prefix: str = "负面/敏感舆情",
) -> dict[str, Any] | None:
    """按标注方法分级：词典占位不单独报警；BERT 负面才进主预警。"""
    keywords = keywords if keywords is not None else get_alert_keywords()
    label = post.get("sentiment_label") or ""
    method = post.get("sentiment_method") or ""
    text = post.get("text") or ""
    hit = [w for w in keywords if w in text]
    is_trusted = method in {"bert", "manual", "llm"}
    is_neg = label == "negative"

    if is_trusted and is_neg and hit:
        severity = "high"
    elif is_trusted and is_neg:
        severity = "medium"
    else:
        # 非负面敏感词、词典占位均不报警，避免刷屏
        return None

    topic = post.get("topic") or "未分类"
    author = post.get("author") or ""
    title_tail = author or topic
    return {
        "id": f"post-{post['id']}",
        "type": "negative_content",
        "severity": severity,
        "title": f"{title_prefix} · {title_tail}",
        "message": text[:120],
        "topic": post.get("topic"),
        "sentiment_label": label,
        "sentiment_method": method,
        "sentiment_confidence": post.get("sentiment_confidence"),
        "keywords": hit,
        "created_at": post.get("fetched_at") or post.get("published_at"),
        "post_id": post["id"],
    }


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
    posts = get_store().list_posts(limit=2000)
    alerts: list[dict[str, Any]] = []
    keywords = get_alert_keywords()

    for post in posts:
        item = alert_from_post(post, keywords)
        if item:
            alerts.append(item)

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
            "情感主路径为 BERT（正/中/负；低置信为 uncertain）；入库不再写词典情感。",
            "主题向量默认使用本机 Ollama 嵌入模型。",
            "预警仅采信 BERT 负面（可叠加敏感词升为 high）；换模型后需重跑情感。",
            "趋势：滑动平均；样本充足时附加 Prophet 预测。",
        ],
    }
