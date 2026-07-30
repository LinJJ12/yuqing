# 演示前：模型缓存与依赖就绪

> 目标：避免答辩/演示时因 **HF 下载失败** 或 **Ollama 未启动** 卡住。  
> 设置页会显示情感模型 / Ollama / 云端 LLM 就绪状态（`GET /api/v1/health/ready` → `readiness`）。

---

## 1. 情感模型（必做）

默认模型：`senlou/weibo-sentiment-chinese-bert`（微博域真三分类：正/中/负；经 `HF_ENDPOINT` 镜像拉取）。  
低置信（默认 `<0.55`）会标为 `uncertain`，并写入 `sentiment_confidence`。  
若需换回点评二分类：`SENTIMENT_MODEL_ID=uer/roberta-base-finetuned-dianping-chinese`（中性由阈值推断）。  
换模型后请全量重跑：`uv run python backend/scripts/rerun_sentiment.py`  
（系统也会把旧标签标为 `model_stale`，「分析待处理」会自动覆盖；`manual` / `llm` 改判不会被覆盖。）

采集/导入成功后会自动排队「待处理」情感任务。难例可在情感页人工改判或 LLM 复判（`GET /posts/review`、`PATCH /posts/{id}/sentiment`、`POST /analysis/sentiment/llm-review`）。

小黄金集评测：`uv run python backend/scripts/eval_sentiment.py`

```powershell
cd C:\Users\Administrator\Desktop\yuqing

# 确认 backend/.env 有镜像（国内推荐）
# HF_ENDPOINT=https://hf-mirror.com

uv run python backend/scripts/prefetch_models.py
```

成功后，设置页「情感模型」应显示 **本地缓存已就绪**。  
再到「情感」页点一次单句预测，把模型加载进 GPU（预热）。

离线排查：若预取失败，检查网络/代理，或换可用镜像后再跑脚本。

---

## 2. Ollama 嵌入（主题聚类推荐）

词云不依赖 Ollama；**BERTopic** 默认走本地 Ollama。

```powershell
# 启动 Ollama 后：
ollama pull quentinz/bge-large-zh-v1.5
# 与 backend/.env 中 OLLAMA_EMBED_MODEL 保持一致
```

设置页「Ollama」为绿即可放心做主题分析。

---

## 3. 云端 LLM（可选，OpenAI 兼容）

报告「AI 摘要」与智能助手优先走 OpenAI 兼容接口（火山引擎、阿里云百炼、DeepSeek、官方 OpenAI 等）：

```text
# backend/.env
OPENAI_API_KEY=...
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
OPENAI_MODEL=qwen-plus
```

示例见 `backend/.env.example`。未配置时摘要会跳过，Agent 可回退 Ollama Chat。

---

## 4. B 站 Cookie（可选，内嵌采集）

监测页「B 站评论采集」未配置 Cookie 时也能跑，但评论条数常被限制。建议：

```text
# backend/.env
# 可只填 SESSDATA，或粘贴浏览器整段 Cookie
BILIBILI_SESSDATA=...
```

详见 [`real-data-collection.md`](./real-data-collection.md)。修改后重启后端。

---

## 5. 演示最小清单

| 项 | 命令 / 位置 | 通过标准 |
|----|-------------|---------|
| 后端 | `uv run python backend/main.py --reload --port 8001` | `/docs` 可开 |
| 前端 | `cd frontend; npm run dev` | `5173` 可开 |
| 情感缓存 | `prefetch_models.py` | 设置页情感 = 已缓存 |
| GPU | 设置页设备信息 | `cuda: true`（有卡时） |
| Ollama | `ollama pull …` | 主题页 BERTopic 不报错 |
| 样例 | `generate_sample_data.py` + 监测页上传 | 总览有帖子 |
| B 站（可选） | 监测页采集 + `BILIBILI_SESSDATA` | 入库 `platform=bili` |

核心演示（导入→情感→预警→报告）只需 **情感缓存 + 后端**；主题聚类额外需要 Ollama；真评论演示建议配置 B 站 Cookie。
