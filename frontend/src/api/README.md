# `frontend/src/api/` — 后端客户端

上级规范：[../README.md](../README.md)

## 职责

- 封装 `/api/v1/*` 请求；解析 `{ok,data|error}`。
- `validateStatus` 放行 4xx 业务体，由调用方读 `error`。
- Vite 代理失败时回退直连 `http://127.0.0.1:8001/api/v1`。

## 文件

| 文件 | 说明 |
|------|------|
| `client.js` | Axios 实例与各资源方法 |

主要方法：`login` / `fetchAuthMe` / `logoutApi`、`collectBilibili`、`deletePosts`、`fetchVideoReport` / `fetchVideoSummaries`、`compareVideos`、`fetchUpSummaries` / `fetchUpReport`、`agentChat` / `agentBrief`（可传 `bvid`）、`downloadReportExport`（CSV/PDF，带 Bearer）等。

鉴权：请求自动附带 `Authorization: Bearer`（见 `lib/auth.js`）；业务接口 401 时清除本地会话。报告导出须走 `downloadReportExport`，勿对受保护路径使用裸 `window.open`。

## 禁止

- 在本层写 DOM / Vue 组件
- 绕过本层在页面里散落裸 `axios.create`
- 假设响应一定是 200（业务失败常带 `ok:false`）
