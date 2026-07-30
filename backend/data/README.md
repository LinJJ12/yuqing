# `backend/data/` — 运行时数据（不进 Git）

上级规范：[../README.md](../README.md)

## 职责

- 存放 SQLite、上传导入文件、样例 JSON 等本地运行产物。
- 整目录已在根 `.gitignore` 中忽略。

## 布局（运行后生成）

```text
data/
├── yuqing.db          # 主库
├── imports/           # 上传落盘
└── samples/           # generate_sample_data.py 输出
```

## 禁止

- 把真实用户隐私数据提交到 Git
- 在文档中依赖本目录的固定绝对路径（应用 `config.settings`）
- 手改 DB 当「正式迁移」而不改 `storage/db.py` 建表逻辑
