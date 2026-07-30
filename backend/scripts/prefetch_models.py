"""预取情感模型到本机 HuggingFace 缓存，避免演示时现场下载失败。"""

from __future__ import annotations

import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from src.config.settings import settings


def main() -> None:
    if settings.hf_endpoint:
        os.environ["HF_ENDPOINT"] = settings.hf_endpoint.rstrip("/")
    model_id = settings.sentiment_model_id
    print(f"HF_ENDPOINT={os.environ.get('HF_ENDPOINT', '(default)')}")
    print(f"预取情感模型: {model_id}")
    from transformers import AutoConfig, AutoModelForSequenceClassification, AutoTokenizer

    AutoConfig.from_pretrained(model_id)
    AutoTokenizer.from_pretrained(model_id)
    AutoModelForSequenceClassification.from_pretrained(model_id)
    print("OK — 已写入本机 HF 缓存。可到设置页刷新「情感模型」状态。")
    print("可选：预热 GPU —— 在情感页点一次「预测」。")


if __name__ == "__main__":
    main()
