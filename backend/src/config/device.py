"""设备探测：优先 CUDA（RTX 5070 / sm_120）。"""

from __future__ import annotations

from functools import lru_cache
from typing import Any


@lru_cache(maxsize=1)
def get_device_info() -> dict[str, Any]:
    info: dict[str, Any] = {
        "torch_installed": False,
        "cuda_available": False,
        "device": "cpu",
        "gpu_name": None,
        "cuda_version": None,
        "arch_list": [],
        "torch_version": None,
    }
    try:
        import torch
    except ImportError:
        return info

    info["torch_installed"] = True
    info["torch_version"] = torch.__version__
    info["cuda_available"] = bool(torch.cuda.is_available())
    info["cuda_version"] = getattr(torch.version, "cuda", None)

    if info["cuda_available"]:
        info["device"] = "cuda"
        info["gpu_name"] = torch.cuda.get_device_name(0)
        try:
            info["arch_list"] = list(torch.cuda.get_arch_list())
        except Exception:
            info["arch_list"] = []
    return info


def resolve_device(preference: str = "auto") -> str:
    info = get_device_info()
    if preference == "cpu":
        return "cpu"
    if preference == "cuda":
        return "cuda" if info["cuda_available"] else "cpu"
    return "cuda" if info["cuda_available"] else "cpu"
