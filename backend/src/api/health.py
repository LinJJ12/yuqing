from __future__ import annotations

from src.config.device import get_device_info, resolve_device
from src.config.settings import settings
from src.lib.http import ok
from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health/live")
def health_live():
    return ok({"status": "alive"})


@router.get("/health/ready")
def health_ready():
    device_info = get_device_info()
    resolved = resolve_device(settings.device_preference)
    ready = device_info["torch_installed"]
    return ok(
        {
            "status": "ready" if ready else "degraded",
            "cuda": device_info["cuda_available"],
            "device": resolved,
            "gpu_name": device_info["gpu_name"],
            "torch_version": device_info["torch_version"],
            "cuda_version": device_info["cuda_version"],
            "arch_list": device_info["arch_list"],
            "sentiment_model_id": settings.sentiment_model_id,
            "api_port": settings.port,
            "stack": {
                "sentiment": "lexicon + chinese-roberta → positive/neutral/negative (GPU)",
                "topics": "wordcloud + BERTopic (Ollama local embed)",
                "forecast": "rolling-mean / Prophet",
                "spread": "growth-rate + peak (no SIR)",
            },
        }
    )
