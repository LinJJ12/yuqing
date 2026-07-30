# `frontend/src/components/` — 共享组件

上级规范：[../README.md](../README.md)

## 职责

- 跨页面复用的纯展示/交互组件。
- 当前：`layout/` 壳层（侧栏、顶栏），对齐 OmniStream 布局拆分；页面级 `PageHeader`。

## 结构

| 路径 | 说明 |
|------|------|
| `layout/AppSidebar.vue` | 品牌 Logo「知微」、主导航、顶部收起 |
| `layout/AppTopBar.vue` | 面包屑、后端连接状态、刷新 |
| `PageHeader.vue` | 页面标题 + 副标题 + actions 插槽 |

## 禁止

- 直接调用后端业务接口并缓存全局状态（状态用 Pinia，请求经 `api/`）
- 用 emoji 当图标（用 `@lucide/vue`）
- 塞进「半个页面」的巨型组件而不拆
