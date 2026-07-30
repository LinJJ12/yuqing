"""B 站采集质量门禁：视频标题过滤 + 评论去噪。"""

from __future__ import annotations

import re
from typing import Any

# 关键词搜索时跳过明显娱乐/番剧向标题（BV 直采不套用）
DEFAULT_TITLE_BLACKLIST: tuple[str, ...] = (
    "一口气看完",
    "规则怪谈",
    "全集",
    "番剧",
    "动漫",
    "二次元",
    "漫画改",
    "剧场版",
    "配音剧",
    "MAD",
    "AMV",
    "鬼畜",
    "剪辑合集",
    "高能名场面",
    "致敬经典",
    "同人",
    "手书",
    "MMD",
)

_EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001F9FF"
    "\U0001FA00-\U0001FAFF"
    "\u2600-\u27BF"
    "\uFE0F"
    "\u200D"
    "]+",
    flags=re.UNICODE,
)
_PUNCT_RE = re.compile(r"[\s\W_]+", re.UNICODE)
_REPEAT_RE = re.compile(r"(.)\1{5,}")  # 同一字符连续 ≥6
_ONLY_DIGIT_RE = re.compile(r"^[\d\s.]+$")


def _keyword_tokens(keyword: str) -> list[str]:
    raw = (keyword or "").strip()
    if not raw:
        return []
    parts = re.split(r"[\s,，、|/]+", raw)
    tokens = [p.strip() for p in parts if len(p.strip()) >= 2]
    if raw not in tokens and len(raw) >= 2:
        tokens.insert(0, raw)
    return tokens


def title_reject_reason(
    title: str,
    *,
    keyword: str | None = None,
    blacklist: list[str] | tuple[str, ...] | None = None,
    require_keyword_hit: bool = True,
) -> str | None:
    """若不通过返回原因，通过返回 None。"""
    text = re.sub(r"<[^>]+>", "", title or "").strip()
    if not text:
        return "空标题"
    bl = blacklist if blacklist is not None else DEFAULT_TITLE_BLACKLIST
    lower = text.lower()
    for word in bl:
        w = (word or "").strip()
        if not w:
            continue
        if w.lower() in lower or w in text:
            return f"标题命中黑名单「{w}」"
    if require_keyword_hit and keyword:
        tokens = _keyword_tokens(keyword)
        if tokens and not any(t in text for t in tokens):
            return "标题未命中搜索词"
    return None


def filter_video_candidates(
    videos: list[dict[str, Any]],
    *,
    keyword: str | None,
    max_videos: int,
    blacklist: list[str] | tuple[str, ...] | None = None,
    require_keyword_hit: bool = True,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """返回 (accepted, rejected_with_reason)。"""
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for v in videos:
        bvid = str(v.get("bvid") or "")
        key = bvid or f"aid:{v.get('aid')}"
        if key in seen:
            continue
        seen.add(key)
        reason = title_reject_reason(
            str(v.get("title") or ""),
            keyword=keyword,
            blacklist=blacklist,
            require_keyword_hit=require_keyword_hit,
        )
        if reason:
            rejected.append({**v, "reject_reason": reason})
            continue
        accepted.append(v)
        if len(accepted) >= max_videos:
            break
    return accepted, rejected


def comment_noise_reason(text: str, *, min_chars: int = 2) -> str | None:
    """明显噪声评论返回原因，否则 None。"""
    raw = (text or "").strip()
    if not raw:
        return "空评论"
    # 去掉表情与空白后再判长度
    no_emoji = _EMOJI_RE.sub("", raw)
    compact = _PUNCT_RE.sub("", no_emoji)
    if not compact:
        return "纯表情/符号"
    if len(compact) < max(1, min_chars):
        return "过短"
    if _ONLY_DIGIT_RE.match(raw) and len(compact) <= 6:
        return "纯数字刷评"
    if _REPEAT_RE.search(compact):
        return "重复刷评"
    # 仅「哈/呵/嘿/6/啊」等刷屏
    if re.fullmatch(r"[哈呵嘿啊哦嗯6]+", compact) and len(compact) >= 4:
        return "无意义刷评"
    return None


def denoise_comments(
    comments: list[dict[str, Any]],
    *,
    min_chars: int = 2,
    drop_duplicates: bool = True,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """过滤噪声；返回 (kept, stats_by_reason)。"""
    kept: list[dict[str, Any]] = []
    stats: dict[str, int] = {}
    seen_text: set[str] = set()
    for c in comments:
        text = str(c.get("text") or "")
        reason = comment_noise_reason(text, min_chars=min_chars)
        if reason:
            stats[reason] = stats.get(reason, 0) + 1
            continue
        norm = re.sub(r"\s+", "", text)
        if drop_duplicates and norm in seen_text:
            stats["重复正文"] = stats.get("重复正文", 0) + 1
            continue
        seen_text.add(norm)
        kept.append(c)
    return kept, stats
