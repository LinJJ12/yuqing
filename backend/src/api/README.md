# `backend/src/api/` — HTTP 接口层

上级规范：[../README.md](../README.md) · [../../../docs/directory-structure.md](../../../docs/directory-structure.md)

## 职责

- 对接前端的 FastAPI 路由：参数校验、状态码、统一 `{ok,data|error}` 包络。
- 只调用下一层入口（`services/` / `storage/` / `config/`），把结果转成 DTO。
- 应用组装在 `app.py`（CORS、生命周期、全局异常）。

## 文件

| 文件 | 路由域 |
|------|--------|
| `app.py` | 创建 `FastAPI` 应用 |
| `health.py` | `/api/v1/health/*` |
| `data.py` | `/imports` `/posts` `/dashboard/overview` |
| `alerts.py` | `/alerts` `/trends` `/reports/*` `/settings/alert-keywords` |
| `analysis.py` | `/analysis/*` `/analysis-jobs` |
| `agent.py` | `/agent/status` `/agent/chat` `/agent/brief` |

## 下一层怎么选

| 请求类型 | 下一层 |
|----------|--------|
| 导入 / 列表 / 总览读写 | `storage/`（经 `services/ingest` 做规范化） |
| 情感 / 主题推理 | `services/sentiment` · `services/topics` |
| 预警 / 趋势 / 报告汇总 | `services/forecast` |
| CUDA / 模型名 / 端口 | `config/` |

## 禁止

- 在路由函数里直接 `pipeline(...)` / `SentenceTransformer(...)` / 调 Ollama
- 手写 SQL（必须经 `storage/`）
- 返回与 `{ok,data|error}` 不一致的随意 JSON（用 `src.lib.http.ok/err`）
- 依赖 `frontend/` 或 `vendor/`
