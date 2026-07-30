"""中文 BERT 情感分析：正 / 中 / 负（GPU 优先）。

默认走真三分类模型；若加载的是二分类头，则用阈值/间隔推断中性。
低置信度标为 uncertain（仍写入 method=bert 与 confidence）。
"""

from __future__ import annotations

import logging
import os
import threading
import time
from typing import Any

from src.config.settings import settings
from src.config.device import resolve_device

logger = logging.getLogger(__name__)

_FALLBACK_LABEL_MAP = {
    "positive": "positive",
    "negative": "negative",
    "neutral": "neutral",
    "pos": "positive",
    "neg": "negative",
    "正面": "positive",
    "负面": "negative",
    "中性": "neutral",
}


class SentimentAnalyzer:
    def __init__(self) -> None:
        self._pipe = None
        self._device = "cpu"
        self._lock = threading.Lock()
        self._load_error: str | None = None
        self._loaded_at: float | None = None
        self._num_labels: int | None = None
        self._id2label: dict[str, str] = {}
        self._loaded_model_id: str | None = None

    @property
    def ready(self) -> bool:
        return self._pipe is not None

    @property
    def status(self) -> dict[str, Any]:
        return {
            "ready": self.ready,
            "device": self._device if self.ready else None,
            "model_id": settings.sentiment_model_id,
            "loaded_model_id": self._loaded_model_id,
            "classes": ["positive", "neutral", "negative", "uncertain"],
            "ternary_head": bool(self._num_labels and self._num_labels >= 3),
            "neutral_threshold": settings.sentiment_neutral_threshold,
            "neutral_margin": settings.sentiment_neutral_margin,
            "uncertain_threshold": settings.sentiment_uncertain_threshold,
            "model_num_labels": self._num_labels,
            "load_error": self._load_error,
            "loaded_at": self._loaded_at,
        }

    def ensure_loaded(self) -> None:
        want = settings.sentiment_model_id
        if self._pipe is not None and self._loaded_model_id == want:
            return
        with self._lock:
            if self._pipe is not None and self._loaded_model_id == want:
                return
            if settings.hf_endpoint:
                os.environ["HF_ENDPOINT"] = settings.hf_endpoint.rstrip("/")
            device = resolve_device(settings.device_preference)
            self._device = device
            device_arg: int | str = 0 if device == "cuda" else -1
            logger.info("Loading sentiment model %s on %s", want, device)
            try:
                from transformers import pipeline

                # 换模型时释放旧 pipeline，避免占显存
                self._pipe = None
                config = self._load_config(want)
                self._num_labels = int(getattr(config, "num_labels", 0) or 0)
                raw_id2label = getattr(config, "id2label", None) or {}
                self._id2label = {
                    str(k): self._normalize_label(str(v))
                    for k, v in dict(raw_id2label).items()
                }
                if not self._num_labels and self._id2label:
                    self._num_labels = len(self._id2label)
                tokenizer, model = self._load_model_and_tokenizer(want)
                self._pipe = pipeline(
                    "sentiment-analysis",
                    model=model,
                    tokenizer=tokenizer,
                    device=device_arg,
                    truncation=True,
                    max_length=256,
                    top_k=None,
                )
                self._loaded_model_id = want
                self._load_error = None
                self._loaded_at = time.time()
            except Exception as exc:
                self._load_error = str(exc)
                self._pipe = None
                self._loaded_model_id = None
                logger.exception("Failed to load sentiment model")
                raise

    @staticmethod
    def _load_config(model_id: str):
        from transformers import AutoConfig

        try:
            return AutoConfig.from_pretrained(model_id, local_files_only=True)
        except Exception:
            return AutoConfig.from_pretrained(model_id)

    @staticmethod
    def _load_model_and_tokenizer(model_id: str):
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        try:
            tokenizer = AutoTokenizer.from_pretrained(model_id, local_files_only=True)
            model = AutoModelForSequenceClassification.from_pretrained(
                model_id, local_files_only=True
            )
            return tokenizer, model
        except Exception:
            tokenizer = AutoTokenizer.from_pretrained(model_id)
            model = AutoModelForSequenceClassification.from_pretrained(model_id)
            return tokenizer, model

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
        items = self._normalize_pipeline_batch(raw, len(cleaned))
        if len(items) != len(cleaned):
            raise RuntimeError(
                f"情感批次结果数量不匹配: got {len(items)}, expected {len(cleaned)}"
            )
        return [self._decide(item) for item in items]

    @staticmethod
    def _normalize_pipeline_batch(raw: Any, n: int) -> list[Any]:
        """统一 pipeline 输出为「每条文本一个 item」。

        - 单条 + top_k=None → list[dict]（各标签分数），需包成 [list]
        - 多条 + top_k=None → list[list[dict]]
        - 多条 + top-1 → list[dict]（每条一个 dict），不可再包一层
        """
        if n <= 0:
            return []
        if not isinstance(raw, list):
            return [raw]
        if not raw:
            return []
        if isinstance(raw[0], list):
            return raw
        if isinstance(raw[0], dict):
            # 仅当「一条文本、返回全部分数」时才包一层
            if n == 1:
                return [raw]
            return raw
        return raw

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

        if (
            label in {"positive", "negative", "neutral"}
            and float(confidence) < settings.sentiment_uncertain_threshold
        ):
            label = "uncertain"

        sentiment = {
            "positive": 1,
            "neutral": 0,
            "negative": -1,
            "uncertain": 0,
        }[label]
        return {
            "sentiment": sentiment,
            "sentiment_label": label,
            "sentiment_method": "bert",
            "sentiment_confidence": round(float(confidence), 4),
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
            label = self._resolve_pipeline_label(str(item.get("label", "")))
            scores[label] = float(item.get("score", 0.0))
            return scores
        if isinstance(item, list):
            for row in item:
                if not isinstance(row, dict):
                    continue
                label = self._resolve_pipeline_label(str(row.get("label", "")))
                scores[label] = float(row.get("score", 0.0))
        return scores

    def _resolve_pipeline_label(self, label: str) -> str:
        key = label.strip()
        lower = key.lower()
        # LABEL_N → 优先用模型 id2label，避免写死顺序
        if lower.startswith("label_"):
            idx = lower.split("_", 1)[-1]
            if idx in self._id2label:
                return self._id2label[idx]
            if idx.isdigit() and idx in self._id2label:
                return self._id2label[idx]
        return self._normalize_label(key)

    @staticmethod
    def _normalize_label(label: str) -> str:
        key = label.strip().lower()
        if key in _FALLBACK_LABEL_MAP:
            return _FALLBACK_LABEL_MAP[key]
        if "neu" in key or "中性" in label:
            return "neutral"
        if "pos" in key or "positive" in key or "正面" in label:
            return "positive"
        if "neg" in key or "negative" in key or "负面" in label:
            return "negative"
        return "neutral"


_analyzer: SentimentAnalyzer | None = None
_APPLIED_MODEL_KEY = "sentiment_model_id"


def get_sentiment_analyzer() -> SentimentAnalyzer:
    global _analyzer
    if _analyzer is None:
        _analyzer = SentimentAnalyzer()
    return _analyzer


def sentiment_model_status(store: Any | None = None) -> dict[str, Any]:
    """库内标注是否与当前 SENTIMENT_MODEL_ID 一致。"""
    from src.storage.db import get_store

    store = store or get_store()
    current = settings.sentiment_model_id
    applied = store.get_setting(_APPLIED_MODEL_KEY)
    with store.connect() as conn:
        bert_done = conn.execute(
            "SELECT COUNT(*) AS c FROM posts WHERE sentiment_method = 'bert'"
        ).fetchone()["c"]
    if applied is None:
        # 有 BERT 标签但未记录模型 → 视为过期（换模升级场景）
        stale = int(bert_done) > 0
    else:
        stale = str(applied) != current
    return {
        "model_id": current,
        "model_id_applied": applied,
        "model_stale": stale,
    }


def mark_sentiment_model_applied(store: Any | None = None) -> str:
    from src.storage.db import get_store

    store = store or get_store()
    mid = settings.sentiment_model_id
    store.set_setting(_APPLIED_MODEL_KEY, mid)
    return mid


def should_rerun_all_sentiment(only_pending: bool, store: Any | None = None) -> bool:
    """换模型后即使 only_pending=True 也要全量覆盖。"""
    if not only_pending:
        return True
    return bool(sentiment_model_status(store)["model_stale"])
