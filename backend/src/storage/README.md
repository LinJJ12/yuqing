# `backend/src/storage/` — 持久化

上级规范：[../README.md](../README.md)

## 职责

- **唯一**业务 I/O：SQLite 帖子、导入/分析任务、设置键值、统计。
- 表结构初始化、WAL、去重插入、情感字段更新、总览聚合。

## 文件

| 文件 | 说明 |
|------|------|
| `db.py` | `Store` / `get_store` / `utc_now` |

## 约定

- DB 路径默认 `backend/data/yuqing.db`（见 `config.settings`）。
- 表：`posts`、`import_jobs`、`analysis_jobs`、`app_settings`。
- `__init__.py` 仅作包标记，不堆再导出。

## 禁止

- 调用 HuggingFace、Ollama、BERT、BERTopic
- 依赖 `api/` 或解析 HTTP 表单
- 在本层拼「预警文案 / 报告段落」（属 `services/forecast`）
