# `backend/src` — 分层入口

上级规范：[../README.md](../README.md) · [../../docs/directory-structure.md](../../docs/directory-structure.md)

```text
api/  →  services/*  →  storage / config
设备与模型配置只出自 config/
情感 / 主题 / 导入 / B 站采集与质量门禁 / 预警 / 视频口碑 / Agent 在 services/
SQLite 只经 storage/
lib/ 仅放无业务词工具（如 http 响应封装）
```

| 目录 | 一句话 | 禁止 | 细则 |
|------|--------|------|------|
| `api/` | HTTP 边界（`alerts` / `reports` 分文件） | 写模型推理细节 | [api/README.md](./api/README.md) |
| `services/` | 可复用单步能力 | 直接操作 HTTP Request | [services/README.md](./services/README.md) |
| `storage/` | 唯一落盘 | 调 LLM / Ollama | [storage/README.md](./storage/README.md) |
| `config/` | 配置与设备探测 | 业务规则 | [config/README.md](./config/README.md) |
| `lib/` | 无业务工具 | 堆业务代码 | [lib/README.md](./lib/README.md) |

调用关系：

```text
前端
  └─ api/ ──► services/ ──► storage/
                 │
                 └─ config/（settings、CUDA、Ollama 地址）
```
