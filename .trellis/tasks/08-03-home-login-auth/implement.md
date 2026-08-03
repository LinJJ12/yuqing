# 实现计划：首页与登录鉴权

## Checklist

1. **后端配置**  
   - 在 `settings.py` 增加 `auth_username`、`auth_password`、`jwt_secret`、`jwt_expire_hours`（及可选 `auth_disabled`）。  
   - 更新 `.env.example`（若存在）与演示文档说明默认本地凭证。

2. **后端鉴权核心**  
   - 新增 `services/auth.py`（或 `lib/auth_tokens.py`）：签发/校验 JWT、比对凭证。  
   - 新增 `api/auth.py`：`POST /login`、`GET /me`、（可选）`POST /logout`。  
   - 新增 `Depends(require_user)`；在 `data/collect/analysis/alerts/reports/agent` 路由挂载（health 除外）。  
   - 在 `app.py` 注册 auth router。

3. **后端测试**  
   - 扩展 `conftest.py`：测试凭证 monkeypatch + 已登录 `client` / `auth_headers`。  
   - 新增 auth 用例；修正现有 API 测试以带 token。  
   - 验证：`uv run pytest backend/tests -q`。

4. **前端 auth 基建**  
   - `lib/auth.js`：token 存取、login/logout、`isAuthenticated`。  
   - `api/client.js`：login/me；请求拦截附加 Bearer；401 时可清 token（避免循环）。  
   - `router/index.js`：`/` → Home、`/login`、`/overview`；`meta.layout` / `requiresAuth`；`beforeEach`。

5. **前端页面与壳**  
   - `HomePage.vue`、`LoginPage.vue`（复用 tokens，无侧栏）。  
   - `App.vue`：public / app 双布局。  
   - `AppSidebar.vue`：总览 → `/overview`。  
   - `AppTopBar.vue`：登出。

6. **文档**  
   - `docs/prd.md` 范围与路由；API README；必要时 `AGENTS.md`。

7. **手工验收**  
   - 未登录打开业务页 → 登录页。  
   - 错误密码提示；正确密码进 `/overview`。  
   - 登出后再访 API/页面失败。  
   - `/` 无侧栏且风格一致。

## Validation Commands

```powershell
uv run pytest backend/tests -q
cd frontend; npm run build
```

（若有前端 lint 脚本则一并跑。）

## Risky Files / Rollback Points

| 文件 | 风险 |
|------|------|
| `backend/src/api/*.py` | 批量加 Depends，漏挂则留下未保护口 |
| `backend/tests/conftest.py` | 夹具错误导致全套测试红 |
| `frontend/src/api/client.js` | 拦截器与直连回退交互 |
| `frontend/src/App.vue` + `router/index.js` | 布局/守卫循环跳转 |
| `docs/prd.md` | 与实现不同步 |

回滚：按提交 revert；或临时 `AUTH_DISABLED`（若实现了）。

## Before `task.py start`

- [x] `prd.md` 已收敛  
- [x] `design.md` / `implement.md` 已写  
- [x] `implement.jsonl` / `check.jsonl` 已有真实 spec 条目  
- [x] 用户批准本规划摘要  

## Spec / Research Manifests

见同目录 `implement.jsonl`、`check.jsonl`（目录结构、API client、跨层指南、质量指南）。
