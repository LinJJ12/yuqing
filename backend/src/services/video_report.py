"""单视频口碑报告：按 B 站 bvid 聚合评论情感与关键词。"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from src.services.bilibili_collect import normalize_bvid
from src.services.forecast import get_alert_keywords
from src.services.topics import get_topic_analyzer
from src.storage.db import get_store


def list_video_summaries(*, limit: int = 50) -> list[dict[str, Any]]:
    return get_store().list_bilibili_videos(limit=limit)


def _likes(post: dict[str, Any]) -> int:
    eng = post.get("engagement") or {}
    try:
        return int(eng.get("likes") or 0)
    except (TypeError, ValueError):
        return 0


def _sentiment_breakdown(posts: list[dict[str, Any]]) -> dict[str, Any]:
    by_label = Counter((p.get("sentiment_label") or "unknown") for p in posts)
    by_method = Counter((p.get("sentiment_method") or "unknown") for p in posts)
    breakdown = [
        {"label": label, "method": "all", "count": count}
        for label, count in sorted(by_label.items(), key=lambda x: (-x[1], x[0]))
    ]
    # 与全局报告兼容：再按 method 细分
    method_rows = []
    for p in posts:
        method_rows.append(
            (
                p.get("sentiment_label") or "unknown",
                p.get("sentiment_method") or "unknown",
            )
        )
    pair = Counter(method_rows)
    detailed = [
        {"label": lab, "method": meth, "count": cnt}
        for (lab, meth), cnt in sorted(pair.items(), key=lambda x: (-x[1], x[0][0], x[0][1]))
    ]
    bert_done = sum(1 for p in posts if p.get("sentiment_method") == "bert")
    return {
        "breakdown": detailed or breakdown,
        "by_label": dict(by_label),
        "by_method": dict(by_method),
        "bert_done": bert_done,
        "total": len(posts),
    }


def _rule_conclusion(
    *,
    total: int,
    by_label: dict[str, int],
    top_words: list[dict[str, Any]],
    keyword_hits: list[str],
) -> str:
    if total <= 0:
        return "暂无该视频的评论数据，请先在监测页按 BV 采集。"
    pos = by_label.get("positive", 0)
    neu = by_label.get("neutral", 0)
    neg = by_label.get("negative", 0)
    pos_r = pos / total
    neg_r = neg / total
    if neg_r >= 0.45:
        tone = "整体偏负"
    elif pos_r >= 0.45:
        tone = "整体偏正"
    elif abs(pos_r - neg_r) < 0.12:
        tone = "褒贬接近、整体偏中性"
    else:
        tone = "情绪分化明显"

    parts = [
        f"共分析 {total} 条评论：正面 {pos}（{pos_r:.0%}）、"
        f"中性 {neu}（{neu / total:.0%}）、负面 {neg}（{neg_r:.0%}）。"
        f"{tone}。"
    ]
    if top_words:
        words = "、".join(str(w.get("name")) for w in top_words[:6] if w.get("name"))
        if words:
            parts.append(f"高频词集中在：{words}。")
    if keyword_hits:
        parts.append(f"敏感词命中：{'、'.join(keyword_hits[:8])}。")
    if neg_r >= 0.35:
        parts.append("建议关注差评集中点，再决定是否需要回复或调整内容。")
    elif pos_r >= 0.5:
        parts.append("观众反馈偏积极，可提炼好评点用于简介或后续选题。")
    else:
        parts.append("建议结合负面样例与高频词，定位具体槽点后再做内容迭代。")
    return "".join(parts)


def _scoped_alerts(posts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    keywords = get_alert_keywords()
    alerts: list[dict[str, Any]] = []
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
                "title": f"负面/敏感评论 · {post.get('author') or '匿名'}",
                "message": text[:120],
                "keywords": hit,
                "created_at": post.get("fetched_at") or post.get("published_at"),
                "post_id": post["id"],
            }
        )
    severity_rank = {"high": 0, "medium": 1, "low": 2}
    alerts.sort(key=lambda a: (severity_rank.get(a["severity"], 9), a.get("created_at") or ""))
    return alerts[:30]


def build_video_report(bvid_or_url: str, *, sample_limit: int = 8) -> dict[str, Any]:
    bvid = normalize_bvid(bvid_or_url) or (bvid_or_url or "").strip()
    if not bvid:
        raise ValueError("请提供有效的 BV 号或视频链接")

    posts = get_store().list_posts_by_bvid(bvid, limit=2000)
    if not posts:
        return {
            "bvid": bvid,
            "video_title": "",
            "aid": None,
            "source_url": f"https://www.bilibili.com/video/{bvid}",
            "generated_for": f"视频口碑报告 · {bvid}",
            "overview": {"total_posts": 0, "by_sentiment": [], "by_day": []},
            "sentiment": {
                "breakdown": [],
                "by_label": {},
                "bert_done": 0,
                "total": 0,
            },
            "word_cloud": [],
            "keyword_topics": [],
            "alerts": {"items": [], "total": 0, "high": 0},
            "sample_posts": [],
            "conclusion": "暂无该视频的评论数据，请先在监测页按 BV 采集。",
            "notes": [
                "范围：raw.extra.bvid 匹配的评论。",
                "可先到监测页贴 BV 采集，再到情感页跑 BERT 提升标注质量。",
            ],
        }

    first = posts[0]
    extra = (first.get("raw") or {}).get("extra") or {}
    video_title = extra.get("video_title") or first.get("topic") or ""
    aid = extra.get("aid")
    source_url = f"https://www.bilibili.com/video/{bvid}"

    sentiment = _sentiment_breakdown(posts)
    by_label = sentiment["by_label"]
    by_day: dict[str, int] = defaultdict(int)
    for p in posts:
        day = (p.get("fetched_at") or p.get("published_at") or "")[:10]
        if day:
            by_day[day] += 1

    texts = [p.get("text") or "" for p in posts if (p.get("text") or "").strip()]
    analyzer = get_topic_analyzer()
    word_cloud = analyzer.word_cloud(texts, top_k=30) if texts else []
    keyword_topics = analyzer.keyword_topics(texts, top_k=8) if texts else []

    alerts = _scoped_alerts(posts)
    keyword_hits = sorted({w for a in alerts for w in (a.get("keywords") or [])})

    # 样例：负面优先，再按点赞
    neg = sorted(
        [p for p in posts if p.get("sentiment_label") == "negative"],
        key=_likes,
        reverse=True,
    )
    pos = sorted(
        [p for p in posts if p.get("sentiment_label") == "positive"],
        key=_likes,
        reverse=True,
    )
    rest = sorted(posts, key=_likes, reverse=True)
    samples: list[dict[str, Any]] = []
    seen: set[int] = set()
    for bucket in (neg[: sample_limit // 2], pos[: sample_limit // 2], rest):
        for p in bucket:
            pid = p.get("id")
            if pid in seen:
                continue
            seen.add(pid)
            samples.append(
                {
                    "id": pid,
                    "author": p.get("author") or "",
                    "text": (p.get("text") or "")[:200],
                    "sentiment_label": p.get("sentiment_label"),
                    "likes": _likes(p),
                    "source_url": p.get("source_url"),
                }
            )
            if len(samples) >= sample_limit:
                break
        if len(samples) >= sample_limit:
            break

    conclusion = _rule_conclusion(
        total=len(posts),
        by_label=by_label,
        top_words=word_cloud,
        keyword_hits=keyword_hits,
    )

    return {
        "bvid": bvid,
        "video_title": video_title,
        "aid": aid,
        "source_url": source_url,
        "generated_for": f"视频口碑报告 · {video_title or bvid}",
        "overview": {
            "total_posts": len(posts),
            "by_sentiment": [
                {"label": k, "count": v} for k, v in sorted(by_label.items(), key=lambda x: -x[1])
            ],
            "by_day": [{"day": d, "count": by_day[d]} for d in sorted(by_day.keys())],
        },
        "sentiment": sentiment,
        "word_cloud": word_cloud,
        "keyword_topics": keyword_topics,
        "alerts": {
            "items": alerts,
            "total": len(alerts),
            "high": sum(1 for a in alerts if a["severity"] == "high"),
        },
        "sample_posts": samples,
        "conclusion": conclusion,
        "notes": [
            f"范围：bvid={bvid} 下 {len(posts)} 条评论。",
            "结论为规则摘要；可到助手页结合库内数据追问细节。",
            "情感以已写入库的标注为准；未跑 BERT 时多为词典结果。",
        ],
    }
