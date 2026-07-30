# 演示前：模型缓存与依赖就绪

> 目标：避免答辩/演示时因 **HF 下载失败** 或 **Ollama 未启动** 卡住。  
> 设置页会显示情感模型 / Ollama / 云端 LLM 就绪状态（`GET /api/v1/health/ready` → `readiness`）。

---

## 1. 情感模型（必做）

默认模型：`uer/roberta-base-finetuned-dianping-chinese`（经 `HF_ENDPOINT` 镜像拉取）。

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

## 4. 演示最小清单

| 项 | 命令 / 位置 | 通过标准 |
|----|-------------|---------|
| 后端 | `uv run python backend/main.py --reload --port 8001` | `/docs` 可开 |
| 前端 | `cd frontend; npm run dev` | `5173` 可开 |
| 情感缓存 | `prefetch_models.py` | 设置页情感 = 已缓存 |
| GPU | 设置页设备信息 | `cuda: true`（有卡时） |
| Ollama | `ollama pull …` | 主题页 BERTopic 不报错 |
| 样例 | `generate_sample_data.py` + 监测页上传 | 总览有帖子 |

核心演示（导入→情感→预警→报告）只需 **情感缓存 + 后端**；主题聚类额外需要 Ollama。
