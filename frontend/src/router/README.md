# `frontend/src/router/` — 路由表

上级规范：[../README.md](../README.md)

## 职责

- 声明路径 ↔ 页面组件；侧栏高亮依赖 `exact`/`meta` 时在此统一。
- `meta.layout`：`public`（首页/登录，无侧栏）或 `app`（工作台壳）。
- `beforeEach`：未登录访问 `requiresAuth` / `layout=app` → `/login?redirect=`；已登录访问登录页 → `/overview`。

## 文件

| 文件 | 说明 |
|------|------|
| `index.js` | `createRouter` + routes + 鉴权守卫 |

## 禁止

- 在路由守卫里做重业务（仅 token 有无判断；登录请求走 `api/client.js`）
- 在本层发 API 请求
