# `frontend/src/pages/` — 路由页面

上级规范：[../README.md](../README.md)

## 职责

- 每个文件对应一个路由视图：总览、监测、情感、主题、预警、报告、设置。
- 组合 `api/` 与图表库（ECharts），不实现后端算法。

## 页面

| 文件 | 路由 |
|------|------|
| `OverviewPage.vue` | `/` |
| `MonitorPage.vue` | `/monitor` |
| `SentimentPage.vue` | `/sentiment` |
| `TopicsPage.vue` | `/topics` |
| `AlertsPage.vue` | `/alerts` |
| `ReportsPage.vue` | `/reports` |
| `AgentPage.vue` | `/agent` |
| `SettingsPage.vue` | `/settings` |

## 禁止

- 把可复用图表/表格复制多份而不抽到 `components/`（重复第三次时再抽）
- 在页面写 SQL / 模型推理逻辑
- 修改后端端口写死在页面（用代理与 `VITE_*`）
