"""应用配置。"""

from __future__ import annotations

import os
from pathlib import Path

from pydantic import AliasChoices, Field
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

    app_name: str = "Yuqing"
    app_version: str = "0.1.0"
    host: str = "127.0.0.1"
    port: int = 8001
    cors_origins: list[str] = [
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ]

    # 情感：默认真三分类中文 BERT（微博域，更贴近短评/弹幕）
    # 若换回二分类（如 uer/roberta-base-finetuned-dianping-chinese），
    # 仍可用下方阈值/间隔推断中性。
    sentiment_model_id: str = "senlou/weibo-sentiment-chinese-bert"
    device_preference: str = "cuda"
    sentiment_batch_size: int = 32
    sentiment_neutral_threshold: float = 0.62
    sentiment_neutral_margin: float = 0.12
    # 最高类概率低于此值 → uncertain（仍 method=bert）
    sentiment_uncertain_threshold: float = 0.55

    # 向量：默认本机 Ollama
    embedding_backend: str = "ollama"  # ollama | huggingface
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_embed_model: str = "quentinz/bge-large-zh-v1.5"
    embedding_model_id: str = "BAAI/bge-small-zh-v1.5"
    hf_endpoint: str = "https://hf-mirror.com"

    db_path: str = str(DATA_DIR / "yuqing.db")
    import_dir: str = str(DATA_DIR / "imports")
    max_upload_bytes: int = 10 * 1024 * 1024
    default_platform: str = "campus"  # 文件导入默认平台码（历史兼容，非产品定位）
    # 可选主题词典（样例/无显式 topic 时用）；校园场景仍可用，不限制采集范围
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
    # 默认预警词：偏 B 站口碑 / 内容槽点（设置页可覆盖）
    default_alert_keywords: list[str] = [
        "劝退",
        "差评",
        "翻车",
        "塌房",
        "抄袭",
        "注水",
        "水文",
        "浪费时间",
        "看不下去",
        "尴尬",
        "离谱",
        "失望",
        "恶心",
        "投诉",
        "骗人",
        "虚假",
        "引战",
        "崩坏",
        "太烂",
        "烂尾",
    ]

    # 云端 LLM：OpenAI 兼容（火山 / 百炼 / DeepSeek / 官方等）
    # 亦兼容旧环境变量 DEEPSEEK_*（见 AliasChoices）
    openai_api_key: str = Field(
        default="",
        validation_alias=AliasChoices(
            "openai_api_key",
            "OPENAI_API_KEY",
            "DEEPSEEK_API_KEY",
        ),
    )
    openai_base_url: str = Field(
        default="",
        validation_alias=AliasChoices(
            "openai_base_url",
            "OPENAI_BASE_URL",
            "DEEPSEEK_BASE_URL",
        ),
    )
    openai_model: str = Field(
        default="",
        validation_alias=AliasChoices(
            "openai_model",
            "OPENAI_MODEL",
            "DEEPSEEK_MODEL",
        ),
    )

    # Agent：无云端 Key 时回退 Ollama Chat
    ollama_chat_model: str = "qwen2.5"

    # B 站内嵌采集（可选 Cookie，提高搜索/评论成功率）
    bilibili_sessdata: str = ""

    @property
    def llm_api_key(self) -> str:
        return (self.openai_api_key or "").strip()

    @property
    def llm_base_url(self) -> str | None:
        url = (self.openai_base_url or "").strip().rstrip("/")
        return url or None

    @property
    def llm_model(self) -> str:
        return (self.openai_model or "").strip() or "gpt-4o-mini"

    @property
    def has_cloud_llm(self) -> bool:
        return bool(self.llm_api_key)


settings = Settings()

# huggingface_hub 在 import 时读取 HF_ENDPOINT 并缓存；必须在首次 import transformers 之前写入。
# settings.hf_endpoint 已合并 .env，此处强制同步到进程环境。
if settings.hf_endpoint:
    os.environ["HF_ENDPOINT"] = settings.hf_endpoint.rstrip("/")
