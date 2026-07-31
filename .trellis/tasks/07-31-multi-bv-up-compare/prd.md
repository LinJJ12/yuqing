# 多 BV / UP 口碑对比

## Goal

让创作者与运营在知微内**并排对比**多条视频（BV）或同一 UP 主下多稿的情感 / 热度 / 高频词，而不是只能一次看一个 `bvid`。

## Background

- 现行能力：`list_bilibili_videos`、单视频 `build_video_report`、全站 `?bvid=` 作用域。
- 缺口：无法一次选 2～N 个 BV 对比；采集 `raw.extra` 目前有 `bvid` / `aid` / `video_title`，**尚未稳定写入 UP `mid`**，UP 聚合需先补采集字段。

## Requirements

1. **多 BV 对比 API**：接受 2～8 个 `bvid`，返回每个视频的评论数、正/中/负/uncertain 占比、最近入库时间、可选 top 关键词（轻量，不做全量 BERTopic）。
2. **前端对比页或报告子视图**：在报告页或独立入口选择多个已入库视频，表格 + 简易对比柱状图；深链 `?bvids=BV1,BV2`。
3. **UP 维度（二期同任务可拆子任务）**：采集时写入 `raw.extra.mid` + `owner_name`；提供 `GET /reports/ups` 与 `GET /reports/up?mid=` 聚合该 UP 下各 BV 摘要。
4. **空态与上限**：未选满 2 个 BV 时禁用对比；超过上限返回 `400`；未知 BV 在结果里标记 `missing` 而非整单失败。
5. **测试**：pytest 覆盖对比 API（临时库插入两条 bili 帖）；前端不强制 e2e，但 `client.js` 必须同步。

## Acceptance Criteria

- [ ] `GET` 或 `POST /api/v1/reports/compare`（或等价路径）对 2+ BV 返回可渲染的对比结构
- [ ] 报告页（或新页）能完成「选片 → 看对比」主路径，无需手改 URL
- [ ] 采集新评论时 `raw.extra` 含 `mid`（若接口可得）；旧数据无 mid 时 UP 列表可空但不报错
- [ ] `uv run pytest` 含对比契约用例且通过
- [ ] `frontend/src/api/client.js` 与 `docs/prd.md` 功能表已更新

## Out of scope

- 跨平台（抖音/微博）账号对齐
- 自动爬取「该 UP 全部历史稿」（仅聚合**已入库** BV）
- 登录与多人协作权限

## Notes

- Complex task：实现前补 `design.md` + `implement.md`，并在 `implement.jsonl` / `check.jsonl` 引用 `spec/backend/*` 与 `spec/frontend/*`。
- 优先落地 **多 BV 对比**；UP 聚合可作为同任务后半或子任务，避免阻塞演示。
