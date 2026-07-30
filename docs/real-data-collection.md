# 真实数据采集（外挂 MediaCrawler）

> 一期：文件导入。二期：**本机独立爬取 → 转换 → 监测页导入**。  
> 系统内**不**内嵌二维码登录采集台。演示前请先看 [`model-cache.md`](./model-cache.md)。

---

## 合规

- 仅用于学习 / 大创演示，遵守平台 ToS 与当地法规。
- **不要**把真实用户隐私数据提交到 Git；`backend/data/imports/` 已忽略。
- 仓库内夹具 `backend/data/samples/mediacrawler_xhs_fixture.json` 为**合成数据**，仿真实字段名。

---

## 流程

```text
MediaCrawler（本机）
  → data/<platform>/json|jsonl
  → uv run python backend/scripts/convert_mediacrawler.py ...
  → backend/data/imports/converted_*.json
  → 监测页选择平台并上传
  → 情感 / 主题 / 预警 / Agent
```

---

## 1. 安装并运行 MediaCrawler

仓库：[NanmiCoder/MediaCrawler](https://github.com/NanmiCoder/MediaCrawler)

建议（示意，以官方 README 为准）：

```powershell
# 单独目录克隆，勿放进 yuqing/vendor 当运行时依赖
git clone https://github.com/NanmiCoder/MediaCrawler.git
cd MediaCrawler
# 按官方文档用 uv/pip 安装；抖音等可能需要 Node.js >= 16
```

配置要点（`config/base_config.py` 或 CLI 参数）：

| 项 | 建议 |
|----|------|
| `PLATFORM` | `xhs` / `dy` / `wb` 等 |
| `KEYWORDS` | 校园相关词，如 `食堂,宿舍,校园网` |
| `CRAWLER_TYPE` | `search` |
| `SAVE_DATA_OPTION` | `json` 或 `jsonl` |
| 登录 | 二维码 / Cookie（按官方说明） |

示例：

```powershell
python main.py --platform xhs --lt qrcode --type search
```

导出一般在 MediaCrawler 的 `data/xhs/`、`data/douyin/`、`data/weibo/` 下。

---

## 2. 转换为 Yuqing 格式

在 **yuqing 仓库根**：

```powershell
# 转换整个导出目录（从路径推断平台，或显式 --platform）
uv run python backend/scripts/convert_mediacrawler.py D:\MediaCrawler\data\xhs --platform xhs

# 可选：把评论展平为独立帖
uv run python backend/scripts/convert_mediacrawler.py D:\MediaCrawler\data\xhs --platform xhs --include-comments
```

输出：`backend/data/imports/converted_xhs_<时间>.json`。

无爬虫时可用夹具验证：

```powershell
uv run python backend/scripts/convert_mediacrawler.py backend/data/samples/mediacrawler_xhs_fixture.json --platform xhs
```

---

## 3. 导入并分析

1. 打开监测页 `/monitor`
2. **平台**选 `小红书 (xhs)` / `抖音 (dy)` / …
3. 上传转换后的 JSON
4. 到「情感」跑分析，「预警 / 报告 / 智能助手」查看结果

字段别名已在 [`backend/src/services/normalize.py`](../backend/src/services/normalize.py) 扩展（`note_id`、`desc`、`create_time` 等），多数导出可直接导入；转换脚本用于批量扫盘与评论可选处理。

---

## 平台码

| 监测页 | MediaCrawler |
|--------|----------------|
| `xhs` | 小红书 |
| `dy` | 抖音 |
| `wb` | 微博 |
| `bili` | B 站 |
| `campus` | 校园样例 / 通用 |
