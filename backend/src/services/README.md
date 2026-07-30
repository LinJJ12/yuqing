# `backend/src/services/` — 单步业务能力

上级规范：[../README.md](../README.md)

## 职责

- 实现可复用的**单步**能力：规范化、导入、情感、主题、预警趋势、Ollama 嵌入。
- 可被 `api/` 直接调用；不感知 FastAPI `Request`。

## 模块

| 模块 | 说明 |
|------|------|
| `normalize.py` | 原始记录 → 统一帖子字段；**不写**词典情感（仅 `provided`） |
| `ingest.py` | JSON/JSONL/CSV 解析并入库 |
| `sentiment.py` | 中文 BERT 情感；真三分类 + 低置信 uncertain；二分类时阈值推断中性 |
| `sentiment_review.py` | 人工 / LLM 难例改判（method=manual|llm，BERT 不覆盖） |
| `topics.py` | 词云 / TF-IDF / BERTopic |
| `ollama_embed.py` | 本地 Ollama 向量（供 BERTopic） |
| `forecast.py` | 日聚合滑动平均、Prophet、预警规则、报告摘要 |
| `report.py` | PDF / CSV 导出；可选 OpenAI 兼容摘要 |
| `jobs.py` | 异步情感/主题；采集/导入后可 `enqueue_pending_sentiment` |
| `readiness.py` | 情感缓存 / Ollama / 云端 LLM / Agent 就绪探测 |
| `agent.py` | 轻量舆情问答与简报（OpenAI 兼容 / Ollama Chat） |
| `bilibili_collect.py` | B 站关键词/BV 评论采集并入库；话题：显式 > 关键词 > 视频标题 |
| `bilibili_quality.py` | 标题黑名单/须命中搜索词；评论去噪（空评/表情/刷评） |
| `video_report.py` | 按 bvid 聚合单视频口碑（情感 / 词云 / 规则结论；可选 LLM 观众反馈） |

## 调用

```text
api/ ──► services/* ──► storage/
              │
              └─ config/（设备、模型、阈值）
```

## 禁止

- `from fastapi import Request` 或返回 `JSONResponse`（那是 `api/` / `lib.http` 的事）
- 绕过 `storage/` 自己 `sqlite3.connect` 业务库
- 引入 `vendor/` 代码作运行时依赖
- 在本层做多 Agent 编排（若二期需要，另开 `pipeline/` 或 `agent/`，先改 README）
