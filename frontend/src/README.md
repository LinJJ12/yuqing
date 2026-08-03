# `frontend/src/` — Vue 应用源码

上级规范：[../README.md](../README.md) · [../../docs/directory-structure.md](../../docs/directory-structure.md)

## 职责

- 路由、页面、API 客户端、共享组件与静态资源。
- 所有页面经 `api/` 访问后端，不硬编码业务库路径。

## 子目录

| 目录 | 说明 |
|------|------|
| `api/` | Axios 封装与 typed 接口 |
| `pages/` | 路由级页面 |
| `router/` | Vue Router |
| `lib/` | 非 UI 助手：`auth.js`（会话）、`agentSession.js`、`datetime.js` |
| `components/` | 可复用 UI（可选） |
| `assets/` | 静态资源（品牌 `logo.png`；公开副本见 `frontend/public/logo.png`） |

入口：`main.js` · `App.vue` · `style.css`（全局样式，Vite 惯例放在 `src/` 根）

## 禁止

- 在页面内直接 `fetch('http://127.0.0.1:8001/...')`（统一走 `api/client.js` + Vite 代理）
- 引入后端 `src/` 或 `vendor/`
- 把密钥写进前端代码
