# `frontend/src/router/` — 路由表

上级规范：[../README.md](../README.md)

## 职责

- 声明路径 ↔ 页面组件；侧栏高亮依赖 `exact`/`meta` 时在此统一。

## 文件

| 文件 | 说明 |
|------|------|
| `index.js` | `createRouter` + routes |

## 禁止

- 在路由守卫里做重业务（鉴权二期可加，需改本 README）
- 在本层发 API 请求（登录守卫除外，若引入须注明）
