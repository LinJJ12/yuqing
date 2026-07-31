# `.trellis/` — 合并方案与门禁

上级规范：[docs/directory-structure.md](../docs/directory-structure.md)

## 职责

- 记录「两参考仓 → 合并工程」的计划、Gate 决策、阶段验收标准。
- 供人或 AI 按阶段执行，避免范围漂移。

## 文件

| 文件 | 说明 |
|------|------|
| `MERGE_PLAN.md` | Triage → Plan → Gate → Execute → Verify |
| `GATE.md` | 已确认的技术选型（Vue / SQLite / BERT / Ollama 等） |
| `README.md` | 本说明 |

产品级说明（面向谁、定位、演进）不在本目录，见 [`docs/prd.md`](../docs/prd.md)、[`docs/positioning.md`](../docs/positioning.md)。

## 禁止

- 当作运行时配置目录（端口、模型路径应在 `backend/.env`）
- 把可运行业务代码堆在这里
- 与 `docs/directory-structure.md` 长期矛盾而不回改
