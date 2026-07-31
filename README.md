<p align="center">
  <img src="frontend/public/logo.png" alt="知微" width="128" />
</p>

<h1 align="center">知微</h1>

<p align="center"><b>见微知著 — 从评论细节见口碑走势</b></p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue" alt="Python 3.11+" />
  <img src="https://img.shields.io/badge/Vue-3.5+-brightgreen" alt="Vue 3.5+" />
  <img src="https://img.shields.io/badge/FastAPI-0.100+-red" alt="FastAPI" />
  <img src="https://img.shields.io/badge/uv-managed-informational" alt="uv" />
  <img src="https://img.shields.io/badge/GPU-optional-lightgrey" alt="GPU optional" />
</p>

<p align="center">
  本地可运行的社交媒体<strong>观众反馈 / 内容口碑</strong>分析工作台。<br />
  以 B 站评论为主：采集 → 情感 / 主题 / 趋势 → 预警与单视频口碑报告。<br />
  属舆情分析，主战场是内容口碑，而非全网危机监测；校园样例仅为可选演示数据。
</p>

---

## 做什么

```
设置检查就绪 → 监测贴 BV / 导入 → 情感跑批 → 主题 · 预警 · 趋势
                                              ↓
                         单视频口碑报告 / PDF·CSV / 智能助手简报
```

正式工程：`frontend/` + `backend/`。参考仓在 `vendor/`（只读，勿当运行时依赖）。

仓库文件夹可能仍为 `yuqing`，**产品品牌是知微**。

### 核心能力

| 能力 | 说明 |
|------|------|
| 舆情监测 | BV 评论采集（主）、关键词搜索（次）、JSON/CSV 导入、质量门禁与噪声清理 |
| 情感分析 | 中文 BERT 三分类（正/中/负 + uncertain，可 GPU）；难例人工 / LLM 改判 |
| 热点话题 | 词云 / TF-IDF + BERTopic（默认本机 Ollama 向量） |
| 预警 · 趋势 | 负面 / 可配置敏感词 + 热度突增；滑动平均 / Prophet |
| 分析报告 | 全局汇总 + **单视频口碑**；PDF / CSV；可选 OpenAI 兼容摘要 |
| 智能助手 | 基于库内数据的问答与简报（云端 LLM 或 Ollama Chat） |
| 系统设置 | 情感缓存 / B 站 Cookie / Ollama / LLM 就绪检查 |

---

## 系统架构

```
知微
├── frontend/          Vue 3 + Vite（总览 · 监测 · 入库 · 洞察 · 预警 · 报告 · 助手 · 设置）
├── backend/           FastAPI BFF
│   ├── api/           HTTP 边界（与 frontend/src/api 垂直对齐）
│   ├── services/      采集 · 情感 · 主题 · 预警 · 报告 · Agent · 就绪探测
│   ├── storage/       SQLite
│   └── config/        settings · CUDA · Ollama · Cookie（密钥只出自此处）
├── docs/              PRD · 定位 · 目录约定 · 架构图 · 采集 / 模型
├── .trellis/          Trellis 工作流 + 合并历史 Gate
├── .cursor/           Trellis → Cursor 命令 / Agent
└── vendor/            第三方参考（本地，勿 import 进生产路径）
```

Key 只放 `backend/.env`，前端不持模型密钥。目录细则见 [`docs/directory-structure.md`](docs/directory-structure.md)。

---

## 快速开始

**环境**：Python **3.11–3.12**（根目录 `uv` + `.venv`）+ Node.js 18+。GPU（CUDA）可选，用于加速情感推理。

```powershell
# 依赖（仓库根）
cd C:\Users\Administrator\Desktop\yuqing
uv sync
# 开发依赖（含 pytest）：uv sync --extra dev

# 终端 1 — 后端
uv run python backend/main.py --reload --port 8001
# API 文档：http://127.0.0.1:8001/docs

# 终端 2 — 前端
cd frontend
npm install
npm run dev
```

打开：**http://127.0.0.1:5173**

| 地址 | 说明 |
|------|------|
| `/` | 总览（空库时为首跑三步引导） |
| `/monitor` | 舆情监测（贴 BV / 导入 / 清理） |
| `/inbox` | 入库浏览（搜索 · 增删改 · 改判） |
| `/insights` | 洞察（情感 · 词云话题；旧 `/sentiment` `/topics` 会重定向） |
| `/alerts` | 预警中心 |
| `/reports` | 分析报告（单视频口碑 · 全局导出） |
| `/agent` | 智能助手 |
| `/settings` | 系统设置（就绪检查 · 敏感词） |

### 演示前（防翻车）

```powershell
# 1) 复制环境变量模板并按需填写
copy backend\.env.example backend\.env
# 国内建议：HF_ENDPOINT=https://hf-mirror.com
# 真 BV 采集建议：BILIBILI_SESSDATA=...（填后重启后端）

# 2) 预取情感模型到本机缓存
uv run python backend/scripts/prefetch_models.py

# 3) 主题聚类（可选）：启动 Ollama 并拉取嵌入模型
# ollama pull quentinz/bge-large-zh-v1.5
```

设置页可一眼查看：情感缓存、B 站 Cookie、Ollama、云端 LLM / 助手是否就绪。详情见 [`docs/model-cache.md`](docs/model-cache.md)、[`docs/real-data-collection.md`](docs/real-data-collection.md)。

日常演示推荐：监测页贴 **BV** → 等情感 → 报告页看单视频口碑。校园样例仍可用（不代表产品限定校园）：

```powershell
uv run python backend/scripts/generate_sample_data.py
# 监测页上传 backend/data/samples/campus_sample.json
```

### 测试

```powershell
# 后端（需先 uv sync --extra dev；用例在 backend/tests，已忽略 vendor）
uv run pytest
# 更完整的手工冒烟（含导出 / Agent 等）
uv run python backend/scripts/smoke_test.py

# 前端
cd frontend
npm run build
node scripts/agent-session-check.mjs
```

---

## 目录

| 路径 | 内容 |
|------|------|
| `frontend/` | 正式 Web（Vue，品牌：知微） |
| `backend/` | 分析 BFF（FastAPI） |
| `backend/scripts/` | 样例生成、模型预取等 |
| `docs/` | PRD、定位、架构图、目录约定、采集 / 模型 |
| `.trellis/` | Trellis 工作流 + 合并历史 Gate |
| `.cursor/` | Trellis → Cursor 命令 / Agent |
| `vendor/` | 第三方参考（本地，勿当运行时） |

---

## 环境变量

写在 `backend/.env`（勿提交）。模板：`backend/.env.example`。

| 变量 | 用途 |
|------|------|
| `HF_ENDPOINT` | HuggingFace 镜像（国内常用 `https://hf-mirror.com`） |
| `SENTIMENT_MODEL_ID` / `DEVICE_PREFERENCE` | 情感模型与 cuda/cpu |
| `EMBEDDING_BACKEND` / `OLLAMA_*` | 主题向量（默认本机 Ollama） |
| `OPENAI_API_KEY` / `OPENAI_BASE_URL` / `OPENAI_MODEL` | 报告摘要 / Agent（OpenAI 兼容） |
| `OLLAMA_CHAT_MODEL` | 无云端 Key 时 Agent 回退 |
| `BILIBILI_SESSDATA` | B 站登录态（强烈建议；可填整段 Cookie） |

前端一般无需 Key；开发代理见 `frontend/vite.config.js`。

---

## 当前阶段

- **合并主线（A–F）**：脚手架 → 数据闭环 → GPU 情感 / 主题 → 预警趋势 → 报告导出 → B 站采集 + 轻量 Agent — 已交付
- **产品打磨**：设置就绪曝光、空库首跑引导、情感未完成提示、监测门禁文案与成功态 — 已交付
- **近程可选**：词典 vs BERT 实验表；Redis + RQ；多 BV / UP 聚合
- **明确不做（一期）**：登录多租户、全网实时监听、把产品锁死在校园舆情

详情：[`docs/prd.md`](docs/prd.md) · [`docs/positioning.md`](docs/positioning.md) · [`.trellis/GATE.md`](.trellis/GATE.md)

### Trellis（AI 协作）

已安装 [`@mindfoldhq/trellis`](https://github.com/mindfold-ai/Trellis) 并初始化 Cursor 平台。说明见 [`.trellis/README.md`](.trellis/README.md)。

```powershell
npm install -g @mindfoldhq/trellis@latest
# Windows 若找不到命令：
& "$env:APPDATA\npm\trellis.cmd" platforms
```

Cursor 内可用：`/trellis-continue`、`/trellis-finish-work`；Agent：`trellis-implement` / `trellis-check` / `trellis-research`。

---

## 文档

- [产品需求 PRD](docs/prd.md)
- [定位与演进](docs/positioning.md)
- [流程 / 架构图](docs/diagrams.md)
- [目录与分层约定](docs/directory-structure.md)
- [演示就绪 · 模型缓存](docs/model-cache.md)
- [真实采集 · 质量门禁](docs/real-data-collection.md)
- [文档索引](docs/README.md)
- [后端说明](backend/README.md)
- [前端说明](frontend/README.md)
- [协作入口 AGENTS](AGENTS.md)
- [Trellis 说明](.trellis/README.md)

---

## 许可与贡献

私有仓库。改需求请先对照 [`docs/prd.md`](docs/prd.md) 与 [`docs/positioning.md`](docs/positioning.md)；改接口须同步 `backend/src/api/` 与 `frontend/src/api/`。
