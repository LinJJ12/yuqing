# backend/ — 知微 FastAPI BFF

分层约定对齐桌面旁路仓 **chatbot / OmniStream**（前后端分离、`api` 薄入口、能力在 `services`、落盘在 `storage`）。

```text
backend/
├── main.py                 # 进程入口
├── .env.example            # 含 AUTH_* / JWT_* 等
├── data/                   # 运行时数据（gitignore）
├── scripts/                # 样例生成等
├── docs/                   # 后端专用文档
└── src/
    ├── api/                # HTTP：校验、组响应；auth / alerts / reports 分文件
    ├── config/             # settings + device（含本地管理员凭证）
    ├── services/           # 单步能力：鉴权 / 情感 / 主题 / 导入 / B站采集 / 口碑 / Agent
    ├── storage/            # SQLite 唯一业务 I/O
    └── lib/                # 极瘦无业务工具（含 UnauthorizedError）
```

业务 API（除健康检查与 `/auth/login`）需 `Authorization: Bearer`。默认管理员见 `.env.example`。
## 启动

在仓库根目录（共用根 `.venv`）：

```powershell
cd C:\Users\Administrator\Desktop\yuqing
uv run python backend/main.py --reload --port 8001
```

文档：http://127.0.0.1:8001/docs

冒烟：`uv run python backend/scripts/smoke_test.py`

分层细则见各子目录 README：`src/api` · `src/services` · `src/storage` · `src/config` · `src/lib` · `scripts` · `data` · `docs`。

## 禁止

- `api/` 内直接加载 HuggingFace / Ollama 客户端（应经 `services/`）
- `storage/` 依赖 `api/`
- 把业务逻辑堆进 `lib/`
- 运行时 `import vendor/`
