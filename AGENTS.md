# Yuqing 协作入口

- 目录约定：[`docs/directory-structure.md`](docs/directory-structure.md)
- 流程与架构图：[`docs/diagrams.md`](docs/diagrams.md)
- 演示就绪（模型缓存）：[`docs/model-cache.md`](docs/model-cache.md)
- 真实采集（B 站内嵌 / MediaCrawler）：[`docs/real-data-collection.md`](docs/real-data-collection.md)
- 合并方案：[`.trellis/MERGE_PLAN.md`](.trellis/MERGE_PLAN.md)
- 后端分层：[`backend/src/README.md`](backend/src/README.md)

启动：

```powershell
uv run python backend/main.py --reload --port 8001
cd frontend; npm run dev
```

改接口时：同步 `backend/src/api/` 与 `frontend/src/api/`。
