"""将原始记录规范化为统一帖子结构。

兼容样例 JSON，以及 MediaCrawler 导出字段（小红书 / 抖音 / 微博等）。
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Any

from src.config.settings import settings
from src.storage.db import utc_now

# 简易情感词典（导入期占位；正式分析走 BERT）
_POS = ("好评", "满意", "感谢", "方便", "干净", "好吃", "给力", "优秀", "喜欢", "推荐")
_NEG = ("差评", "投诉", "难吃", "脏乱", "故障", "不满", "排队久", "离谱", "失望", "恶心")

# MediaCrawler / 导入常用平台码
PLATFORM_ALIASES = {
    "campus": "campus",
    "xhs": "xhs",
    "xiaohongshu": "xhs",
    "dy": "dy",
    "douyin": "dy",
    "wb": "wb",
    "weibo": "wb",
    "bili": "bili",
    "bilibili": "bili",
    "zhihu": "zhihu",
    "ks": "ks",
    "kuaishou": "ks",
    "tieba": "tieba",
}


def normalize_platform(value: str | None, fallback: str | None = None) -> str:
    raw = (value or fallback or settings.default_platform or "campus").strip().lower()
    return PLATFORM_ALIASES.get(raw, raw or "campus")


def _first(record: dict, *keys: str, default: Any = None) -> Any:
    for key in keys:
        if key in record and record[key] not in (None, ""):
            return record[key]
    return default


def _integer(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _timestamp(value: Any) -> str | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        try:
            ts = float(value)
            # 毫秒时间戳
            if ts > 1e12:
                ts = ts / 1000.0
            # 秒级但写成字符串数字的短时间戳也兼容
            elif ts > 1e10:
                ts = ts / 1000.0
            return datetime.fromtimestamp(ts, tz=timezone.utc).replace(
                microsecond=0
            ).isoformat()
        except (OSError, OverflowError, ValueError):
            return None
    text = str(value).strip().replace("/", "-")
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    # 纯数字字符串时间戳
    if re.fullmatch(r"\d{10,13}", text):
        return _timestamp(int(text))
    try:
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat()
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(text[:19] if " " in text else text[:10], fmt)
            return dt.replace(tzinfo=timezone.utc).isoformat()
        except ValueError:
            continue
    return text


def _extract_text(record: dict) -> str:
    """合并标题与正文等 MediaCrawler 常见字段。"""
    title = str(
        _first(record, "title", "note_title", "aweme_title", default="") or ""
    ).strip()
    body = str(
        _first(
            record,
            "text",
            "content",
            "desc",
            "raw_text",
            "note_desc",
            "aweme_desc",
            "share_info",
            "note_content",
            "content_text",
            default="",
        )
        or ""
    ).strip()
    # 评论体
    if not body:
        body = str(
            _first(record, "comment_text", "content_clean", default="") or ""
        ).strip()
    if title and body:
        if title in body:
            text = body
        else:
            text = f"{title}。{body}"
    else:
        text = body or title
    return re.sub(r"\s+", " ", text).strip()


def infer_topic(
    text: str,
    fallback: str = "综合",
    *,
    platform: str | None = None,
) -> str:
    """无显式 topic 时的弱推断。B 站等口碑场景不套校园词表。"""
    plat = (platform or "").strip().lower()
    if plat in {"bili", "bilibili", "dy", "douyin", "xhs", "xiaohongshu", "wb", "weibo"}:
        return fallback
    for kw in settings.default_school_keywords:
        if kw in text:
            return kw
    return fallback


def lexicon_sentiment(text: str) -> tuple[int, str, str]:
    """返回 (score -1/0/1, label, method)。仅作调试/对照，入库默认不再使用。"""
    pos = sum(1 for w in _POS if w in text)
    neg = sum(1 for w in _NEG if w in text)
    if pos > neg:
        return 1, "positive", "lexicon"
    if neg > pos:
        return -1, "negative", "lexicon"
    return 0, "neutral", "lexicon"


def normalize_post(
    record: dict,
    *,
    platform: str | None = None,
    topic: str | None = None,
) -> dict:
    platform = normalize_platform(
        platform or str(_first(record, "platform", "source", default="") or ""),
        settings.default_platform,
    )
    text = _extract_text(record)
    source_id = str(
        _first(
            record,
            "source_id",
            "post_id",
            "note_id",
            "aweme_id",
            "video_id",
            "mid",
            "id",
            "comment_id",
            default="",
        )
        or ""
    ).strip()
    published_at = _timestamp(
        _first(
            record,
            "published_at",
            "created_at",
            "publish_time",
            "create_time",
            "create_time_str",
            "time_stamp",
            "timestamp",
            "time",
        )
    )
    if not source_id and text:
        identity = f"{platform}|{published_at}|{text}".encode("utf-8")
        source_id = hashlib.sha256(identity).hexdigest()[:24]
    if not source_id or not text:
        raise ValueError("记录缺少可识别的 ID 或正文")

    resolved_topic = topic or str(
        _first(record, "topic", "keyword", "source_keyword", default="") or ""
    ).strip()
    if not resolved_topic:
        resolved_topic = infer_topic(text, platform=platform)

    # 入库不写词典情感，避免未跑 BERT 时污染预警/报告；仅保留显式提供的标签
    score: int | None = None
    label: str | None = None
    method: str | None = None
    raw_sent = record.get("sentiment")
    if isinstance(raw_sent, str) and raw_sent.lower() in {
        "positive",
        "negative",
        "neutral",
    }:
        label = raw_sent.lower()
        score = {"positive": 1, "neutral": 0, "negative": -1}[label]
        method = "provided"

    author = str(
        _first(
            record,
            "author",
            "nickname",
            "user_name",
            "unique_id",
            default="",
        )
        or ""
    )

    return {
        "platform": platform,
        "source_id": source_id,
        "author": author[:200],
        "text": text,
        "published_at": published_at,
        "engagement": {
            "likes": _integer(_first(record, "likes", "liked_count", "digg_count")),
            "comments": _integer(
                _first(record, "comments", "comment_count", "comments_count")
            ),
            "reposts": _integer(
                _first(record, "reposts", "reposts_count", "share_count")
            ),
            "collects": _integer(
                _first(record, "collected_count", "collect_count", "favorite_count")
            ),
        },
        "fetched_at": utc_now(),
        "source_url": _first(
            record,
            "source_url",
            "url",
            "note_url",
            "aweme_url",
            "share_url",
            "video_url",
        ),
        "topic": resolved_topic,
        "sentiment": score,
        "sentiment_label": label,
        "sentiment_method": method,
        "raw": record,
    }
