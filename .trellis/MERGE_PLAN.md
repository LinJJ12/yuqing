# Trellis 任务：合并两仓为「知微」舆情系统（Python + Vue + GPU）

> 产品名：**知微**。工作流：Triage → Plan → Gate → Execute → Verify  
> 环境：`yuqing/.venv`（uv + Python 3.11 + torch cu128）  
> GPU：NVIDIA GeForce RTX 5070（需 sm_120 / CUDA 12.8+）  
> **模型栈（已更新）**：中文三分类 BERT（GPU，低置信 uncertain）+ 人工/LLM 难例改判 + BERTopic + 滑动平均/Prophet；入库不写词典情感；不做 TextCNN / LDA / ARIMA / SIR

---

## 0. Triage（现状诊断）

| 来源仓 | 强项 | 弱项 / 与目标冲突 |
|--------|------|-------------------|
| `social-media-sentiment-analysis` | 完整产品闭环（导入→任务→预警→PDF）；SQLite；RQ；报告 | 前端非 Vue；旧模型栈（TextCNN/LDA/SIR/ARIMA）将被替换 |
| `campus_sentiment_analysis` | 校园场景、预警审核、FastAPI、采集思路 | 前端是 React（改 Vue）；MySQL/Agent 一期简化 |

**目标产品定位（大创）**  
多平台观众反馈 / B 站评论口碑监测（校园样例可选）：导入或采集 → GPU 情感 → 主题/趋势 → 预警与报告 → Vue 工作台。

---

## 1. Plan（合并架构）

### 1.1 目标技术栈

```
前端:  Vue 3 + Vite + Vue Router + Pinia + ECharts
后端:  FastAPI + 可选 RQ Worker
存储:  一期 SQLite
情感:  中文三分类 BERT（默认 weibo-sentiment；GPU；低置信 uncertain）
主题:  TF-IDF 词云 + BERTopic（嵌入可走 GPU / Ollama）
趋势:  日聚合 + 滑动平均；可选 Prophet
传播:  不做 SIR → 增长率 / 峰值检测
报告:  PDF/CSV；可选 OpenAI 兼容摘要；单视频口碑
采集:  文件导入；内嵌 B 站评论；外挂 MediaCrawler
```

### 1.2 仓库布局

```
yuqing/
├── .venv/
├── pyproject.toml
├── .trellis/
├── social-media-sentiment-analysis/   # 参考
├── campus_sentiment_analysis/         # 参考
└── app/                               # ★ 正式工程
    ├── backend/
    │   ├── main.py
    │   ├── api/
    │   ├── core/          # config, device(CUDA)
    │   ├── services/
    │   │   ├── ingest.py
    │   │   ├── sentiment.py   # 三分类 BERT + uncertain
    │   │   ├── topics.py      # 词云 + BERTopic
    │   │   ├── forecast.py    # 滑动平均 / Prophet
    │   │   ├── alert.py       # 增长率 + 校园规则
    │   │   └── report.py
    │   └── workers/
    └── frontend/            # Vue 3
```

### 1.3 模块取舍

| 能力 | 主来源 | 合并方式 |
|------|--------|----------|
| 登录 / 任务状态 | social | FastAPI 会话或 JWT |
| 导入去重 | social | 移植 |
| 情感 | 新实现 | `senlou/weibo-sentiment-chinese-bert` 真三分类（GPU）；换模自动失效旧标签 |
| 主题 | 新实现 | jieba 词频 + BERTopic（替代 LDA） |
| 趋势 | 新实现 | 滑动平均 / Prophet（替代 ARIMA） |
| 传播 | 新实现 | 增长率与峰值（替代 SIR） |
| 预警规则 | 新实现 | B 站口碑敏感词 + BERT 负面（设置页可改） |
| Agent / 爬虫 | campus | 已落地轻量 Agent + 内嵌 B 站采集 |
| 前端 | 新建 Vue | 信息架构参考 campus 页面 |

### 1.4 GPU 策略（RTX 5070）

1. `torch` cu128，启动探测 CUDA，失败则 CPU + 日志。  
2. **上 GPU**：BERT 情感批量推理；BERTopic 用的嵌入模型。  
3. **留 CPU**：jieba、滑动平均、Prophet、预警规则。  
4. 12GB 显存：BERT batch 16～64；嵌入 batch 32～64。

### 1.5 API 契约

统一：`{ "ok": true, "data": ... }` / `{ "ok": false, "error": { "code", "message" } }`

| 方法 | 路径 | 用途 |
|------|------|------|
| POST | `/api/v1/imports` | 上传数据 |
| POST | `/api/v1/analysis-jobs` | 异步分析任务 |
| GET  | `/api/v1/analysis-jobs/{id}` | 任务状态 |
| GET  | `/api/v1/dashboard/overview` | 总览 |
| GET  | `/api/v1/alerts` | 预警 |
| GET  | `/api/v1/trends` | 趋势（滑动平均 + Prophet） |
| GET  | `/api/v1/reports/summary` | 报告汇总 |
| POST | `/api/v1/reports/summary` | 报告汇总（可选 AI） |
| GET  | `/api/v1/reports/export.csv` | 导出 CSV |
| GET  | `/api/v1/reports/export.pdf` | 导出 PDF |
| GET/PUT | `/api/v1/settings/alert-keywords` | 预警敏感词 |
| GET  | `/api/v1/health/live` | 存活 |
| GET  | `/api/v1/health/ready` | 含 `cuda` |

---

## 2. Gate

见 [GATE.md](GATE.md)（默认已确认：校园 + Vue + SQLite + GPU BERT + 文件导入 + Agent 二期）。

---

## 3. Execute

### Phase A — 脚手架 ✅ 已完成
1. `app/backend` FastAPI + health（CUDA）  
2. `app/frontend` Vue3 Vite，代理后端  
3. README 启动说明  

### Phase B — 数据闭环 ✅ 已完成
导入 + SQLite + 前端监测上传页 + 校园样例数据脚本

### Phase C — GPU 分析核心 ★ ✅ 已完成
1. 词典快筛 + 中文 BERT（CUDA）  
2. 词云 + BERTopic  
3. 情感分布 / 主题接口 + 前端页  

### Phase D — 趋势与预警 ✅ 已完成（基础版）
1. 日聚合 + 滑动平均  
2. 增长率峰值 + 校园敏感词/负面预警  
3. 预警中心 / 报告 / 设置页（不再占位）

### Phase E — 报告与打磨 ✅ 已完成（无登录 / 无答辩文档）
PDF/CSV 导出、可选 OpenAI 兼容摘要、Prophet、异步 analysis-jobs、预警敏感词可配置

### Phase F — 增强
- [x] 外挂 MediaCrawler 转换导入 + 监测平台选择（见 `docs/real-data-collection.md`）
- [x] 内嵌 B 站评论采集（`/collect/bilibili`，可选 `BILIBILI_SESSDATA`）
- [x] 轻量 Agent（问答 + 简报）
- [ ] 词典 vs BERT 对比实验表、Redis+RQ  

---

## 4. Verify

| 项 | 标准 |
|----|------|
| CUDA | health/ready 返回 `cuda: true` |
| 闭环 | 上传 → 分析 → 图表 → 报告 |
| GPU | 日志 `device=cuda`，BERT 推理明显快于 CPU |
| 前端 | Vue ≥ 6 业务页 |
| 叙事 | 文档写明替代旧栈的理由与创新点 |

---

## 5. 大创创新点（更新）

1. **本地 GPU 中文 BERT 情感流水线**（主判断不依赖云 API）  
2. **BERTopic 主题发现**（相对 LDA 更贴现代 NLP）  
3. **可解释趋势与预警**（滑动平均/Prophet + 增长率，避免难解释的 SIR）  
4. **多方法可对比**：词典快筛 vs BERT，写进论文实验表  

---

## 6. 启动（现行目录）

```powershell
cd C:\Users\Administrator\Desktop\yuqing
uv run python backend/main.py --reload --port 8001

cd frontend
npm run dev
```
