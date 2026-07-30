# 仓库目录与文件约定

> **目的**：每个文件夹用一句话说清「只负责什么、禁止什么」，方便后期加功能而不搅成泥球。  
> **结构借鉴**：桌面旁路仓 **chatbot**、**OmniStream**（前后端分离、`api` 垂直对齐、单能力 vs 编排分层、目录 README 所有权）。  
> **命名**：正式根目录为 `frontend/`、`backend/`（不用 `app/`、`web/`、`server/`）。

各层细则以**该目录 README**为准；若冲突，以更具体的子目录 README 为准，并应回改本文。

---

## 1. 顶层

```text
yuqing/
├── README.md              # 产品简介 + 如何启动
├── AGENTS.md              # AI/协作最短入口
├── docs/                  # 跨端约定（本文）
├── .trellis/              # 合并方案与阶段门禁
├── frontend/              # Vue 3 工作台
├── backend/               # FastAPI BFF
├── vendor/                # 参考仓（gitignore，只留 README）
├── pyproject.toml         # uv 依赖（根 .venv）
└── .gitignore
```

| 路径 | 一句话职责 | 禁止 |
|------|------------|------|
| `docs/` | 跨端目录/架构约定（给人看） | 运行时代码、密钥 |
| `.trellis/` | 合并计划、Gate、阶段验收 | 产品运行时资源、业务算法 |
| `frontend/` | 界面、本机状态、调 BFF | 持有模型 Key、SQLite、推理 |
| `backend/` | API、分析能力、持久化 | 页面组件、卡通/业务 CSS |
| `vendor/` | 第三方参考实现（只读） | `import` 进生产路径 |

### 1.1 环境变量

```text
backend/.env.example   # ✅ Git
backend/.env           # ❌ Git（Ollama 地址、HF 镜像、密钥等）
仓库根 .env            # ❌ 不推荐；优先 backend/.env
frontend/              # 一般不需要 Key；代理走 vite.config.js
```

### 1.2 调用总览

```text
浏览器
  └─ frontend/src/api/  ──HTTP──►  backend/src/api/
                                      ├─ services/   # 导入 / B站采集 / 情感 / 主题 / 预警 / Agent
                                      ├─ storage/    # SQLite
                                      └─ config/     # settings / CUDA / Ollama / Cookie
```

---

## 2. 后端分层（摘要）

| 目录 | 职责 | 禁止 |
|------|------|------|
| `backend/src/api/` | HTTP：校验、状态码、组响应 | 写模型推理细节 |
| `backend/src/services/` | 可复用单步能力 | 直接碰 Request/Response |
| `backend/src/storage/` | 唯一业务落盘 | 调 LLM / Ollama / HF |
| `backend/src/config/` | 配置与设备探测 | 业务规则、SQL |
| `backend/src/lib/` | 无业务词工具 | 堆业务代码 |
| `backend/scripts/` | 样例生成、冒烟脚本 | 被 api 运行时依赖 |
| `backend/data/` | 运行时 DB/导入/样例 | 提交进 Git（除说明文件） |

细则：[`backend/src/README.md`](../backend/src/README.md) 及各子目录 README。

---

## 3. 前端分层（摘要）

| 目录 | 职责 | 禁止 |
|------|------|------|
| `frontend/src/api/` | **唯一** HTTP 出口 | 在 pages 里裸 `axios`/`fetch` |
| `frontend/src/pages/` | 路由级页面 | 直接拼后端 URL、持有密钥 |
| `frontend/src/router/` | 路由表 | 业务请求 |
| `frontend/src/components/` | 可复用 UI 块 | 绕过 api 层发请求 |
| `frontend/src/assets/` | 静态资源 | 业务逻辑 |

细则：[`frontend/src/README.md`](../frontend/src/README.md)。

---

## 4. 前后端 API 垂直表（改接口必同步）

| 前端 `src/api` | 后端路由前缀 |
|----------------|--------------|
| `client.js` → health / overview / posts / imports | `/api/v1/health*` `/dashboard` `/posts` `/imports` |
| collect (B 站) | `/api/v1/collect/bilibili` |
| sentiment / topics / analysis-jobs | `/api/v1/analysis/*` `/analysis-jobs` |
| alerts / trends / reports / settings | `/api/v1/alerts` `/trends` `/reports/*` `/settings/*` |
| agent | `/api/v1/agent/*` |

统一响应：`{ "ok": true, "data": ... }` / `{ "ok": false, "error": { "code", "message" } }`。

---

## 5. 目录 README 清单

| README | 覆盖 |
|--------|------|
| [`docs/README.md`](./README.md) | 跨端文档 |
| [`diagrams.md`](./diagrams.md) | 流程 · 思维导图 · 架构图 |
| [`model-cache.md`](./model-cache.md) | 演示就绪：模型预取 / Ollama |
| [`real-data-collection.md`](./real-data-collection.md) | 内嵌 B 站评论 + 外挂 MediaCrawler |
| [`directory-structure.md`](./directory-structure.md) | 目录与 API 垂直表 |
| [`../.trellis/README.md`](../.trellis/README.md) | 方案与门禁 |
| [`../vendor/README.md`](../vendor/README.md) | 参考仓 |
| [`../frontend/README.md`](../frontend/README.md) | 前端工程 |
| [`../frontend/src/README.md`](../frontend/src/README.md) | 前端源码 |
| [`../frontend/src/api/README.md`](../frontend/src/api/README.md) | HTTP 客户端 |
| [`../frontend/src/pages/README.md`](../frontend/src/pages/README.md) | 路由页面 |
| [`../frontend/src/router/README.md`](../frontend/src/router/README.md) | 路由表 |
| [`../frontend/src/components/README.md`](../frontend/src/components/README.md) | 共享组件 |
| [`../frontend/src/assets/README.md`](../frontend/src/assets/README.md) | 静态资源 |
| [`../backend/README.md`](../backend/README.md) | 后端工程 |
| [`../backend/src/README.md`](../backend/src/README.md) | 后端源码 |
| [`../backend/src/api/README.md`](../backend/src/api/README.md) | HTTP 接口 |
| [`../backend/src/config/README.md`](../backend/src/config/README.md) | 配置与设备 |
| [`../backend/src/services/README.md`](../backend/src/services/README.md) | 业务能力 |
| [`../backend/src/storage/README.md`](../backend/src/storage/README.md) | 持久化 |
| [`../backend/src/lib/README.md`](../backend/src/lib/README.md) | 无业务工具 |
| [`../backend/scripts/README.md`](../backend/scripts/README.md) | 运维脚本 |
| [`../backend/data/README.md`](../backend/data/README.md) | 运行时数据 |
| [`../backend/docs/README.md`](../backend/docs/README.md) | 后端专用文档 |

新增功能时：**先改对应层 README 的职责/禁止，再写代码**。
