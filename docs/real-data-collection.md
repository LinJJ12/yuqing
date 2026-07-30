# 真实数据采集

> 一期：文件导入。二期：外挂 MediaCrawler + **内嵌 B 站评论采集**。  
> 产品定位：**不局限于校园**——以 B 站视频评论口碑 / 多平台舆情为主；`campus` 平台码仅为通用导入与历史样例。  
> 系统内**不**内嵌小红书/抖音二维码登录台。演示前请先看 [`model-cache.md`](./model-cache.md)。

---

## 合规

- 仅用于学习 / 大创演示，遵守平台 ToS 与当地法规；控制频率与条数。
- **不要**把真实用户隐私数据或 Cookie 提交到 Git；`backend/.env` 与 `backend/data/imports/` 已忽略。
- 仓库内夹具 `backend/data/samples/mediacrawler_xhs_fixture.json` 为**合成数据**，仿真实字段名。

---

## A. 内嵌：B 站评论（推荐演示）

| 位置 | 说明 |
|------|------|
| 前端 | 监测页 `/monitor` →「B 站评论采集」 |
| API | `POST /api/v1/collect/bilibili` |
| 服务 | `backend/src/services/bilibili_collect.py` |
| 路由 | `backend/src/api/collect.py` |
| 配置 | `BILIBILI_SESSDATA`（`backend/.env`） |

### 推荐用法

| 目标 | 建议 |
|------|------|
| 分析**单个视频**口碑 | 填 **BV / 链接**（优先），不必填关键词 |
| 按主题搜一批视频 | 填较具体的关键词（如 `数码评测`），少用过宽单字词 |
| 自定义话题标签 | 填「话题」字段；否则见下方回退规则 |

### 请求示例

```http
POST /api/v1/collect/bilibili
Content-Type: application/json

{
  "video": "BV1xxxxxxxx",
  "max_comments_per_video": 40
}
```

或按关键词搜索：

```json
{
  "keyword": "数码评测",
  "max_videos": 2,
  "max_comments_per_video": 40,
  "topic": "口碑"
}
```

有 `video` 时优先按单视频拉评论。入库平台码为 `bili`，并记入 `import_jobs`。

### 话题（topic）回退

`resolve_collect_topic`（`bilibili_collect.py`）规则：

1. 请求里显式 `topic`
2. 否则用搜索 `keyword`（截断）
3. 否则用解析到的**视频标题**（适合只填 BV）
4. 再否则 `"B站评论"`

### Cookie（强烈建议）

未登录时平台常只返回少量一级评论。在 `backend/.env`：

```env
# 可只填 SESSDATA 值，或粘贴浏览器整段 Cookie（会自动解析 SESSDATA / bili_jct / DedeUserID 等）
BILIBILI_SESSDATA=...
```

获取方式：浏览器登录 [bilibili.com](https://www.bilibili.com) → 开发者工具 → Application/存储 → Cookies → 复制 `SESSDATA`，或复制整段 Cookie。修改后**重启后端**。

### 数据流

```text
关键词 / BV
  → search/all/v2（失败则 HTML 抽 BV）
  → view 解析 aid + 标题
  → reply 拉评论（含二级回复）
  → resolve_collect_topic → normalize_post → SQLite（platform=bili）
```

列表 / 总览 / 趋势默认按 **`fetched_at`（入库时间）** 优先，避免样例假发布时间主导曲线。

---

## B. 外挂 MediaCrawler（多平台）

### 流程

```text
MediaCrawler（本机独立仓库）
  → data/<platform>/json|jsonl
  → uv run python backend/scripts/convert_mediacrawler.py ...
  → backend/data/imports/converted_*.json
  → 监测页选择平台并上传
  → 情感 / 主题 / 预警 / Agent
```

### 1. 安装并运行 MediaCrawler

仓库：[NanmiCoder/MediaCrawler](https://github.com/NanmiCoder/MediaCrawler)

```powershell
# 单独目录克隆，勿放进 yuqing/vendor 当运行时依赖
git clone https://github.com/NanmiCoder/MediaCrawler.git
cd MediaCrawler
```

| 项 | 建议 |
|----|------|
| `PLATFORM` | `xhs` / `dy` / `wb` 等 |
| `KEYWORDS` | 与场景相关的词，如 `评测,探店,开箱` |
| `SAVE_DATA_OPTION` | `json` 或 `jsonl` |

### 2. 转换为 Yuqing 格式

在 **yuqing 仓库根**：

```powershell
uv run python backend/scripts/convert_mediacrawler.py D:\MediaCrawler\data\xhs --platform xhs
uv run python backend/scripts/convert_mediacrawler.py backend/data/samples/mediacrawler_xhs_fixture.json --platform xhs
```

输出：`backend/data/imports/converted_xhs_<时间>.json`。

### 3. 导入并分析

1. 监测页上传转换后的 JSON（平台选 `xhs` / `dy` / …）
2. 「情感」跑分析 → 「预警 / 报告 / 智能助手」

字段别名见 `backend/src/services/normalize.py`。

---

## 平台码

| 码 | 说明 |
|----|------|
| `bili` | B 站（**内嵌**采集或外挂导入） |
| `xhs` | 小红书（外挂） |
| `dy` | 抖音（外挂） |
| `wb` | 微博（外挂） |
| `campus` | 通用文件导入 / 历史样例数据 |

---

## 目录归属（防放错）

| 能力 | 应放位置 | 不应放 |
|------|----------|--------|
| B 站拉评论 | `services/bilibili_collect.py` + `api/collect.py` | `scripts/` 被 API import、`frontend` 直连 B 站 |
| MediaCrawler 转换 | `scripts/convert_mediacrawler.py` | `services/` 运行时依赖爬虫仓 |
| Cookie / Key | `backend/.env`（gitignore） | 提交进 Git、写进页面 |
| 导入落盘 | `backend/data/imports/`（gitignore） | `docs/`、仓库根 |
