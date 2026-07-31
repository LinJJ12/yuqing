# 知微 协作入口

产品名：**知微**。本地「观众反馈 / 内容口碑」分析工作台；属舆情分析，主战场非全网危机监测。不局限于校园：以 B 站评论口碑为主，校园样例为可选演示数据。

- 产品需求（面向谁 / 功能 / 能做什么）：[`docs/prd.md`](docs/prd.md)
- 定位与演进（是否舆情、下一步）：[`docs/positioning.md`](docs/positioning.md)
- 文档索引：[`docs/README.md`](docs/README.md)
- 目录约定：[`docs/directory-structure.md`](docs/directory-structure.md)（含 API 垂直表与忽略路径说明）
- 流程与架构图：[`docs/diagrams.md`](docs/diagrams.md)
- 演示就绪（模型缓存）：[`docs/model-cache.md`](docs/model-cache.md)
- 真实采集（B 站内嵌 / 质量门禁 / MediaCrawler）：[`docs/real-data-collection.md`](docs/real-data-collection.md)
- 合并方案：[`.trellis/MERGE_PLAN.md`](.trellis/MERGE_PLAN.md)
- 后端分层：[`backend/src/README.md`](backend/src/README.md)

启动：

```powershell
uv run python backend/main.py --reload --port 8001
cd frontend; npm run dev
```

改接口时：同步 `backend/src/api/` 与 `frontend/src/api/`。
