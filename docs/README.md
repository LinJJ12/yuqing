# `docs/` — 跨端文档

上级：仓库根 [`README.md`](../README.md)

## 职责

- 存放**给人看**的跨端约定：目录规范、架构说明、大创材料索引。
- 本目录是「产品/协作真相」入口，不跑业务。

## 文件

| 文件 | 说明 |
|------|------|
| `directory-structure.md` | **主规范**：顶层职责、分层、API 对照表 |
| `diagrams.md` | **流程 · 思维导图 · 架构图**（Mermaid） |
| `model-cache.md` | **演示就绪**：模型预取、Ollama、OpenAI 兼容 LLM、检查清单 |
| `real-data-collection.md` | **真实采集**：内嵌 B 站评论（含话题回退）+ 外挂 MediaCrawler |
| `README.md` | 本说明 |

## 禁止

- 放入可执行业务代码、模型权重、`.env` 密钥
- 把仅后端细节写在这里而不回写 `backend/src/**/README.md`
