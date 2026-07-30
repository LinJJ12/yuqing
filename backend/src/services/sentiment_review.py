"""难例情感改判：人工 / LLM。"""

from __future__ import annotations

import json
import re
from typing import Any

_ALLOWED = {"positive", "neutral", "negative", "uncertain"}
_SCORE = {"positive": 1, "neutral": 0, "negative": -1, "uncertain": 0}


def apply_sentiment_override(
    post_id: int,
    label: str,
    *,
    method: str = "manual",
    confidence: float | None = 1.0,
) -> dict[str, Any]:
    """写入人工或 LLM 改判；后续 BERT 全量重跑不会覆盖。"""
    from src.storage.db import get_store

    label = (label or "").strip().lower()
    if label not in _ALLOWED:
        raise ValueError("label 必须是 positive / neutral / negative / uncertain")
    method = (method or "manual").strip().lower()
    if method not in {"manual", "llm"}:
        raise ValueError("method 必须是 manual 或 llm")

    store = get_store()
    post = store.get_post(post_id)
    if not post:
        raise LookupError("帖子不存在")

    conf = 1.0 if confidence is None else float(confidence)
    conf = min(max(conf, 0.0), 1.0)
    store.update_post_sentiment(
        post_id,
        sentiment=_SCORE[label],
        sentiment_label=label,
        sentiment_method=method,
        sentiment_confidence=conf,
    )
    updated = store.get_post(post_id)
    assert updated is not None
    return updated


def llm_review_text(text: str) -> dict[str, Any]:
    """用 LLM 对单条文本做情感复判。"""
    from src.services.agent import AgentUnavailableError, chat_completion

    raw = (text or "").strip()
    if not raw:
        raise ValueError("文本不能为空")

    system = (
        "你是中文短文本情感标注员，面向 B 站评论/弹幕式口碑。"
        "只输出一个 JSON 对象，不要 Markdown，字段："
        '{"label":"positive|neutral|negative|uncertain","confidence":0到1的小数,"reason":"不超过30字"}。'
        "规则：反讽/玩梗拿不准用 uncertain；褒贬参半偏主语气；纯表情/无意义偏 neutral。"
    )
    user = f"待标注文本：\n{raw[:1500]}"
    try:
        result = chat_completion(system=system, user=user, history=None, max_tokens=200)
    except AgentUnavailableError:
        raise
    content = (result.get("content") or "").strip()
    parsed = _parse_llm_json(content)
    label = str(parsed.get("label", "")).strip().lower()
    if label not in _ALLOWED:
        raise ValueError(f"模型返回无法识别的标签: {content[:120]}")
    try:
        confidence = float(parsed.get("confidence", 0.7))
    except (TypeError, ValueError):
        confidence = 0.7
    return {
        "sentiment_label": label,
        "sentiment": _SCORE[label],
        "sentiment_method": "llm",
        "sentiment_confidence": round(min(max(confidence, 0.0), 1.0), 4),
        "confidence": round(min(max(confidence, 0.0), 1.0), 4),
        "reason": str(parsed.get("reason") or "")[:80],
        "provider": result.get("provider"),
        "model": result.get("model"),
        "raw": content[:300],
    }


def llm_review_post(post_id: int, *, apply: bool = True) -> dict[str, Any]:
    from src.storage.db import get_store

    store = get_store()
    post = store.get_post(post_id)
    if not post:
        raise LookupError("帖子不存在")
    judged = llm_review_text(post.get("text") or "")
    out: dict[str, Any] = {
        "post_id": post_id,
        "previous_label": post.get("sentiment_label"),
        "previous_method": post.get("sentiment_method"),
        **judged,
    }
    if apply:
        updated = apply_sentiment_override(
            post_id,
            judged["sentiment_label"],
            method="llm",
            confidence=judged["sentiment_confidence"],
        )
        out["post"] = updated
    return out


def _parse_llm_json(content: str) -> dict[str, Any]:
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{[^{}]+\}", text, re.S)
    if match:
        data = json.loads(match.group(0))
        if isinstance(data, dict):
            return data
    raise ValueError(f"无法解析模型 JSON: {content[:160]}")
