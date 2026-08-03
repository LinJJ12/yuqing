# 设计：首页与登录鉴权

## Architecture

```text
公开：HomePage (/) · LoginPage (/login)
      └─ 无侧栏壳（meta.layout = public）

工作台：/overview · /monitor · … · /settings
      └─ 现有 AppSidebar + AppTopBar（meta.layout = app，需 auth）

前端 auth（lib/auth.js）
  ├─ localStorage 存 JWT
  ├─ axios 请求头 Authorization: Bearer
  └─ router.beforeEach 守卫

后端
  ├─ settings: AUTH_USERNAME / AUTH_PASSWORD / JWT_SECRET / JWT_EXPIRE_HOURS
  ├─ api/auth.py: login · me
  ├─ lib/auth.py 或 services/auth.py: 校验密码 · 签发/解析 JWT
  └─ Depends(require_user) 挂到业务路由（health + login 除外）
```

## Boundaries

| 层 | 职责 |
|----|------|
| `api/auth.py` | HTTP：login body、me、401/400 |
| `services/auth.py`（或 `lib/auth_tokens.py`） | 密码比对、JWT encode/decode；不读 Request |
| `config/settings.py` | 管理员凭证与 JWT 配置 |
| `frontend/src/lib/auth.js` | token 读写、isAuthenticated、logout |
| `frontend/src/api/client.js` | 登录 API + 请求拦截器附带 Bearer |
| `pages/HomePage.vue` / `LoginPage.vue` | 公开 UI |
| `App.vue` | 按 `route.meta.layout` 切换壳 |

不引入 users 表（账号模型 A）。不引入 Redis / 会话表。

## API Contracts

统一信封：`{ ok, data }` / `{ ok: false, error: { code, message } }`。

### `POST /api/v1/auth/login`

Request:

```json
{ "username": "admin", "password": "…" }
```

Success `data`:

```json
{
  "access_token": "<jwt>",
  "token_type": "bearer",
  "user": { "username": "admin" }
}
```

Failure: `401` + `code: invalid_credentials`（用户名或密码错误统一文案）。

### `GET /api/v1/auth/me`

Header: `Authorization: Bearer <jwt>`

Success `data`: `{ "username": "admin" }`  
Failure: `401` + `code: unauthorized`

### `POST /api/v1/auth/logout`（可选薄接口）

服务端可无状态返回 `ok`；前端必须清除本地 token。MVP 可仅前端登出，仍建议提供空操作 endpoint 以对称 API。

### 受保护路由

除以下外均需有效 JWT：

- `GET /api/v1/health/*`
- `POST /api/v1/auth/login`
- 应用根 `GET /`（后端元信息，非前端首页）

未授权：`401`，`error.code = unauthorized`。

## Token 方案

- **JWT**（HS256），claim 含 `sub`（username）、`exp`。
- 前端存 `localStorage`（键名如 `zhiwei.auth.token`），因 `client.js` 会回退直连 `127.0.0.1:8001`，Cookie 跨端口不可靠。
- 依赖：`PyJWT`（或项目已有等价库）；密码用 `hmac.compare_digest` 比对明文环境变量即可（本地单机）；文档提醒勿把生产密码提交进仓库。若实现成本低可用 bcrypt 哈希环境变量 `AUTH_PASSWORD_HASH`，但 MVP 以 `AUTH_PASSWORD` 明文配置为默认并写清风险。

## Frontend Routing

| path | name | layout | auth |
|------|------|--------|------|
| `/` | home | public | no |
| `/login` | login | public | no |
| `/overview` | overview | app | yes |
| 其余现有业务路由 | … | app | yes |

- `/` 不再 redirect 到总览。
- 守卫：`meta.requiresAuth !== false` 的 app 路由需登录；登录成功后 `redirect` query 或默认 `/overview`。
- 侧栏总览 `to: '/overview'`；`exact` 匹配相应调整。
- TopBar 增加登出按钮（仅 app 壳）。

## Compatibility

- 书签 `/`：从总览变为首页（有意破坏）；总览新地址 `/overview`。
- 开发默认凭证写入 `.env.example`（非密钥仓库），如 `admin` / 文档约定的本地口令；真实口令仅本地 `.env`。
- pytest：`conftest` 提供 `auth_headers` 或自动 login fixture；`monkeypatch` 固定测试用 username/password/jwt_secret。

## Trade-offs

| 选择 | 收益 | 代价 |
|------|------|------|
| 环境变量单用户，无 DB | 实现快、符合本地工作台 | 改密需改 env 并重启 |
| Bearer JWT + localStorage | 兼容 Vite 代理与直连回退 | XSS 可窃 token；本地可信环境可接受 |
| 全业务 API 强制鉴权 | 「真鉴权」名副其实 | 测试与脚本需带 token |

## Rollback

- 功能开关可选：`AUTH_DISABLED=1` 跳过校验（仅建议测试/紧急）；默认关闭。若不想加开关，回滚即 revert 本任务提交。
- 前端：去掉守卫与公开页即可恢复旧壳；总览路径需一并还原或保留 `/overview` redirect。

## Docs touchpoints

- `docs/prd.md`：功能表增加首页/登录；删除或改写「不做登录」；路由列表更新。
- `AGENTS.md` / `docs/README.md` 若写死 `/` 为总览则同步。
- `frontend/src/api/README.md`、`backend/src/api/README.md` 补充 auth。
