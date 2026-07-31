"""单视频口碑报告：按 B 站 bvid 聚合评论情感与关键词。"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from typing import Any

from src.services.bilibili_collect import normalize_bvid
from src.services.forecast import alert_from_post, get_alert_keywords
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
    unknown = int(by_label.get("unknown") or 0)
    labeled = len(posts) - unknown
    pending_ratio = (unknown / len(posts)) if posts else 0.0
    # 未标注才算「未完成」；已人工/LLM 改判的不算 pending（勿仅用 bert_done < total）
    return {
        "breakdown": detailed or breakdown,
        "by_label": dict(by_label),
        "by_method": dict(by_method),
        "bert_done": bert_done,
        "total": len(posts),
        "labeled": labeled,
        "pending": unknown,
        "pending_ratio": round(pending_ratio, 4),
        "sentiment_pending": unknown > 0,
    }


def _rule_conclusion(
    *,
    total: int,
    by_label: dict[str, int],
    top_words: list[dict[str, Any]],
    keyword_hits: list[str],
    bert_done: int = 0,
) -> str:
    if total <= 0:
        return "暂无该视频的评论数据，请先在监测页按 BV 采集。"

    unknown = int(by_label.get("unknown") or 0)
    labeled = max(total - unknown, 0)
    pending = unknown > 0
    prefix = ""
    if pending:
        prefix = f"情感分析未完成（已标注 {labeled}/{total}，BERT {bert_done}）。"

    if labeled <= 0:
        return prefix + "请先到「情感」页完成分析后再看口碑定论。"

    pos = by_label.get("positive", 0)
    neu = by_label.get("neutral", 0)
    neg = by_label.get("negative", 0)
    unc = by_label.get("uncertain", 0)
    pos_r = pos / labeled
    neg_r = neg / labeled
    if neg_r >= 0.45:
        tone = "整体偏负"
    elif pos_r >= 0.45:
        tone = "整体偏正"
    elif abs(pos_r - neg_r) < 0.12:
        tone = "褒贬接近、整体偏中性"
    else:
        tone = "情绪分化明显"

    parts = [
        prefix,
        f"基于已标注 {labeled} 条（共 {total}）：正面 {pos}（{pos_r:.0%}）、"
        f"中性 {neu}（{neu / labeled:.0%}）、负面 {neg}（{neg_r:.0%}）"
        + (f"、不确定 {unc}（{unc / labeled:.0%}）" if unc else "")
        + f"。{tone}。",
    ]
    if pending:
        parts.append("以下倾向仅供参考，跑完情感后再下定论。")
    if top_words:
        words = "、".join(str(w.get("name")) for w in top_words[:6] if w.get("name"))
        if words:
            parts.append(f"高频词集中在：{words}。")
    if keyword_hits:
        parts.append(f"敏感词命中：{'、'.join(keyword_hits[:8])}。")
    if not pending:
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
        item = alert_from_post(post, keywords, title_prefix="负面/敏感评论")
        if item:
            alerts.append(item)
    severity_rank = {"high": 0, "medium": 1, "low": 2}
    alerts.sort(key=lambda a: (severity_rank.get(a["severity"], 9), a.get("created_at") or ""))
    return alerts[:30]


def build_video_report(
    bvid_or_url: str,
    *,
    sample_limit: int = 8,
    with_ai: bool = False,
) -> dict[str, Any]:
    bvid = normalize_bvid(bvid_or_url) or (bvid_or_url or "").strip()
    if not bvid:
        raise ValueError("请提供有效的 BV 号或视频链接")

    empty_conclusion = "暂无该视频的评论数据，请先在监测页按 BV 采集。"
    posts = get_store().list_posts_by_bvid(bvid, limit=2000)
    if not posts:
        report = {
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
                "labeled": 0,
                "pending": 0,
                "pending_ratio": 0.0,
                "sentiment_pending": False,
            },
            "word_cloud": [],
            "keyword_topics": [],
            "alerts": {"items": [], "total": 0, "high": 0},
            "sample_posts": [],
            "rule_conclusion": empty_conclusion,
            "conclusion": empty_conclusion,
            "conclusion_source": "rule",
            "sentiment_pending": False,
            "notes": [
                "范围：raw.extra.bvid 匹配的评论。",
                "采集入库后会自动排队 BERT；也可在情感页全量重跑。",
            ],
        }
        if with_ai:
            return apply_video_ai_conclusion(report)
        return report

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
        bert_done=int(sentiment.get("bert_done") or 0),
    )
    sentiment_pending = bool(sentiment.get("sentiment_pending"))
    notes = [
        f"范围：bvid={bvid} 下 {len(posts)} 条评论。",
        "默认结论为规则摘要；可点「AI 生成观众反馈」调用 LLM 重写。",
        "情感以库内标注为准；BERT 低置信为 uncertain；未跑 BERT 时预警降权。",
    ]
    if sentiment_pending:
        notes.insert(
            0,
            (
                f"情感分析未完成：已标注 {sentiment.get('labeled', 0)}/{len(posts)}"
                f"（BERT {sentiment.get('bert_done', 0)}）。请到「情感」页确认进度后再下定论。"
            ),
        )

    report = {
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
        "rule_conclusion": conclusion,
        "conclusion": conclusion,
        "conclusion_source": "rule",
        "sentiment_pending": sentiment_pending,
        "notes": notes,
    }
    if with_ai:
        return apply_video_ai_conclusion(report)
    return report


def generate_video_ai_conclusion(report: dict[str, Any]) -> dict[str, Any]:
    """基于口碑统计与样例调用 LLM，生成差异化观众反馈（云端或 Ollama）。"""
    if not (report.get("overview") or {}).get("total_posts"):
        return {
            "enabled": False,
            "summary": None,
            "message": "暂无评论，无法生成 AI 口碑",
            "provider": None,
            "model": None,
        }

    payload = {
        "bvid": report.get("bvid"),
        "video_title": report.get("video_title"),
        "overview": report.get("overview"),
        "sentiment": {
            "by_label": (report.get("sentiment") or {}).get("by_label"),
            "bert_done": (report.get("sentiment") or {}).get("bert_done"),
            "total": (report.get("sentiment") or {}).get("total"),
        },
        "word_cloud": (report.get("word_cloud") or [])[:12],
        "keyword_topics": (report.get("keyword_topics") or [])[:6],
        "alerts": {
            "total": (report.get("alerts") or {}).get("total"),
            "high": (report.get("alerts") or {}).get("high"),
            "samples": [
                {"severity": a.get("severity"), "message": a.get("message")}
                for a in ((report.get("alerts") or {}).get("items") or [])[:5]
            ],
        },
        "sample_posts": [
            {
                "sentiment_label": p.get("sentiment_label"),
                "text": p.get("text"),
                "likes": p.get("likes"),
            }
            for p in (report.get("sample_posts") or [])[:8]
        ],
        "rule_conclusion": report.get("rule_conclusion") or report.get("conclusion"),
    }
    system = (
        "你是 B 站视频观众反馈分析师。根据给定统计与评论样例，写一段 180～320 字中文"
        "「观众反馈」口碑结论。要求：\n"
        "1) 点明总体口碑倾向，并引用具体比例或样例槽点/亮点（勿编造未出现的内容）；\n"
        "2) 归纳 2～4 个具体争议点或好评点，避免空泛套话；\n"
        "3) 结尾给 UP/运营 1～2 条可执行建议；\n"
        "4) 不要使用「根据以上数据」「综上所述」等套话开头，直接写结论。"
    )
    user = (
        "视频口碑材料（JSON）：\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
        + "\n\n请直接输出观众反馈正文。"
    )
    try:
        # 懒加载，避免与 agent.build_opinion_context 循环导入
        from src.services.agent import AgentUnavailableError, chat_completion
    except Exception as exc:
        return {
            "enabled": False,
            "summary": None,
            "message": f"无法加载 LLM 模块: {exc}",
            "provider": None,
            "model": None,
        }

    try:
        result = chat_completion(system=system, user=user, history=None, max_tokens=900)
        text = (result.get("content") or "").strip()
        if not text:
            return {
                "enabled": True,
                "summary": None,
                "message": "模型返回空内容",
                "provider": result.get("provider"),
                "model": result.get("model"),
            }
        return {
            "enabled": True,
            "summary": text,
            "message": "ok",
            "provider": result.get("provider"),
            "model": result.get("model"),
        }
    except AgentUnavailableError as exc:
        return {
            "enabled": False,
            "summary": None,
            "message": str(exc),
            "provider": None,
            "model": None,
        }
    except Exception as exc:
        return {
            "enabled": True,
            "summary": None,
            "message": str(exc),
            "provider": None,
            "model": None,
        }


def apply_video_ai_conclusion(report: dict[str, Any]) -> dict[str, Any]:
    """把 AI 结论写回报告；失败则保留规则结论。"""
    out = dict(report)
    if "rule_conclusion" not in out:
        out["rule_conclusion"] = out.get("conclusion")
    ai = generate_video_ai_conclusion(out)
    out["ai"] = ai
    if ai.get("summary"):
        out["conclusion"] = ai["summary"]
        out["conclusion_source"] = "llm"
        notes = list(out.get("notes") or [])
        notes = [n for n in notes if "规则摘要" not in n and "AI 生成" not in n]
        notes.insert(
            0,
            f"结论来源：LLM（{ai.get('provider')}/{ai.get('model')}）。下方「数据速览」为规则摘要。",
        )
        out["notes"] = notes
    else:
        out["conclusion_source"] = "rule"
        out.setdefault("notes", [])
        msg = ai.get("message") or "AI 不可用"
        if not any(msg in str(n) for n in out["notes"]):
            out["notes"] = [f"AI 口碑未生成：{msg}", *out["notes"]]
    return out

