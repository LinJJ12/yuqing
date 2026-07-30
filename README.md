# yuqing — 社交媒体舆情 / 观众反馈分析（Python + Vue + GPU）

统一环境 + 合并工程。目录约定见 [`docs/directory-structure.md`](docs/directory-structure.md)，流程与架构图见 [`docs/diagrams.md`](docs/diagrams.md)，方案见 [`.trellis/MERGE_PLAN.md`](.trellis/MERGE_PLAN.md)。

结构对齐桌面 **chatbot / OmniStream**：`frontend/` + `backend/` 并列，参考仓在 `vendor/`。不局限于校园场景：以 B 站视频评论口碑分析为主，文件导入与校园样例仍可用。

## 分析栈

| 能力 | 方案 |
|------|------|
| 情感 | 词典快筛 + 中文 RoBERTa/BERT（正/中/负，GPU） |
| 主题 | 词云 + BERTopic（本地 Ollama 向量） |
| 趋势 | 滑动平均 + Prophet |
| 预警 | 负面/敏感词（可配置）+ 热度突增 |
| 报告 | 页面汇总 + PDF/CSV；可选 OpenAI 兼容摘要 |
| 采集 | 文件导入；内嵌 B 站评论；外挂 MediaCrawler（见 docs/real-data-collection.md） |
| 助手 | 舆情问答 + 简报（OpenAI 兼容 / Ollama Chat） |

## 环境

```powershell
cd C:\Users\Administrator\Desktop\yuqing
.\.venv\Scripts\activate
uv sync
```

## 启动

```powershell
# 终端 1 — 后端
cd C:\Users\Administrator\Desktop\yuqing
uv run python backend/main.py --reload --port 8001
# http://127.0.0.1:8001/docs

# 终端 2 — 前端
cd C:\Users\Administrator\Desktop\yuqing\frontend
npm run dev
# http://127.0.0.1:5173
```

### 样例数据（可选）

校园主题演示包仍可用，不代表产品限定校园：

```powershell
uv run python backend/scripts/generate_sample_data.py
# 监测页上传 backend/data/samples/campus_sample.json（平台码 campus = 样例/导入）
```

日常演示更推荐：监测页贴 **BV** 采集真实 B 站评论，再跑情感 / 主题 / 报告。

### 演示前（防翻车）

```powershell
# 预取情感模型到本机缓存（国内请在 backend/.env 设 HF_ENDPOINT=https://hf-mirror.com）
uv run python backend/scripts/prefetch_models.py

# 主题聚类还需 Ollama：
# ollama pull quentinz/bge-large-zh-v1.5
```

详情见 [`docs/model-cache.md`](docs/model-cache.md)。设置页可查看情感 / Ollama / 云端 LLM 就绪状态。

## 目录

| 路径 | 说明 |
|------|------|
| `frontend/` | Vue 3 正式前端 |
| `backend/` | FastAPI 正式后端（`src/api|services|storage|config`） |
| `vendor/` | 参考仓（只读） |
| `docs/` | 跨端目录约定 |
| `.trellis/` | 合并方案与门禁 |
