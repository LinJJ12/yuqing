# 知微 协作入口

产品名：**知微**。本地「观众反馈 / 内容口碑」分析工作台；属舆情分析，主战场非全网危机监测。不局限于校园：以 B 站评论口碑为主，校园样例为可选演示数据。

**许可**：仅供学习 / 教学 / 非营利研究，**禁止商用**。见 [`LICENSE`](LICENSE)。

- 产品需求（面向谁 / 功能 / 能做什么）：[`docs/prd.md`](docs/prd.md)
- 定位与演进（是否舆情、下一步）：[`docs/positioning.md`](docs/positioning.md)
- 文档索引：[`docs/README.md`](docs/README.md)
- 目录约定：[`docs/directory-structure.md`](docs/directory-structure.md)（含 API 垂直表与忽略路径说明）
- 流程与架构图：[`docs/diagrams.md`](docs/diagrams.md)
- 演示就绪（模型缓存）：[`docs/model-cache.md`](docs/model-cache.md)
- 真实采集（B 站内嵌 / 质量门禁 / MediaCrawler）：[`docs/real-data-collection.md`](docs/real-data-collection.md)
- 合并方案（历史）：[`.trellis/MERGE_PLAN.md`](.trellis/MERGE_PLAN.md) · [`.trellis/GATE.md`](.trellis/GATE.md)
- Trellis 工作流：[`.trellis/workflow.md`](.trellis/workflow.md)
- 后端分层：[`backend/src/README.md`](backend/src/README.md)

启动：

```powershell
uv run python backend/main.py --reload --port 8001
cd frontend; npm run dev
```

改接口时：同步 `backend/src/api/` 与 `frontend/src/api/`。

<!-- TRELLIS:START -->
# Trellis Instructions

These instructions are for AI assistants working in this project.

This project is managed by Trellis. The working knowledge you need lives under `.trellis/`:

- `.trellis/workflow.md` — development phases, when to create tasks, skill routing
- `.trellis/spec/` — package- and layer-scoped coding guidelines (read before writing code in a given layer)
- `.trellis/workspace/` — per-developer journals and session traces
- `.trellis/tasks/` — active and archived tasks (PRDs, research, jsonl context)

If a Trellis command is available on your platform (e.g. `/trellis:finish-work`, `/trellis:continue`), prefer it over manual steps. Not every platform exposes every command.

If you're using Codex or another agent-capable tool, additional project-scoped helpers may live in:
- `.agents/skills/` — reusable Trellis skills
- `.codex/agents/` — optional custom subagents

Managed by Trellis. Edits outside this block are preserved; edits inside may be overwritten by a future `trellis update`.

<!-- TRELLIS:END -->
