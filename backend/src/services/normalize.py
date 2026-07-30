"""将原始记录规范化为统一帖子结构。"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Any

from src.config.settings import settings
from src.storage.db import utc_now

# 简易校园情感词典（Phase C 会换成 BERT；此处仅作导入期占位标签）
_POS = ("好评", "满意", "感谢", "方便", "干净", "好吃", "给力", "优秀", "喜欢", "推荐")
_NEG = ("差评", "投诉", "难吃", "脏乱", "故障", "不满", "排队久", "离谱", "失望", "恶心")


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
            return datetime.fromtimestamp(ts, tz=timezone.utc).replace(
                microsecond=0
            ).isoformat()
        except (OSError, OverflowError, ValueError):
            return None
    text = str(value).strip().replace("/", "-")
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    # 优先 fromisoformat
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


def infer_topic(text: str, fallback: str = "校园综合") -> str:
    for kw in settings.default_school_keywords:
        if kw in text:
            return kw
    return fallback


def lexicon_sentiment(text: str) -> tuple[int, str, str]:
    """返回 (score -1/0/1, label, method)。"""
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
    platform = platform or settings.default_platform
    text = str(
        _first(record, "text", "content", "desc", "raw_text", default="")
    ).strip()
    text = re.sub(r"\s+", " ", text)
    source_id = str(
        _first(record, "source_id", "post_id", "id", default="")
    ).strip()
    published_at = _timestamp(
        _first(record, "published_at", "created_at", "publish_time", "time")
    )
    if not source_id and text:
        identity = f"{platform}|{published_at}|{text}".encode("utf-8")
        source_id = hashlib.sha256(identity).hexdigest()[:24]
    if not source_id or not text:
        raise ValueError("记录缺少可识别的 ID 或正文")

    resolved_topic = topic or str(
        _first(record, "topic", "keyword", default="") or ""
    ).strip()
    if not resolved_topic:
        resolved_topic = infer_topic(text)

    score, label, method = lexicon_sentiment(text)
    # 若原始数据自带情感则尊重
    raw_sent = record.get("sentiment")
    if isinstance(raw_sent, str) and raw_sent.lower() in {
        "positive",
        "negative",
        "neutral",
    }:
        label = raw_sent.lower()
        score = {"positive": 1, "neutral": 0, "negative": -1}[label]
        method = "provided"

    return {
        "platform": platform,
        "source_id": source_id,
        "author": str(
            _first(record, "author", "user_name", "nickname", default="")
        )[:200],
        "text": text,
        "published_at": published_at,
        "engagement": {
            "likes": _integer(_first(record, "likes", "liked_count")),
            "comments": _integer(_first(record, "comments", "comment_count")),
            "reposts": _integer(_first(record, "reposts", "reposts_count")),
        },
        "fetched_at": utc_now(),
        "source_url": _first(record, "source_url", "url"),
        "topic": resolved_topic,
        "sentiment": score,
        "sentiment_label": label,
        "sentiment_method": method,
        "raw": record,
    }
