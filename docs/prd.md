# 知微 — 产品需求文档（PRD）

> 版本：0.2 · 状态：现行产品说明  
> 关联：[定位与演进](./positioning.md) · [架构图](./diagrams.md) · [真实采集](./real-data-collection.md) · [Trellis](../.trellis/README.md)

---

## 1. 一句话

**知微**是面向内容创作者、运营与教学演示的本地工作台：从社交媒体（当前以 **B 站评论**为主）采集观众反馈，做情感 / 主题 / 趋势分析，输出预警与口碑报告。

---

## 2. 面向谁（用户与场景）

| 角色 | 要解决什么 | 典型用法 |
|------|------------|----------|
| **UP 主 / 内容团队** | 单视频或一批视频「观众怎么说」 | 贴 BV → 采集评论 → 洞察看情感与词云 → 出单视频口碑报告 |
| **运营 / 品宣** | 话题或内容是否翻车、负面是否突增 | 监测入库 → 预警中心 → PDF/CSV 汇总给协作方 |
| **学生 / 大创答辩** | 可演示的完整闭环（采集→分析→报告） | 样例数据或真实 BV；设置页检查模型就绪 |
| **研究者 / 二次开发** | 可替换模型栈的本地分析底座 | FastAPI + SQLite；改 `services/` 与 `.env`；`uv run pytest` |

**非目标用户（一期不做）**

- 需要多租户 SaaS、权限审批流的大型政企舆情中台
- 仅要「一键爬全网」且不关心分析质量的纯爬虫用户
- 必须云端托管、零本地 GPU/依赖的纯网页消费用户

---

## 3. 产品能做什么（价值主张）

1. **把评论变成可行动洞察**：正/中/负情感、主题词、趋势曲线，而不是原始评论堆。
2. **单视频口碑闭环**：按 `bvid` 看该稿的情感分布、高频词、规则结论，可选 LLM 观众反馈摘要。
3. **可配置预警**：负面占比、敏感词、热度突增等规则，避免「事后才发现翻车」。
4. **本地可控**：数据落本机 SQLite；情感可走 GPU BERT；LLM/Ollama 按需启用，密钥不进前端。
5. **演示与交付一体**：总览工作台 + PDF/CSV + 智能助手问答/简报，适合汇报与答辩。

---

## 4. 功能范围

### 4.1 已交付（现行）

| 模块 | 用户可见能力 | 关键能力 |
|------|--------------|----------|
| **舆情监测** | BV 评论采集（主）、关键词采集（次）、JSON/CSV 导入、噪声清理 | 内嵌 B 站采集、质量门禁（标题/空评/刷评）、文件 ingest |
| **入库浏览** | 按平台筛选、关键词搜索、翻页；手工增删改；行内情感改判；按 id 批量删除 | `GET/POST/PATCH/DELETE /posts*`、`q` 搜索、`/posts/delete` |
| **总览** | 帖子量、话题与情感快照；空库三步首跑引导 | dashboard overview |
| **洞察** | 情感跑批 / 分布 / 预览；词云 · TF-IDF · BERTopic；后台 analysis-jobs（合并原情感页+话题页） | BERT 三分类 + uncertain；jieba / TF-IDF + BERTopic |
| **预警中心** | 负面/敏感词命中、热度突增；难例人工/LLM 改判；敏感词可配置 | 规则引擎 + 趋势日聚合 + review 列表 |
| **趋势** | 滑动平均；可选 Prophet（预警页/报告共用） | `forecast` |
| **分析报告** | 全局汇总；单视频口碑；CSV/PDF 导出；可选 AI 摘要 | `report` / `video_report` |
| **智能助手** | 多会话隔离问答与简报（可限定 BV）；切页不丢；请求代数防串写 | OpenAI 兼容或 Ollama Chat；`frontend/src/lib/agentSession.js` |
| **系统设置** | 情感模型 / Ollama / 云端 LLM / B 站 Cookie 就绪检查；设备信息；敏感词 | readiness |

路由要点：主路径为 `/` · `/monitor` · `/inbox` · `/insights` · `/alerts` · `/reports` · `/agent` · `/settings`。旧 `/sentiment`、`/topics` 重定向到 `/insights`（带 `tab`）。

### 4.2 明确不做（当前边界）

| 不做 | 原因 |
|------|------|
| 登录 / 多用户权限 | 一期本地单机工作台 |
| TextCNN / LDA / ARIMA / SIR | 已替换为 BERT / BERTopic / 滑动平均·Prophet / 增长率峰值 |
| 全平台自动调度爬虫中台 | 采集以 B 站内嵌 + 可选外挂 MediaCrawler 为主 |
| 实时流式全网监听 | 当前为按需拉取与文件导入 |

详见 [定位与演进](./positioning.md) 中的路线图。

---

## 5. 用户主路径

```text
① 监测页贴 BV（或导入文件）→ 入库
② 洞察页跑情感 / 看词云（或采集后自动入队）
③ 入库页可搜索核对；总览 / 预警看异常 → 报告页出全局或单视频口碑
④ （可选）助手页多会话问答 / 生成简报 → PDF/CSV 交付
```

演示防翻车：启动前按 [`model-cache.md`](./model-cache.md) 预取模型并确认设置页就绪。

---

## 6. 非功能需求

| 维度 | 要求 |
|------|------|
| 运行形态 | 本机前后端分离；默认后端 `8001`、前端 `5173` |
| 存储 | 一期 SQLite（`backend/data/`） |
| 性能 | GPU 可用时 BERT/嵌入上 GPU；无 GPU 则 CPU 降级并日志提示 |
| 安全 | 密钥仅 `backend/.env`；前端不持有模型 Key |
| 可维护 | 改接口须同步 `backend/src/api/` 与 `frontend/src/api/` |
| 测试 | `uv run pytest`（`backend/tests`，含 posts / import / alerts / reports / jobs）；前端 `node scripts/agent-session-check.mjs`；完整冒烟 `backend/scripts/smoke_test.py` |
| AI 协作 | 可选 Trellis（`.trellis/` + Cursor 命令）；会话脚本默认不自动 commit |
| 品牌 | 产品名「知微」；仓库目录名 `yuqing` 仅为路径，不代表品牌 |

---

## 7. 成功标准（验收视角）

- [x] 仅用真实 BV，可不依赖校园样例完成「采集→情感→主题→单视频报告」
- [x] 设置页能区分情感缓存 / **B 站 Cookie** / Ollama / 云端 LLM 就绪状态，并有「演示前 3 步」清单
- [x] 空库总览给出三步首跑引导（监测 → 洞察 → 报告），而非空图表
- [x] 情感未跑完时单视频报告标明「未完成」，不假装口碑已定论
- [x] 预警敏感词可改且立即影响后续判定；placeholder 为口碑向示例
- [x] 报告可导出 PDF 与 CSV
- [x] 洞察合并情感与话题；旧路由可重定向
- [x] 入库支持搜索与帖子 CRUD；助手多会话不串写
- [x] `uv run pytest` 可在忽略 vendor 后通过
- [ ] 文档读者能在 10 分钟内回答：面向谁、有哪些功能、能做什么（本文 + [positioning.md](./positioning.md)）

> 2026-07 演示主路径打磨：设置 Cookie 就绪、总览首跑、报告 pending 提示、监测门禁文案与成功态 stats、预警/助手跳转。  
> 2026-07-31：洞察页合并、入库 CRUD、pytest、Trellis 初始化。

---

## 8. 文档与代码对照

| 想了解 | 去哪看 |
|--------|--------|
| 为什么这样定位、以后做成什么 | [positioning.md](./positioning.md) |
| 页面与路由 | `frontend/src/pages/README.md` |
| 服务能力 | `backend/src/services/README.md` |
| 目录与 API 垂直表 | [directory-structure.md](./directory-structure.md) |
| 合并历史决策 | `.trellis/MERGE_PLAN.md` · `.trellis/GATE.md` |
| Trellis 工作流 / spec | [`.trellis/README.md`](../.trellis/README.md) |
