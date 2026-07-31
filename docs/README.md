# `docs/` — 跨端文档（知微）

上级：仓库根 [`README.md`](../README.md)

## 职责

- 存放**给人看**的产品说明与跨端约定：PRD、定位、目录规范、架构、演示与采集。
- 本目录是「产品/协作真相」入口（产品名：**知微**），不跑业务。

## 先读哪份

| 问题 | 文档 |
|------|------|
| 面向谁？有哪些功能？能做什么？ | [`prd.md`](./prd.md) |
| 还算舆情吗？定位是什么？以后做成什么？ | [`positioning.md`](./positioning.md) |
| 文件夹怎么分？改接口改哪？ | [`directory-structure.md`](./directory-structure.md) |
| 数据怎么流、架构长什么样？ | [`diagrams.md`](./diagrams.md) |
| 演示前模型怎么准备？ | [`model-cache.md`](./model-cache.md) |
| 真实 B 站数据怎么采？ | [`real-data-collection.md`](./real-data-collection.md) |

## 文件

| 文件 | 说明 |
|------|------|
| `prd.md` | **产品需求**：用户、价值、功能范围、主路径、验收 |
| `positioning.md` | **定位与演进**：口碑工作台定位、舆情属性、路线图 |
| `directory-structure.md` | **主规范**：顶层职责、分层、API 对照表 |
| `diagrams.md` | **流程 · 思维导图 · 架构图**（Mermaid） |
| `model-cache.md` | **演示就绪**：模型预取、Ollama、OpenAI 兼容 LLM、检查清单 |
| `real-data-collection.md` | **真实采集**：内嵌 B 站（话题回退 / 质量门禁 / 口碑报告）+ MediaCrawler |
| `README.md` | 本说明 |

## 禁止

- 放入可执行业务代码、模型权重、`.env` 密钥
- 把仅后端细节写在这里而不回写 `backend/src/**/README.md`
