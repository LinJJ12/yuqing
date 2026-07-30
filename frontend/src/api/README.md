# `frontend/src/api/` — 后端客户端

上级规范：[../README.md](../README.md)

## 职责

- 封装 `/api/v1/*` 请求；解析 `{ok,data|error}`。
- `validateStatus` 放行 4xx 业务体，由调用方读 `error`。

## 文件

| 文件 | 说明 |
|------|------|
| `client.js` | Axios 实例、代理回退、各资源方法（含 `collectBilibili` / Agent） |

## 禁止

- 在本层写 DOM / Vue 组件
- 绕过本层在页面里散落裸 `axios.create`
- 假设响应一定是 200（业务失败常带 `ok:false`）
