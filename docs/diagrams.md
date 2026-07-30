# Yuqing：流程 · 思维导图 · 架构图

> **Yuqing** 是社交媒体舆情 / 观众反馈工作台：文件导入 / B 站评论采集 → 本地 GPU 情感 / 主题分析 → 趋势预警 → 报告导出。不局限于校园场景。  
> **一期已结项：** Vue 3 工作台 + FastAPI BFF + SQLite；**无登录**；采集为文件导入。  
> **二期已落地：** 外挂 MediaCrawler 转换导入；**内嵌 B 站评论采集**；轻量 Agent（问答 + 简报）。  
> 下图均为 Mermaid，可在支持 Mermaid 的编辑器中预览。目录细则见 [`directory-structure.md`](./directory-structure.md)，真实采集见 [`real-data-collection.md`](./real-data-collection.md)。

---

## 1. 用户主流程

### 1.1 演示闭环（导入 → 分析 → 图表 → 报告）

```mermaid
flowchart TD
    A[打开 Web 工作台<br/>http://127.0.0.1:5173] --> B[总览页看帖子量快照]
    B --> C{数据从哪来?}
    C -->|文件| C1[监测页上传 JSON / CSV]
    C -->|B 站| C2[监测页 B 站评论采集]
    C1 --> D[后端规范化 + 去重入库]
    C2 --> D
    D --> E[情感页：同步分析或后台任务]
    E --> F[热点话题：词云 / BERTopic]
    F --> G[预警中心：负面/敏感词 + 热度趋势]
    G --> H[报告页：汇总 / PDF / CSV]
    H --> I[设置页：健康检查 · 改敏感词]
    I --> B
```

### 1.2 单次文件导入

```mermaid
flowchart TD
    A[用户选择文件并上传] --> B[前端 FormData<br/>POST /api/v1/imports]
    B --> C[api/data 校验后缀与大小]
    C --> D[落盘 backend/data/imports/]
    D --> E[services/ingest 解析<br/>JSON / JSONL / CSV]
    E --> F[normalize_post<br/>统一字段 + 词典情感占位]
    F --> G[storage 插入 posts<br/>UNIQUE platform+source_id]
    G --> H[回写 import_jobs 统计]
    H --> I[前端刷新帖子列表 / 总览]
```

### 1.2b B 站评论采集（内嵌）

```mermaid
flowchart TD
    A[监测页填写关键词或 BV] --> B[POST /api/v1/collect/bilibili]
    B --> C[api/collect 校验参数]
    C --> D[services/bilibili_collect]
    D --> E{有 video?}
    E -->|是| F[view 解析 aid]
    E -->|否| G[search/all/v2 或 HTML 抽 BV]
    G --> F
    F --> H[reply/main 拉评论<br/>含二级回复]
    H --> I[normalize_post platform=bili]
    I --> J[storage 入库 + import_jobs]
    J --> K[前端刷新任务与帖子列表]
```

### 1.3 情感分析（同步 vs 异步）

```mermaid
flowchart TD
    A[用户点击分析] --> B{同步还是后台?}
    B -->|同步| C[POST /analysis/sentiment/run]
    B -->|后台| D[POST /analysis-jobs<br/>kind=sentiment]
    D --> E[analysis_jobs 入队<br/>进程内线程池执行]
    C --> F[services/sentiment<br/>中文 RoBERTa GPU]
    E --> F
    F --> G[写回 posts<br/>sentiment_label / method=bert]
    G --> H[前端刷新统计与柱状图]
    E --> I[前端轮询 GET /analysis-jobs/id]
    I -->|succeeded / failed| H
```

### 1.4 报告导出（含可选 AI 摘要）

```mermaid
flowchart TD
    A[报告页重新生成] --> B[GET /reports/summary]
    B --> C[汇总 overview · sentiment · alerts · trend]
    C --> D{用户点 AI 摘要?}
    D -->|是| E{已配置 OPENAI_API_KEY?}
    E -->|否| F[提示跳过]
    E -->|是| G[OpenAI 兼容接口生成中文摘要]
    G --> C2[页面展示 ai_summary]
    D -->|否| H[直接看页面汇总]
    C2 --> I{导出?}
    H --> I
    I -->|CSV| J[GET /reports/export.csv]
    I -->|PDF| K[GET /reports/export.pdf]
    J --> L[浏览器下载]
    K --> L
```

### 1.5 版本演进路线（产品流程视角）

```mermaid
flowchart LR
    P1[一期 已结项<br/>文件导入<br/>BERT+BERTopic<br/>预警+Prophet<br/>PDF/CSV]
    P2[二期 已落地<br/>外挂 MediaCrawler<br/>内嵌 B 站评论<br/>轻量 Agent]
    P3[另阶段<br/>词典 vs BERT 实验<br/>可选 Redis+RQ]
    P1 --> P2 --> P3
```

---

## 2. 产品思维导图

### 2.1 总览

```mermaid
mindmap
  root((Yuqing 舆情分析))
    用户
      演示与研究同学
      内容运营 / 口碑观察
    价值
      本地 GPU 情感
      主题可解释
      预警可配置
      报告可下载
    场景
      B 站视频评论口碑
      文件导入多平台
      情感分布对比
      热点话题发现
      负面敏感预警
      日报导出
    一期已结
      Vue3 八业务页
      FastAPI 统一包络
      SQLite
      词典加 BERT
      词云加 BERTopic
      滑动平均加 Prophet
      analysis-jobs
      PDF CSV 云端LLM可选
      无登录
    二期已落地
      外挂 MediaCrawler 转换导入
      内嵌 B 站评论采集
      监测平台选择
      轻量 Agent 问答与简报
    明确不做近期
      登录鉴权
      多 Agent 编排
      小红书抖音内嵌登录爬虫台
    另阶段可选
      词典 vs BERT 实验
      Redis 加 RQ
```

### 2.2 功能模块脑图（研发拆分视角）

```mermaid
mindmap
  root((模块拆分))
    前端 Web
      总览 Overview
      监测 Monitor
      助手 Agent
      情感 Sentiment
      话题 Topics
      预警 Alerts
      报告 Reports
      设置 Settings
      api client 唯一出口
    后端 BFF
      health 含 CUDA
      data 导入帖子总览
      collect B站评论
      analysis 情感主题
      analysis-jobs 异步
      alerts trends reports
      agent 问答简报
      settings 敏感词
    分析能力 services
      ingest normalize
      bilibili_collect
      sentiment BERT
      topics BERTopic
      forecast Prophet预警
      report PDF CSV
      agent
      jobs 线程池
      ollama_embed
    存储
      posts
      import_jobs
      analysis_jobs
      app_settings
    外部可选
      HuggingFace 模型
      Ollama 向量
      OpenAI 兼容摘要
      B站公开接口
```

---

## 3. 项目架构图

### 3.1 系统逻辑架构（一期）

```mermaid
flowchart TB
    subgraph Client["客户端 · Vue 3 工作台"]
        Pages[pages/* 业务页]
        ApiFE[src/api/client.js<br/>唯一 HTTP 出口]
        Pages --> ApiFE
    end

    subgraph BFF["backend · FastAPI BFF"]
        API[api/<br/>校验 · 状态码 · ok/err]
        SVC[services/<br/>ingest · bilibili_collect<br/>sentiment · topics<br/>forecast · report · agent · jobs]
        CFG[config/<br/>settings · device CUDA]
        API --> SVC
        SVC --> CFG
    end

    subgraph Data["数据层"]
        DB[(SQLite<br/>posts · jobs · settings)]
        FS[data/imports · samples]
    end

    subgraph Ext["外部 / 本地推理"]
        BERT[中文 RoBERTa<br/>GPU / CPU]
        OLL[Ollama 嵌入<br/>BERTopic]
        DS[OpenAI 兼容 LLM<br/>可选报告摘要 / Agent]
        BILI[B 站公开接口<br/>可选 SESSDATA]
    end

    ApiFE -->|HTTP /api/v1| API
    SVC --> DB
    API --> FS
    SVC --> BERT
    SVC --> OLL
    SVC -.->|可选| DS
    SVC -.->|可选| BILI
```

**调用关系一句话：**

```text
浏览器 → frontend/src/api → backend/src/api → services → storage
设备与模型配置只出自 config/；SQLite 只经 storage/
```

### 3.2 导入 → 情感 → 预警 时序

```mermaid
sequenceDiagram
    actor U as 用户
    participant FE as Vue 前端
    participant API as FastAPI api/
    participant SVC as services
    participant DB as storage/SQLite
    participant M as BERT / Ollama

    U->>FE: 上传 JSON/CSV
    FE->>API: POST /imports
    API->>SVC: ingest + normalize
    SVC->>DB: insert posts / import_jobs
    API-->>FE: ok + stats

    U->>FE: 分析待处理 / 后台任务
    FE->>API: POST /analysis/sentiment/run<br/>或 /analysis-jobs
    API->>SVC: sentiment.predict_batch
    SVC->>M: GPU 推理
    M-->>SVC: label + scores
    SVC->>DB: update sentiment_*
    API-->>FE: stats / job status

    U->>FE: 打开预警 / 报告
    FE->>API: GET /alerts · /trends · /reports/*
    API->>SVC: detect_alerts · daily_volume · report
    SVC->>DB: list_posts / overview
    API-->>FE: 图表数据 / PDF·CSV
```

### 3.3 仓库目录结构

```mermaid
flowchart TB
    ROOT[yuqing/]
    ROOT --> DOCS[docs/<br/>directory-structure · diagrams]
    ROOT --> TRE[/.trellis/<br/>MERGE_PLAN · GATE]
    ROOT --> FE[frontend/<br/>Vue 3]
    ROOT --> BE[backend/<br/>FastAPI]
    ROOT --> VEN[vendor/<br/>参考仓只读]

    FE --> F1[src/pages · router · components]
    FE --> F2[src/api 唯一 HTTP]

    BE --> B1[src/api]
    BE --> B2[src/services]
    BE --> B3[src/storage · config · lib]
    BE --> B4[data/ 运行时 · scripts/]
```

**文字版目录（摘要；细目见 directory-structure.md）：**

```text
yuqing/
├── README.md
├── AGENTS.md
├── docs/
│   ├── directory-structure.md   ← 目录与 API 垂直表
│   ├── diagrams.md              ← 本文件
│   └── README.md
├── .trellis/                    ← 合并方案与阶段门禁
├── frontend/
│   └── src/{pages,api,router,components,assets}
├── backend/
│   ├── main.py
│   ├── src/{api,services,storage,config,lib}
│   ├── data/                    ← DB / imports / samples（gitignore）
│   ├── scripts/                 ← 样例生成、冒烟
│   └── docs/                    ← 后端专用备忘
├── vendor/                      ← 参考仓，非运行时
└── pyproject.toml               ← uv + 根 .venv
```

### 3.4 数据关系（概念）

```mermaid
erDiagram
    IMPORT_JOB ||--o{ POST : inserts
    ANALYSIS_JOB ||--o| POST : updates_sentiment
    APP_SETTINGS ||--o{ ALERT_RULE : configures

    IMPORT_JOB {
        string id
        string filename
        string status
        string stats_json
    }
    POST {
        int id
        string platform
        string source_id
        string text
        string topic
        string sentiment_label
        string sentiment_method
    }
    ANALYSIS_JOB {
        string id
        string kind
        string status
        string params_json
        string result_json
    }
    APP_SETTINGS {
        string key
        string value_json
    }
```

> 说明：`ALERT_RULE` 为逻辑概念；现行实现是 `app_settings.key=alert_keywords` 的词表，由 `services/forecast.detect_alerts` 消费。

### 3.5 前后端 API 垂直对照

| 前端能力 | `frontend/src/api` | 后端路由 |
|----------|-------------------|----------|
| 健康 / CUDA | `fetchHealthReady` | `/api/v1/health/*` |
| 总览 / 帖子 / 导入 / 清理 | `fetchOverview` · `fetchPosts` · `uploadImport` · `deletePosts` | `/dashboard/overview` · `/posts` · `/posts/delete` · `/imports` |
| B 站采集 | `collectBilibili` | `/collect/bilibili` |
| 情感 / 主题 | `runSentiment` · `runTopics` · … | `/analysis/sentiment*` · `/analysis/topics*` |
| 异步任务 | `createAnalysisJob` · `fetchAnalysisJob` | `/analysis-jobs` |
| 预警 / 趋势 | `fetchAlerts` · `fetchTrends` | `/alerts` · `/trends` |
| 报告 / 视频口碑 | `fetchReportSummary` · `fetchVideoReport` · `fetchVideoSummaries` · export | `/reports/summary` · `/reports/video` · `/reports/videos` · `/reports/export.*` |
| 助手 | `agentChat` · `agentBrief`（可选 `bvid`） | `/agent/chat` · `/agent/brief` |
| 敏感词 | `fetchAlertKeywords` · `saveAlertKeywords` | `/settings/alert-keywords` |

统一响应：`{ "ok": true, "data": ... }` / `{ "ok": false, "error": { "code", "message" } }`。

---

## 4. 页面信息架构

```mermaid
flowchart TB
    O["/ 总览"] --> M["/monitor 舆情监测"]
    O --> S["/sentiment 情感分析"]
    O --> T["/topics 热点话题"]
    O --> A["/alerts 预警中心"]
    O --> R["/reports 分析报告"]
    O --> AG["/agent 智能助手"]
    O --> SET["/settings 系统设置"]

    M -->|贴 BV 采集| R
    M -->|清理噪声| M
    R -->|?bvid 口碑| AG
    S --> T
    T --> A
    A --> R
    SET -.->|改敏感词影响| A
```

**已有：** 总览、监测（BV 采集 / 导入 / 噪声清理）、情感、话题、预警（含 Prophet 趋势）、报告（全局汇总 + 单视频口碑）、助手（可选 BV 观众反馈）、设置（健康 + 敏感词）。  
**没有：** 登录页、家长/权限页、爬虫配置台、多 Agent 画布。

---

## 5. 图例说明

| 图 | 用途 |
|----|------|
| §1 流程图 | 演示闭环、导入、情感同步/异步、报告导出怎么走 |
| §2 思维导图 | 范围边界、模块拆分、防范围膨胀 |
| §3 架构图 | `api → services → storage`、目录落地、数据关系、API 对照 |
| §4 信息架构 | 八个业务页有哪些、没有哪些 |

如需导出 PNG/SVG，可用 Mermaid CLI 或 IDE 插件对上述代码块导出。
