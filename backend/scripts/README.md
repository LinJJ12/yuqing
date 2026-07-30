# `backend/scripts/` — 运维与验证脚本

上级规范：[../README.md](../README.md)

## 职责

- 本地样例生成、冒烟回归等**命令行脚本**。
- 不被 `api` 在请求路径上 import。

## 文件

| 脚本 | 说明 |
|------|------|
| `generate_sample_data.py` | 写入 `backend/data/samples/campus_sample.json` |
| `smoke_test.py` | 规范化 / API / CUDA 等断言 |

## 用法

```powershell
# 在仓库根
uv run python backend/scripts/generate_sample_data.py
uv run python backend/scripts/smoke_test.py
```

## 禁止

- 作为 Web 运行时依赖（`api` 禁止 import 本目录）
- 写入密钥到脚本正文
- 修改 `vendor/` 参考仓内容
