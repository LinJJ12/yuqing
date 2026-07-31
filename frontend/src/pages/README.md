# `frontend/src/pages/` — 路由页面

上级规范：[../README.md](../README.md)

## 职责

- 每个文件对应一个路由视图：总览、监测、入库、洞察、预警、报告、助手、设置。
- 组合 `api/` 与图表库（ECharts），不实现后端算法。

## 页面

| 文件 | 路由 | 说明 |
|------|------|------|
| `OverviewPage.vue` | `/` | 库内快照；空库首跑引导 |
| `MonitorPage.vue` | `/monitor` | BV 采集（主）/ 关键词（次）/ 文件导入 / 噪声清理 |
| `InboxPage.vue` | `/inbox` | 入库浏览：搜索 · 增删改 · 行内改判 · 批量删除 |
| `InsightsPage.vue` | `/insights` | 情感跑批 · 分布 · 词云话题（旧 `/sentiment` `/topics` 会重定向） |
| `AlertsPage.vue` | `/alerts` | 预警列表 · 难例改判 · 热度趋势 |
| `ReportsPage.vue` | `/reports` | 全局汇总 + **单视频口碑**（`?bvid=`） |
| `AgentPage.vue` | `/agent` | 多会话问答 / 简报（可选 BV 限定） |
| `SettingsPage.vue` | `/settings` | 就绪检查、敏感词 |

## 禁止

- 把可复用图表/表格复制多份而不抽到 `components/`（重复第三次时再抽）
- 在页面写 SQL / 模型推理逻辑
- 修改后端端口写死在页面（用代理与 `VITE_*`）
