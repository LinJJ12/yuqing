# `backend/src/services/` — 单步业务能力

上级规范：[../README.md](../README.md)

## 职责

- 实现可复用的**单步**能力：规范化、导入、情感、主题、预警趋势、Ollama 嵌入。
- 可被 `api/` 直接调用；不感知 FastAPI `Request`。

## 模块

| 模块 | 说明 |
|------|------|
| `normalize.py` | 原始记录 → 统一帖子字段；词典情感占位 |
| `ingest.py` | JSON/JSONL/CSV 解析并入库 |
| `sentiment.py` | 中文 RoBERTa；正/中/负（含阈值推断中性） |
| `topics.py` | 词云 / TF-IDF / BERTopic |
| `ollama_embed.py` | 本地 Ollama 向量（供 BERTopic） |
| `forecast.py` | 日聚合滑动平均、Prophet、预警规则、报告摘要 |
| `report.py` | PDF / CSV 导出；可选 OpenAI 兼容摘要 |
| `jobs.py` | 异步分析任务（进程内线程池） |
| `readiness.py` | 情感缓存 / Ollama / 云端 LLM / Agent 就绪探测 |
| `agent.py` | 轻量舆情问答与简报（OpenAI 兼容 / Ollama Chat） |

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
