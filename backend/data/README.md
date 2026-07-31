# `backend/data/` — 运行时数据

上级规范：[../README.md](../README.md)

## 职责

- 存放 SQLite、上传导入文件、样例 JSON 等本地运行产物。
- 默认整目录忽略；**合成样例**可进 Git：`samples/`。

## 布局

```text
data/
├── yuqing.db          # 主库（gitignore）
├── imports/           # 上传/转换落盘（gitignore）
└── samples/           # 合成样例 / 评测集（可提交；勿放真实用户数据）
    ├── campus_sample.json            # generate_sample_data.py
    ├── mediacrawler_xhs_fixture.json # 仿 MediaCrawler 字段
    └── sentiment_eval.json           # eval_sentiment.py 黄金集（口碑向短句）
```

## 禁止

- 把真实用户隐私数据提交到 Git
- 在文档中依赖本目录的固定绝对路径（应用 `config.settings`）
- 手改 DB 当「正式迁移」而不改 `storage/db.py` 建表逻辑
