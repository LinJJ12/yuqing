# `backend/src/config/` — 配置与设备

上级规范：[../README.md](../README.md)

## 职责

- 集中管理环境变量与默认值（`settings.py`）。
- 探测 CUDA / GPU（`device.py`），供情感推理选设备。
- 定义数据目录：`backend/data/`（DB、imports、samples）。

## 文件

| 文件 | 说明 |
|------|------|
| `settings.py` | `Settings`：端口、模型、Ollama、OpenAI 兼容 LLM、B 站 Cookie、主题/预警关键词 |
| `device.py` | `get_device_info` / `resolve_device` |

## 约定

- `.env` 优先读 `backend/.env`，其次仓库根 `.env`。
- LLM / HF / Ollama / `BILIBILI_SESSDATA` **只出自本目录**；其它层经 `settings` 引用。
- `BILIBILI_SESSDATA` 可填单字段或整段 Cookie（由 `bilibili_collect` 解析）。

## 禁止

- 写业务规则（敏感词表可放 `services/forecast`，不放这里膨胀）
- 直接读写帖子表
- 在本层发 HTTP 业务请求
