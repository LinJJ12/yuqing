# `.trellis/` — Trellis 工作流 + 合并历史

上级规范：[docs/directory-structure.md](../docs/directory-structure.md)

本目录同时承担两件事：

1. **Trellis 工程框架**（`@mindfoldhq/trellis`）：任务 PRD、workflow、spec、journal、Cursor 命令/Agent  
2. **知微合并历史文档**：`MERGE_PLAN.md` / `GATE.md`（两参考仓合并决策，只读归档）

## Trellis（现行）

| 路径 | 说明 |
|------|------|
| `workflow.md` | Plan → Execute → Finish；技能路由 |
| `config.yaml` | 项目级 Trellis 配置 |
| `spec/` | 分层编码约定（写代码前按层阅读） |
| `tasks/` | 进行中 / 已归档任务（PRD、research、jsonl） |
| `workspace/` | 开发者 journal / 会话痕迹 |
| `scripts/` | `task.py` 等本地任务脚本 |
| `agents/` | 平台无关 Agent 定义源 |

Cursor 集成生成在仓库根：`.cursor/commands`、`.cursor/agents`、`.cursor/skills`、`.cursor/hooks`。

### 本机 CLI

```powershell
npm install -g @mindfoldhq/trellis@latest
# 若 PowerShell 找不到命令，用完整路径或把 %AppData%\npm 加入 PATH：
#   & "$env:APPDATA\npm\trellis.cmd" --version
trellis platforms
trellis update --cursor
```

开发者身份：`.developer`（已 gitignore，勿提交）。当前用户：`Administrator`。

会话自动提交默认关闭（见 `config.yaml` 的 `session_auto_commit`），避免未经确认就 git commit。

常用斜杠命令（Cursor）：`/trellis-continue`、`/trellis-finish-work`。

## 合并历史（归档）

| 文件 | 说明 |
|------|------|
| `MERGE_PLAN.md` | 合并期 Triage → Plan → Gate → Execute → Verify |
| `GATE.md` | 已确认技术选型（Vue / SQLite / BERT 等） |

产品级说明仍在 [`docs/prd.md`](../docs/prd.md)、[`docs/positioning.md`](../docs/positioning.md)。

## 禁止

- 当作运行时配置目录（端口、模型路径应在 `backend/.env`）
- 把可运行业务代码堆在这里
- 与 `docs/directory-structure.md` 长期矛盾而不回改
- 把 `.developer` / 本机 journal 当共享事实源强行覆盖他人
