# frontend/ — 知微 Vue 3 工作台

上级规范：[docs/directory-structure.md](../docs/directory-structure.md)

## 职责

- **知微** UI：营销首页、本地登录、总览、监测、情感、主题、预警、报告、助手、设置。
- 经 Vite 代理访问后端 `/api`（默认 `127.0.0.1:8001`）。
- 会话：`src/lib/auth.js`（Bearer token）；工作台路由需登录。

```text
frontend/
├── public/
│   └── logo.png      # favicon / 公开直链（透明底品牌图）
├── scripts/          # node 冒烟：agent-session / auth-guard
├── src/
│   ├── api/          # 唯一 HTTP 出口
│   ├── pages/        # 路由页面（含 HomePage / LoginPage）
│   ├── router/       # 路由 + 鉴权守卫
│   ├── lib/          # auth · agentSession · datetime
│   ├── components/   # 共享组件（侧栏引用品牌 Logo）
│   ├── assets/
│   │   └── logo.png  # 侧栏等组件 import 用品牌图
│   ├── style.css     # 全局样式（Vite 惯例）
│   ├── App.vue
│   └── main.js
├── vite.config.js    # /api → 127.0.0.1:8001
└── package.json
```

品牌图：`src/assets/logo.png`（组件引用）与 `public/logo.png`（浏览器图标 / README）保持同图；白底已抠除为透明 PNG。

## 启动

```powershell
cd frontend
npm install
npm run dev
```

打开 http://127.0.0.1:5173 。公开：`/` 首页、`/login`；工作台从 `/overview` 起。细则见 [`src/README.md`](./src/README.md) 及子目录 README。

冒烟：

```powershell
npm run test:auth-guard
npm run test:agent-session
```

## 禁止

- 页面内裸 `fetch`/`axios` 直连后端（统一走 `src/api/`）
- 持有模型 Key、SQLite、推理逻辑
- 依赖 `vendor/` 或 `backend/src`
