"""应用配置。"""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/src/config/settings.py → backend/
BACKEND_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_ROOT.parent
DATA_DIR = BACKEND_ROOT / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(
            str(BACKEND_ROOT / ".env"),
            str(REPO_ROOT / ".env"),
        ),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Yuqing Campus Opinion"
    app_version: str = "0.1.0"
    host: str = "127.0.0.1"
    port: int = 8001
    cors_origins: list[str] = [
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ]

    # 情感：二分类中文 RoBERTa + 置信度间隔 → 正/中/负
    sentiment_model_id: str = "uer/roberta-base-finetuned-dianping-chinese"
    device_preference: str = "cuda"
    sentiment_batch_size: int = 32
    sentiment_neutral_threshold: float = 0.62
    sentiment_neutral_margin: float = 0.12

    # 向量：默认本机 Ollama
    embedding_backend: str = "ollama"  # ollama | huggingface
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_embed_model: str = "quentinz/bge-large-zh-v1.5"
    embedding_model_id: str = "BAAI/bge-small-zh-v1.5"
    hf_endpoint: str = "https://hf-mirror.com"

    db_path: str = str(DATA_DIR / "yuqing.db")
    import_dir: str = str(DATA_DIR / "imports")
    max_upload_bytes: int = 10 * 1024 * 1024
    default_platform: str = "campus"
    default_school_keywords: list[str] = [
        "食堂",
        "宿舍",
        "图书馆",
        "教务",
        "就业",
        "奖学金",
        "校园网",
        "后勤",
    ]


settings = Settings()
