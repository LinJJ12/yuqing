"""演示就绪探测：情感模型缓存、Ollama、OpenAI 兼容 LLM（不强制加载大模型）。"""

from __future__ import annotations

from typing import Any

import httpx

from src.config.device import get_device_info, resolve_device
from src.config.settings import settings
from src.services.sentiment import get_sentiment_analyzer


def _probe_sentiment_cache() -> dict[str, Any]:
    model_id = settings.sentiment_model_id
    analyzer = get_sentiment_analyzer()
    if analyzer.ready:
        return {
            "ok": True,
            "cached": True,
            "loaded": True,
            "model_id": model_id,
            "device": analyzer.status.get("device"),
            "message": "情感模型已加载到内存",
            "hint": "",
        }
    try:
        from transformers import AutoConfig

        AutoConfig.from_pretrained(model_id, local_files_only=True)
        return {
            "ok": True,
            "cached": True,
            "loaded": False,
            "model_id": model_id,
            "device": None,
            "message": "本地缓存已就绪（首次分析会加载到 GPU/CPU）",
            "hint": "可到「情感」页点一次预览以预热模型。",
        }
    except Exception:
        return {
            "ok": False,
            "cached": False,
            "loaded": False,
            "model_id": model_id,
            "device": None,
            "message": "本地无缓存，首次分析需联网下载",
            "hint": (
                f"先设置 HF_ENDPOINT={settings.hf_endpoint or 'https://hf-mirror.com'}，"
                "再运行：uv run python backend/scripts/prefetch_models.py"
            ),
        }


def _probe_ollama() -> dict[str, Any]:
    base = settings.ollama_base_url.rstrip("/")
    model = settings.ollama_embed_model
    if settings.embedding_backend != "ollama":
        return {
            "ok": True,
            "reachable": False,
            "model_present": False,
            "backend": settings.embedding_backend,
            "base_url": base,
            "model": settings.embedding_model_id,
            "message": "当前嵌入后端不是 Ollama",
            "hint": "BERTopic 将走 HuggingFace 嵌入，首次也可能需下载。",
        }
    try:
        # trust_env=False：避免 Windows 系统代理劫持本机 Ollama
        with httpx.Client(timeout=2.5, trust_env=False) as client:
            tags = client.get(f"{base}/api/tags")
            tags.raise_for_status()
            names = [m.get("name", "") for m in (tags.json().get("models") or [])]
        present = any(
            name == model or name.startswith(f"{model}:") or model in name
            for name in names
        )
        if present:
            return {
                "ok": True,
                "reachable": True,
                "model_present": True,
                "backend": "ollama",
                "base_url": base,
                "model": model,
                "message": f"Ollama 可用，已找到模型 {model}",
                "hint": "",
            }
        return {
            "ok": False,
            "reachable": True,
            "model_present": False,
            "backend": "ollama",
            "base_url": base,
            "model": model,
            "installed_models": names[:12],
            "message": f"Ollama 在线，但未找到嵌入模型 {model}",
            "hint": f"执行：ollama pull {model}",
        }
    except Exception as exc:
        return {
            "ok": False,
            "reachable": False,
            "model_present": False,
            "backend": "ollama",
            "base_url": base,
            "model": model,
            "message": f"无法连接 Ollama（{base}）",
            "hint": "先启动 Ollama 桌面版/服务，主题聚类才可用；词云仍可单独用。",
            "error": str(exc)[:160],
        }


def _probe_llm() -> dict[str, Any]:
    configured = settings.has_cloud_llm
    return {
        "ok": True,
        "configured": configured,
        "model": settings.llm_model if configured else None,
        "base_url": settings.llm_base_url if configured else None,
        "message": (
            "已配置 OpenAI 兼容 LLM"
            if configured
            else "未配置 OPENAI_API_KEY（报告 AI 摘要 / Agent 将跳过或回退 Ollama）"
        ),
        "hint": (
            ""
            if configured
            else "在 backend/.env 设置 OPENAI_API_KEY / OPENAI_BASE_URL / OPENAI_MODEL（火山、百炼等均可）。"
        ),
    }


def _probe_bilibili() -> dict[str, Any]:
    """仅探测是否配置了 SESSDATA，绝不回传 Cookie 内容。"""
    from src.services.bilibili_collect import _has_sessdata

    configured = _has_sessdata()
    return {
        "ok": configured,
        "configured": configured,
        "message": (
            "已配置 B 站登录态（SESSDATA），评论采集更稳定"
            if configured
            else "未配置 BILIBILI_SESSDATA，评论量可能偏少或易被风控"
        ),
        "hint": (
            ""
            if configured
            else "在 backend/.env 填写 BILIBILI_SESSDATA（可从浏览器 Cookie 复制），保存后重启后端。"
        ),
    }


def build_readiness() -> dict[str, Any]:
    device_info = get_device_info()
    sentiment = _probe_sentiment_cache()
    ollama = _probe_ollama()
    llm = _probe_llm()
    bilibili = _probe_bilibili()
    try:
        from src.services.agent import agent_status

        agent = agent_status()
    except Exception as exc:
        agent = {
            "ready": False,
            "message": f"Agent 状态探测失败: {exc}",
            "hint": "检查 OPENAI_* / Ollama Chat 配置",
        }

    blockers: list[str] = []
    warnings: list[str] = []
    if not device_info["torch_installed"]:
        blockers.append("未安装 torch，无法跑情感模型")
    if not sentiment["cached"]:
        warnings.append("情感模型未缓存，演示前请先预取或确保可访问 HF 镜像")
    if not bilibili["configured"]:
        warnings.append("未配置 B 站 Cookie（BILIBILI_SESSDATA），演示采集评论量可能偏少")
    if settings.embedding_backend == "ollama" and not ollama["ok"]:
        warnings.append("Ollama/嵌入模型未就绪，BERTopic 可能失败（词云仍可用）")
    if not agent.get("ready"):
        warnings.append("Agent 未就绪（问答/简报需 OpenAI 兼容 Key 或 Ollama Chat）")

    demo_ok = device_info["torch_installed"] and (
        sentiment["cached"] or sentiment["loaded"]
    )
    return {
        "demo_ready": demo_ok and (ollama["ok"] or settings.embedding_backend != "ollama"),
        "demo_ready_core": demo_ok,
        "blockers": blockers,
        "warnings": warnings,
        "device": {
            "cuda": device_info["cuda_available"],
            "resolved": resolve_device(settings.device_preference),
            "gpu_name": device_info["gpu_name"],
            "torch_version": device_info["torch_version"],
        },
        "sentiment": sentiment,
        "bilibili": bilibili,
        "ollama": ollama,
        "llm": llm,
        # 兼容旧前端字段名
        "deepseek": llm,
        "agent": agent,
    }
