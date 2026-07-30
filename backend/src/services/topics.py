"""主题：jieba 词频 + BERTopic（默认本地 Ollama 向量）。"""

from __future__ import annotations

import logging
import os
import re
import threading
from collections import Counter
from typing import Any

import jieba
import jieba.analyse

from src.config.settings import settings
from src.config.device import resolve_device
from src.services.ollama_embed import OllamaEmbedder

logger = logging.getLogger(__name__)

_STOPWORDS = {
    "的", "了", "是", "在", "我", "有", "和", "就", "不", "人", "都", "一",
    "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着", "没有",
    "看", "好", "自己", "这", "他", "她", "吗", "吧", "啊", "呢", "把", "被",
    "让", "与", "及", "等", "或", "并", "而", "之", "为", "对", "从", "以",
    "可以", "还是", "什么", "怎么", "这个", "那个", "我们", "你们", "他们",
    "学校", "同学", "今天", "已经", "比较", "感觉", "真的", "一下",
}


class TopicAnalyzer:
    def __init__(self) -> None:
        self._bertopic = None
        self._embedder = None
        self._lock = threading.Lock()
        self._load_error: str | None = None

    @property
    def status(self) -> dict[str, Any]:
        embed_info: dict[str, Any] = {
            "backend": settings.embedding_backend,
        }
        if settings.embedding_backend == "ollama":
            embed_info.update(
                {
                    "model": settings.ollama_embed_model,
                    "base_url": settings.ollama_base_url,
                    "local": True,
                }
            )
        else:
            embed_info.update(
                {
                    "model": settings.embedding_model_id,
                    "local": False,
                    "note": "HuggingFace 模型，首次需下载",
                }
            )
        return {
            "bertopic_ready": self._bertopic is not None,
            "embedding": embed_info,
            "load_error": self._load_error,
        }

    def word_cloud(self, texts: list[str], top_k: int = 40) -> list[dict[str, Any]]:
        counter: Counter[str] = Counter()
        for text in texts:
            for word in jieba.cut(text or ""):
                w = word.strip()
                if len(w) < 2 or w in _STOPWORDS:
                    continue
                if re.fullmatch(r"[\W\d_]+", w):
                    continue
                counter[w] += 1
        return [
            {"name": name, "value": int(value)}
            for name, value in counter.most_common(top_k)
        ]

    def keyword_topics(self, texts: list[str], top_k: int = 8) -> list[dict[str, Any]]:
        joined = "\n".join(t for t in texts if t)
        if not joined.strip():
            return []
        tags = jieba.analyse.extract_tags(joined, topK=top_k, withWeight=True)
        return [
            {"topic": str(tag), "weight": round(float(weight), 4), "method": "tfidf"}
            for tag, weight in tags
        ]

    def ensure_bertopic(self) -> None:
        if self._bertopic is not None:
            return
        with self._lock:
            if self._bertopic is not None:
                return
            try:
                from bertopic import BERTopic

                if settings.embedding_backend == "ollama":
                    logger.info(
                        "Using local Ollama embedder: %s",
                        settings.ollama_embed_model,
                    )
                    self._embedder = OllamaEmbedder()
                    # 冒烟：确认 Ollama 可连
                    self._embedder.encode(["连通性测试"])
                else:
                    if settings.hf_endpoint:
                        os.environ.setdefault("HF_ENDPOINT", settings.hf_endpoint)
                    from sentence_transformers import SentenceTransformer

                    device = resolve_device(settings.device_preference)
                    logger.info(
                        "Loading HF embedding %s on %s",
                        settings.embedding_model_id,
                        device,
                    )
                    self._embedder = SentenceTransformer(
                        settings.embedding_model_id, device=device
                    )

                self._bertopic = BERTopic(
                    embedding_model=self._embedder,
                    language="chinese (simplified)",
                    verbose=False,
                    min_topic_size=5,
                    calculate_probabilities=False,
                )
                self._load_error = None
            except Exception as exc:
                self._load_error = str(exc)
                self._bertopic = None
                self._embedder = None
                logger.exception("Failed to load BERTopic")
                raise

    def bertopic_fit(self, texts: list[str], top_n: int = 8) -> list[dict[str, Any]]:
        cleaned = [t.strip() for t in texts if t and t.strip()]
        if len(cleaned) < 10:
            return []
        self.ensure_bertopic()
        assert self._bertopic is not None
        topics, _ = self._bertopic.fit_transform(cleaned)
        info = self._bertopic.get_topic_info()
        result: list[dict[str, Any]] = []
        for _, row in info.iterrows():
            topic_id = int(row["Topic"])
            if topic_id < 0:
                continue
            words = self._bertopic.get_topic(topic_id) or []
            keywords = [w for w, _ in words[:6]]
            result.append(
                {
                    "topic_id": topic_id,
                    "label": " / ".join(keywords[:3]) if keywords else f"主题{topic_id}",
                    "keywords": keywords,
                    "count": int(row["Count"]),
                    "method": "bertopic",
                }
            )
            if len(result) >= top_n:
                break
        assigned = sum(1 for t in topics if t != -1)
        for item in result:
            item["coverage"] = round(assigned / max(len(cleaned), 1), 4)
        return result

    def analyze(self, texts: list[str], use_bertopic: bool = True) -> dict[str, Any]:
        words = self.word_cloud(texts)
        keywords = self.keyword_topics(texts)
        clusters: list[dict[str, Any]] = []
        bertopic_error = None
        if use_bertopic and len(texts) >= 10:
            try:
                clusters = self.bertopic_fit(texts)
            except Exception as exc:
                bertopic_error = str(exc)
                logger.warning("BERTopic failed, fallback to keywords: %s", exc)
        return {
            "word_cloud": words,
            "keywords": keywords,
            "bertopic": clusters,
            "bertopic_error": bertopic_error,
            "document_count": len(texts),
            "embedding": (
                self._embedder.status
                if isinstance(self._embedder, OllamaEmbedder)
                else {
                    "backend": settings.embedding_backend,
                    "model": settings.embedding_model_id,
                }
            ),
        }


_topic_analyzer: TopicAnalyzer | None = None


def get_topic_analyzer() -> TopicAnalyzer:
    global _topic_analyzer
    if _topic_analyzer is None:
        _topic_analyzer = TopicAnalyzer()
    return _topic_analyzer
