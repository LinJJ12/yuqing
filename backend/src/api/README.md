# `backend/src/api/` — HTTP 接口层

上级规范：[../README.md](../README.md) · [../../../docs/directory-structure.md](../../../docs/directory-structure.md)

## 职责

- 对接前端的 FastAPI 路由：参数校验、状态码、统一 `{ok,data|error}` 包络。
- 只调用下一层入口（`services/` / `storage/` / `config/`），把结果转成 DTO。
- 应用组装在 `app.py`（CORS、生命周期、全局异常）。

## 文件

| 文件 | 路由域 |
|------|--------|
| `app.py` | 创建 `FastAPI` 应用、挂载各 router |
| `health.py` | `/health/*` |
| `data.py` | `/imports` `/posts` `/posts/review` `/posts/{id}/sentiment` `/posts/delete` `/dashboard/overview` |
| `collect.py` | `/collect/bilibili`（含标题门禁 / 评论去噪参数） |
| `analysis.py` | `/analysis/*` `/analysis-jobs` |
| `alerts.py` | `/alerts` `/trends` `/settings/alert-keywords` |
| `reports.py` | `/reports/summary` `/reports/videos` `/reports/video`（GET/POST，`with_ai`） `/reports/export.*` |
| `agent.py` | `/agent/status` `/agent/chat` `/agent/brief`（可选 `bvid`） |

## 下一层怎么选

| 请求类型 | 下一层 |
|----------|--------|
| 导入 / 列表 / 删除 / 总览 | `storage/`（导入经 `services/ingest`） |
| B 站评论采集 | `services/bilibili_collect` + `bilibili_quality` |
| 情感 / 主题推理 | `services/sentiment` · `sentiment_review` · `services/topics` |
| 预警 / 趋势 / 全局报告摘要 | `services/forecast` |
| 单视频口碑 | `services/video_report` |
| 报告导出 / AI 摘要 | `services/report` |
| Agent 问答 / 简报 | `services/agent` |
| CUDA / 模型名 / Cookie | `config/` |

## 禁止

- 在路由函数里直接 `pipeline(...)` / `SentenceTransformer(...)` / 调 Ollama
- 手写 SQL（必须经 `storage/`）
- 返回与 `{ok,data|error}` 不一致的随意 JSON（用 `src.lib.http.ok/err`）
- 依赖 `frontend/` 或 `vendor/`
- 把报告路由再塞回 `alerts.py`（报告域用 `reports.py`）
