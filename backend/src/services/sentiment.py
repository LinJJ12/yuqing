"""中文 BERT 情感分析：正 / 中 / 负（GPU 优先）。"""

from __future__ import annotations

import logging
import os
import threading
import time
from typing import Any

from src.config.settings import settings
from src.config.device import resolve_device

logger = logging.getLogger(__name__)

_LABEL_MAP = {
    "positive": "positive",
    "negative": "negative",
    "neutral": "neutral",
    "pos": "positive",
    "neg": "negative",
    "正面": "positive",
    "负面": "negative",
    "中性": "neutral",
    "label_1": "positive",
    "label_0": "negative",
}


class SentimentAnalyzer:
    def __init__(self) -> None:
        self._pipe = None
        self._device = "cpu"
        self._lock = threading.Lock()
        self._load_error: str | None = None
        self._loaded_at: float | None = None
        self._num_labels: int | None = None

    @property
    def ready(self) -> bool:
        return self._pipe is not None

    @property
    def status(self) -> dict[str, Any]:
        return {
            "ready": self.ready,
            "device": self._device if self.ready else None,
            "model_id": settings.sentiment_model_id,
            "classes": ["positive", "neutral", "negative"],
            "neutral_threshold": settings.sentiment_neutral_threshold,
            "neutral_margin": settings.sentiment_neutral_margin,
            "model_num_labels": self._num_labels,
            "load_error": self._load_error,
            "loaded_at": self._loaded_at,
        }

    def ensure_loaded(self) -> None:
        if self._pipe is not None:
            return
        with self._lock:
            if self._pipe is not None:
                return
            if settings.hf_endpoint:
                os.environ.setdefault("HF_ENDPOINT", settings.hf_endpoint)
            device = resolve_device(settings.device_preference)
            self._device = device
            device_arg: int | str = 0 if device == "cuda" else -1
            logger.info(
                "Loading sentiment model %s on %s",
                settings.sentiment_model_id,
                device,
            )
            try:
                from transformers import AutoConfig, pipeline

                config = AutoConfig.from_pretrained(settings.sentiment_model_id)
                self._num_labels = int(getattr(config, "num_labels", 0) or 0)
                self._pipe = pipeline(
                    "sentiment-analysis",
                    model=settings.sentiment_model_id,
                    tokenizer=settings.sentiment_model_id,
                    device=device_arg,
                    truncation=True,
                    max_length=256,
                    top_k=None,  # 返回全部标签分数，便于推断中性
                )
                self._load_error = None
                self._loaded_at = time.time()
            except Exception as exc:
                self._load_error = str(exc)
                self._pipe = None
                logger.exception("Failed to load sentiment model")
                raise

    def predict_one(self, text: str) -> dict[str, Any]:
        return self.predict_batch([text])[0]

    def predict_batch(self, texts: list[str]) -> list[dict[str, Any]]:
        self.ensure_loaded()
        assert self._pipe is not None
        cleaned = [t.strip() or "。" for t in texts]
        raw = self._pipe(
            cleaned,
            batch_size=settings.sentiment_batch_size,
            truncation=True,
            max_length=256,
            top_k=None,
        )
        # 单条时可能直接是 list[dict]（各标签分数）
        if cleaned and isinstance(raw, list) and raw and isinstance(raw[0], dict):
            raw = [raw]
        out: list[dict[str, Any]] = []
        for item in raw:
            out.append(self._decide(item))
        return out

    def _decide(self, item: Any) -> dict[str, Any]:
        scores = self._to_score_map(item)
        pos = scores.get("positive", 0.0)
        neg = scores.get("negative", 0.0)
        neu = scores.get("neutral")

        # 真·三分类模型：直接取最高
        if neu is not None and len(scores) >= 3:
            label = max(scores, key=scores.get)
            confidence = float(scores[label])
        else:
            # 二分类（如点评 RoBERTa）→ 用阈值/间隔得到中性
            top = max(pos, neg)
            gap = abs(pos - neg)
            if (
                top < settings.sentiment_neutral_threshold
                or gap < settings.sentiment_neutral_margin
            ):
                label = "neutral"
                # 中性置信度：两边越接近、峰值越低 → 越高
                confidence = round(1.0 - gap, 4)
                confidence = min(max(confidence, 0.0), 1.0)
            else:
                label = "positive" if pos >= neg else "negative"
                confidence = top

        sentiment = {"positive": 1, "neutral": 0, "negative": -1}[label]
        return {
            "sentiment": sentiment,
            "sentiment_label": label,
            "sentiment_method": "bert",
            "confidence": round(float(confidence), 4),
            "scores": {
                "positive": round(pos, 4),
                "neutral": round(
                    float(neu)
                    if neu is not None
                    else (1.0 - abs(pos - neg) if label == "neutral" else 0.0),
                    4,
                ),
                "negative": round(neg, 4),
            },
        }

    def _to_score_map(self, item: Any) -> dict[str, float]:
        scores: dict[str, float] = {}
        if isinstance(item, dict) and "label" in item:
            label = self._normalize_label(str(item.get("label", "")))
            scores[label] = float(item.get("score", 0.0))
            return scores
        if isinstance(item, list):
            for row in item:
                if not isinstance(row, dict):
                    continue
                label = self._normalize_label(str(row.get("label", "")))
                scores[label] = float(row.get("score", 0.0))
        return scores

    @staticmethod
    def _normalize_label(label: str) -> str:
        key = label.strip().lower()
        if key in _LABEL_MAP:
            return _LABEL_MAP[key]
        if "neu" in key or "中性" in label:
            return "neutral"
        if "pos" in key or "positive" in key or "正面" in label:
            return "positive"
        if "neg" in key or "negative" in key or "负面" in label:
            return "negative"
        return "neutral"


_analyzer: SentimentAnalyzer | None = None


def get_sentiment_analyzer() -> SentimentAnalyzer:
    global _analyzer
    if _analyzer is None:
        _analyzer = SentimentAnalyzer()
    return _analyzer
