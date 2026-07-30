# yuqing — 校园舆情（Python + Vue + GPU）

统一环境 + 合并工程。目录约定见 [`docs/directory-structure.md`](docs/directory-structure.md)，方案见 [`.trellis/MERGE_PLAN.md`](.trellis/MERGE_PLAN.md)。

结构对齐桌面 **chatbot / OmniStream**：`frontend/` + `backend/` 并列，参考仓在 `vendor/`。

## 分析栈

| 能力 | 方案 |
|------|------|
| 情感 | 词典快筛 + 中文 RoBERTa/BERT（正/中/负，GPU） |
| 主题 | 词云 + BERTopic（本地 Ollama 向量） |
| 趋势 | 滑动平均 |
| 预警 | 负面/敏感词 + 热度突增 |

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

### 样例数据

```powershell
uv run python backend/scripts/generate_sample_data.py
# 监测页上传 backend/data/samples/campus_sample.json
```

## 目录

| 路径 | 说明 |
|------|------|
| `frontend/` | Vue 3 正式前端 |
| `backend/` | FastAPI 正式后端（`src/api|services|storage|config`） |
| `vendor/` | 参考仓（只读） |
| `docs/` | 跨端目录约定 |
| `.trellis/` | 合并方案与门禁 |
