# `frontend/src/pages/` — 路由页面

上级规范：[../README.md](../README.md)

## 职责

- 每个文件对应一个路由视图：总览、监测、情感、主题、预警、报告、助手、设置。
- 组合 `api/` 与图表库（ECharts），不实现后端算法。

## 页面

| 文件 | 路由 | 说明 |
|------|------|------|
| `OverviewPage.vue` | `/` | 库内快照 |
| `MonitorPage.vue` | `/monitor` | BV 采集（主）/ 关键词（次）/ 文件导入 / 噪声清理 |
| `SentimentPage.vue` | `/sentiment` | 情感预览与批量分析 |
| `TopicsPage.vue` | `/topics` | 词云 / 主题 |
| `AlertsPage.vue` | `/alerts` | 预警列表 |
| `ReportsPage.vue` | `/reports` | 全局汇总 + **单视频口碑**（`?bvid=`） |
| `AgentPage.vue` | `/agent` | 问答 / 简报（可选 BV 限定） |
| `SettingsPage.vue` | `/settings` | 就绪检查、敏感词 |

## 禁止

- 把可复用图表/表格复制多份而不抽到 `components/`（重复第三次时再抽）
- 在页面写 SQL / 模型推理逻辑
- 修改后端端口写死在页面（用代理与 `VITE_*`）
