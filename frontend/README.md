# frontend/ — Vue 3 舆情工作台

上级规范：[docs/directory-structure.md](../docs/directory-structure.md)

## 职责

- 校园舆情工作台 UI：总览、监测、情感、主题、预警、报告、设置。
- 经 Vite 代理访问后端 `/api`（默认 `127.0.0.1:8001`）。

```text
frontend/
├── src/
│   ├── api/          # 唯一 HTTP 出口
│   ├── pages/        # 路由页面
│   ├── router/
│   ├── components/   # 共享组件（按需）
│   ├── assets/
│   ├── App.vue
│   └── main.js
├── vite.config.js    # /api → 127.0.0.1:8001
└── package.json
```

## 启动

```powershell
cd frontend
npm install
npm run dev
```

打开 http://127.0.0.1:5173 。细则见 [`src/README.md`](./src/README.md) 及子目录 README。

## 禁止

- 页面内裸 `fetch`/`axios` 直连后端（统一走 `src/api/`）
- 持有模型 Key、SQLite、推理逻辑
- 依赖 `vendor/` 或 `backend/src`
