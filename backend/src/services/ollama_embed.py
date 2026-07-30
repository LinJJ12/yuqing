"""本地 Ollama 向量嵌入（bge-large-zh / bge-m3 等）。"""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx
import numpy as np

from src.config.settings import settings

logger = logging.getLogger(__name__)


class OllamaEmbedder:
    """兼容 BERTopic / sentence-transformers 风格的 embed 接口。"""

    def __init__(
        self,
        model: str | None = None,
        base_url: str | None = None,
        timeout: float = 120.0,
        retries: int = 3,
    ) -> None:
        self.model = model or settings.ollama_embed_model
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.timeout = timeout
        self.retries = retries
        self._dim: int | None = None

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed_one(text)

    def encode(
        self,
        sentences: list[str] | str,
        **_kwargs: Any,
    ) -> np.ndarray:
        if isinstance(sentences, str):
            sentences = [sentences]
        vectors = self.embed_documents(list(sentences))
        return np.asarray(vectors, dtype=np.float32)

    def _embed_one(self, text: str) -> list[float]:
        prompt = (text or "").strip() or "。"
        last_exc: Exception | None = None
        for attempt in range(1, self.retries + 1):
            try:
                return self._request_embedding(prompt)
            except Exception as exc:
                last_exc = exc
                logger.warning(
                    "Ollama embed attempt %s/%s failed: %s",
                    attempt,
                    self.retries,
                    exc,
                )
                # 503 常见于模型冷启动
                time.sleep(min(1.5 * attempt, 5))
        raise RuntimeError(f"Ollama 向量失败（已重试 {self.retries} 次）: {last_exc}")

    def _request_embedding(self, prompt: str) -> list[float]:
        # 优先新接口 /api/embed，失败再回退 /api/embeddings
        try:
            payload = self._post_json(
                "/api/embed",
                {"model": self.model, "input": prompt},
            )
            emb = payload.get("embeddings")
            if isinstance(emb, list) and emb:
                vec = emb[0]
            else:
                vec = payload.get("embedding")
        except Exception:
            payload = self._post_json(
                "/api/embeddings",
                {"model": self.model, "prompt": prompt},
            )
            vec = payload.get("embedding")

        if not isinstance(vec, list) or not vec:
            raise RuntimeError(f"Ollama 未返回向量: model={self.model}")
        self._dim = len(vec)
        return [float(x) for x in vec]

    def _post_json(self, path: str, body: dict) -> dict:
        url = f"{self.base_url}{path}"
        # trust_env=False：避免 Windows 系统代理劫持 127.0.0.1（常见 503）
        with httpx.Client(timeout=self.timeout, trust_env=False) as client:
            resp = client.post(url, json=body)
            resp.raise_for_status()
            return resp.json()

    @property
    def status(self) -> dict[str, Any]:
        return {
            "backend": "ollama",
            "model": self.model,
            "base_url": self.base_url,
            "dim": self._dim,
        }
