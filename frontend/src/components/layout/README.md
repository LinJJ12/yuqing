# `frontend/src/components/layout/` — 壳层布局

上级规范：[../README.md](../README.md)

## 职责

- 应用壳：侧栏导航、顶栏状态；不含业务页面内容。

## 文件

| 文件 | 说明 |
|------|------|
| `AppSidebar.vue` | 品牌 Logo、主导航、收起 |
| `AppTopBar.vue` | 面包屑、后端连接状态、刷新 |

## 禁止

- 在此发起业务分析请求（经页面 → `api/`）
- 持有模型密钥或拼后端绝对 URL
