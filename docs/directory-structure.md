# 仓库目录与文件约定

> **产品名**：**知微**（仓库文件夹可能仍为 `yuqing`，仅路径名，不代表产品品牌）。  
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
├── .trellis/              # Trellis 工作流 + 合并历史（MERGE_PLAN / GATE）
├── .cursor/               # Trellis 生成的 Cursor 命令 / Agent / hooks
├── frontend/              # Vue 3 工作台
├── backend/               # FastAPI BFF
├── vendor/                # 参考仓（gitignore，只留 README）
├── pyproject.toml         # uv 依赖（根 .venv）
└── .gitignore
```

| 路径 | 一句话职责 | 禁止 |
|------|------------|------|
| `docs/` | 产品说明与跨端约定（PRD / 定位 / 目录 / 架构） | 运行时代码、密钥 |
| `.trellis/` | Trellis 工作流（tasks/spec/workflow）+ 合并历史 Gate | 产品运行时资源、业务算法 |
| `.cursor/` | Trellis 为 Cursor 生成的命令 / skills / agents | 业务源码、密钥 |
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
                                      ├─ services/   # 导入 / B站采集与质量门禁 / 情感 / 主题 / 预警 / 视频口碑 / Agent
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
| `backend/data/` | 运行时 DB/导入/样例 | 提交进 Git（除说明与 samples） |

细则：[`backend/src/README.md`](../backend/src/README.md) 及各子目录 README。

---

## 3. 前端分层（摘要）

| 目录 | 职责 | 禁止 |
|------|------|------|
| `frontend/src/api/` | **唯一** HTTP 出口 | 在 pages 里裸 `axios`/`fetch` |
| `frontend/src/pages/` | 路由级页面 | 直接拼后端 URL、持有密钥 |
| `frontend/src/router/` | 路由表 | 业务请求 |
| `frontend/src/lib/` | 非 UI 助手（鉴权会话、agentSession、时间格式） | 页面组件、裸调后端 URL |
| `frontend/src/components/` | 可复用 UI 块（含 `layout/`） | 绕过 api 层发请求 |
| `frontend/src/assets/` | 静态资源（含品牌 `logo.png`，侧栏 import） | 业务逻辑 |
| `frontend/public/` | 公开静态（`logo.png` 作 favicon / 直链） | 业务逻辑 |
| `frontend/src/style.css` | 全局样式（Vite 惯例，由 `main.js` 引入） | — |

细则：[`frontend/src/README.md`](../frontend/src/README.md)。

---

## 4. 前后端 API 垂直表（改接口必同步）

| 前端 `src/api/client.js` | 后端路由前缀 | 后端文件 |
|--------------------------|--------------|----------|
| login / fetchAuthMe / logoutApi | `/auth/login` `/auth/me` `/auth/logout` | `auth.py`（业务路由经 `deps.require_user`） |
| health / overview / posts / imports / deletePosts | `/health*` `/dashboard` `/posts` `/posts/delete` `/imports` | `health.py` `data.py` |
| collectBilibili | `/collect/bilibili` | `collect.py` |
| sentiment / topics / analysis-jobs | `/analysis/*` `/analysis-jobs` | `analysis.py` |
| alerts / trends / alert-keywords | `/alerts` `/trends` `/settings/alert-keywords` | `alerts.py` |
| report summary / videos / video / export | `/reports/*` | `reports.py` |
| agent status / chat / brief | `/agent/*` | `agent.py` |

统一响应：`{ "ok": true, "data": ... }` / `{ "ok": false, "error": { "code", "message" } }`。

---

## 5. 目录 README 清单

| README | 覆盖 |
|--------|------|
| [`docs/README.md`](./README.md) | 跨端文档索引 |
| [`prd.md`](./prd.md) | 产品需求：用户 · 功能 · 主路径 |
| [`positioning.md`](./positioning.md) | 定位与演进：是否舆情 · 路线图 |
| [`diagrams.md`](./diagrams.md) | 流程 · 思维导图 · 架构图 |
| [`model-cache.md`](./model-cache.md) | 演示就绪：模型预取 / Ollama |
| [`real-data-collection.md`](./real-data-collection.md) | 内嵌 B 站评论 + 质量门禁 + MediaCrawler |
| [`directory-structure.md`](./directory-structure.md) | 目录与 API 垂直表（本文） |
| [`../.trellis/README.md`](../.trellis/README.md) | Trellis 工作流 + 合并历史 |
| [`../vendor/README.md`](../vendor/README.md) | 参考仓 |
| [`../frontend/README.md`](../frontend/README.md) | 前端工程 |
| [`../frontend/src/README.md`](../frontend/src/README.md) | 前端源码 |
| [`../frontend/src/api/README.md`](../frontend/src/api/README.md) | HTTP 客户端 |
| [`../frontend/src/pages/README.md`](../frontend/src/pages/README.md) | 路由页面 |
| [`../frontend/src/router/README.md`](../frontend/src/router/README.md) | 路由表 |
| [`../frontend/src/components/README.md`](../frontend/src/components/README.md) | 共享组件 |
| [`../frontend/src/components/layout/README.md`](../frontend/src/components/layout/README.md) | 壳层布局（侧栏 / 顶栏） |
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

### 本地/忽略路径（勿当业务代码）

| 路径 | 说明 |
|------|------|
| `.tools/` | 本机工具（如 gh），已 gitignore |
| `.vscode/` | 编辑器配置，已 gitignore |
| `frontend/dist/` | 前端构建产物，已 gitignore |
| `backend/data/*` | 运行时库与导入（samples 可提交） |
| `vendor/*` | 参考仓克隆，仅提交 `vendor/README.md` |

新增功能时：**先改对应层 README 的职责/禁止，再写代码**。
