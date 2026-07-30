"""轻量舆情 Agent：问答 + 简报（云端 OpenAI 兼容优先，否则 Ollama Chat）。"""

from __future__ import annotations

import json
from typing import Any

import httpx

from src.config.settings import settings
from src.services.forecast import build_report_summary, detect_alerts
from src.storage.db import get_store


class AgentUnavailableError(RuntimeError):
    """未配置可用 LLM。"""


def build_opinion_context(limit_posts: int = 8) -> dict[str, Any]:
    store = get_store()
    overview = store.overview()
    sentiment = store.sentiment_stats()
    alerts_all = detect_alerts()
    alerts = alerts_all[:8]
    posts = store.list_posts(limit=200)
    negative = [
        {
            "id": p["id"],
            "topic": p.get("topic"),
            "platform": p.get("platform"),
            "text": (p.get("text") or "")[:160],
            "sentiment_label": p.get("sentiment_label"),
        }
        for p in posts
        if p.get("sentiment_label") == "negative"
    ][:limit_posts]
    recent = [
        {
            "id": p["id"],
            "topic": p.get("topic"),
            "platform": p.get("platform"),
            "text": (p.get("text") or "")[:120],
            "sentiment_label": p.get("sentiment_label"),
        }
        for p in posts[:limit_posts]
    ]
    return {
        "overview": {
            "total_posts": overview.get("total_posts"),
            "by_topic": overview.get("by_topic", [])[:8],
            "by_sentiment": overview.get("by_sentiment", []),
        },
        "sentiment": sentiment,
        "alerts": {
            "total": len(alerts_all),
            "high": sum(1 for a in alerts_all if a.get("severity") == "high"),
            "items": [
                {
                    "severity": a.get("severity"),
                    "title": a.get("title"),
                    "message": (a.get("message") or "")[:120],
                }
                for a in alerts
            ],
        },
        "negative_samples": negative,
        "recent_samples": recent,
        "alert_keywords": build_report_summary(with_prophet=False).get("alert_keywords"),
    }


def _context_prompt(ctx: dict[str, Any]) -> str:
    return (
        "以下是校园舆情系统当前库内统计与样例（只读，请基于此回答，勿编造库外事实）：\n"
        + json.dumps(ctx, ensure_ascii=False, indent=2)
    )


def _llm_provider() -> dict[str, Any]:
    if settings.has_cloud_llm:
        return {
            "name": "openai-compatible",
            "base_url": settings.llm_base_url,
            "api_key": settings.llm_api_key,
            "model": settings.llm_model,
        }
    return {
        "name": "ollama",
        "base_url": settings.ollama_base_url.rstrip("/") + "/v1",
        "api_key": "ollama",
        "model": settings.ollama_chat_model,
    }


def _chat_completion(
    *,
    system: str,
    user: str,
    history: list[dict[str, str]] | None = None,
    max_tokens: int = 1200,
) -> dict[str, Any]:
    provider = _llm_provider()
    messages: list[dict[str, str]] = [{"role": "system", "content": system}]
    if history:
        for turn in history[-6:]:
            role = turn.get("role")
            content = (turn.get("content") or "").strip()
            if role in {"user", "assistant"} and content:
                messages.append({"role": role, "content": content[:2000]})
    messages.append({"role": "user", "content": user})

    try:
        from openai import OpenAI

        client = OpenAI(
            api_key=provider["api_key"],
            base_url=provider["base_url"],
            timeout=90.0,
        )
        resp = client.chat.completions.create(
            model=provider["model"],
            messages=messages,
            temperature=0.4,
            max_tokens=max_tokens,
        )
        text = (resp.choices[0].message.content or "").strip()
        if not text:
            raise RuntimeError("模型返回空内容")
        return {
            "provider": provider["name"],
            "model": provider["model"],
            "content": text,
        }
    except Exception as exc:
        if provider["name"] == "openai-compatible":
            raise AgentUnavailableError(f"云端 LLM 调用失败: {exc}") from exc
        try:
            with httpx.Client(timeout=2.5) as http:
                http.get(f"{settings.ollama_base_url.rstrip('/')}/api/tags").raise_for_status()
        except Exception:
            raise AgentUnavailableError(
                "未配置 OPENAI_API_KEY，且无法连接本机 Ollama。"
                "请在 backend/.env 配置 OpenAI 兼容接口（火山/百炼等），"
                "或启动 Ollama 并拉取聊天模型"
                f"（如 ollama pull {settings.ollama_chat_model}）。"
            ) from exc
        raise AgentUnavailableError(
            f"Ollama Chat 调用失败（模型={provider['model']}）: {exc}。"
            f"可执行：ollama pull {settings.ollama_chat_model}"
        ) from exc


def agent_chat(
    question: str,
    *,
    history: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    q = (question or "").strip()
    if not q:
        raise ValueError("问题不能为空")
    ctx = build_opinion_context()
    system = (
        "你是校园舆情分析助手。根据提供的统计与样例回答用户问题，"
        "语气客观简洁，可给 1～3 条可执行建议。若数据不足请明确说明。"
    )
    user = _context_prompt(ctx) + f"\n\n用户问题：{q}"
    result = _chat_completion(system=system, user=user, history=history, max_tokens=900)
    return {
        **result,
        "question": q,
        "context_digest": {
            "total_posts": ctx["overview"].get("total_posts"),
            "alerts_high": ctx["alerts"].get("high"),
            "topics": ctx["overview"].get("by_topic"),
        },
    }


def agent_brief() -> dict[str, Any]:
    ctx = build_opinion_context(limit_posts=10)
    summary = build_report_summary(with_prophet=False)
    system = (
        "你是校园舆情简报作者。请写一篇 250～450 字的中文简报，"
        "结构包含：总体态势、主要话题、风险与预警、建议措施。"
        "只基于给定数据，不要编造具体人名或未出现的事件。"
    )
    user = (
        _context_prompt(ctx)
        + "\n\n报告摘要字段：\n"
        + json.dumps(
            {
                "generated_for": summary.get("generated_for"),
                "notes": summary.get("notes"),
                "prophet": summary.get("prophet"),
            },
            ensure_ascii=False,
        )
        + "\n\n请直接输出简报正文。"
    )
    result = _chat_completion(system=system, user=user, history=None, max_tokens=1400)
    return {
        **result,
        "title": "校园舆情简报（Agent）",
        "context_digest": {
            "total_posts": ctx["overview"].get("total_posts"),
            "alerts_total": ctx["alerts"].get("total"),
            "alerts_high": ctx["alerts"].get("high"),
        },
    }


def agent_status() -> dict[str, Any]:
    has_cloud = settings.has_cloud_llm
    ollama_ok = False
    try:
        with httpx.Client(timeout=2.0) as http:
            r = http.get(f"{settings.ollama_base_url.rstrip('/')}/api/tags")
            r.raise_for_status()
            ollama_ok = True
    except Exception:
        ollama_ok = False
    ready = has_cloud or ollama_ok
    return {
        "ready": ready,
        "openai_configured": has_cloud,
        "ollama_reachable": ollama_ok,
        "preferred": "openai-compatible" if has_cloud else ("ollama" if ollama_ok else "none"),
        "openai_model": settings.llm_model if has_cloud else None,
        "openai_base_url": settings.llm_base_url if has_cloud else None,
        "ollama_chat_model": settings.ollama_chat_model,
        "message": (
            "Agent 可用"
            if ready
            else "请配置 OPENAI_API_KEY（OpenAI 兼容）或启动 Ollama 聊天模型"
        ),
        "hint": (
            ""
            if ready
            else f"填写 OPENAI_API_KEY / BASE_URL / MODEL，或 ollama pull {settings.ollama_chat_model}"
        ),
    }
