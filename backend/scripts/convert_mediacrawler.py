"""将 MediaCrawler 导出转为 Yuqing 可导入 JSON。

支持平台（MVP）: xhs / dy / wb

常见字段映射（内容帖）:
  note_id|aweme_id|mid → id
  title + desc|note_desc|aweme_desc → text
  nickname → author
  create_time → published_at
  liked_count / comment_count / share_count → engagement
  note_url|aweme_url|share_url → source_url

用法（仓库根）:
  uv run python backend/scripts/convert_mediacrawler.py path/to/export --platform xhs
  uv run python backend/scripts/convert_mediacrawler.py path/to/dir --platform dy --include-comments

输出默认: backend/data/imports/converted_<platform>_<timestamp>.json
再用监测页上传，或:
  选择平台后上传该 JSON。
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from src.config.settings import DATA_DIR  # noqa: E402
from src.services.normalize import normalize_platform, normalize_post  # noqa: E402

# MediaCrawler 目录名 → 平台码
DIR_TO_PLATFORM = {
    "xhs": "xhs",
    "xiaohongshu": "xhs",
    "douyin": "dy",
    "dy": "dy",
    "weibo": "wb",
    "wb": "wb",
    "bilibili": "bili",
    "bili": "bili",
}

CONTENT_HINTS = (
    "note_id",
    "aweme_id",
    "video_id",
    "mid",
    "desc",
    "note_desc",
    "aweme_desc",
    "title",
)
COMMENT_HINTS = ("comment_id", "comment_text", "parent_comment_id")


def _load_file(path: Path) -> list[dict]:
    suffix = path.suffix.lower()
    if suffix in {".jsonl", ".ndjson"}:
        rows = []
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(json.loads(line))
        return rows
    if suffix == ".json":
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for key in ("posts", "data", "items", "records", "contents", "notes"):
                if isinstance(data.get(key), list):
                    return data[key]
            return [data]
    return []


def _iter_source_files(root: Path) -> list[Path]:
    if root.is_file():
        return [root]
    files: list[Path] = []
    for pattern in ("**/*.json", "**/*.jsonl", "**/*.ndjson"):
        files.extend(root.glob(pattern))
    # 跳过词云等非内容文件
    skip = {"wordcloud", "words", "word_cloud"}
    return [
        p
        for p in sorted(files)
        if p.is_file() and not any(s in p.parts for s in skip)
    ]


def _looks_like_comment(rec: dict) -> bool:
    if any(k in rec for k in COMMENT_HINTS) and not any(
        k in rec for k in ("note_id", "aweme_id", "mid", "video_id")
    ):
        return True
    # 评论常有 content + comment_id
    if "comment_id" in rec:
        return True
    return False


def _looks_like_content(rec: dict) -> bool:
    return any(k in rec for k in CONTENT_HINTS) or bool(
        rec.get("desc") or rec.get("title") or rec.get("content")
    )


def _flatten_comment(rec: dict, platform: str) -> dict:
    parent = (
        rec.get("note_id")
        or rec.get("aweme_id")
        or rec.get("video_id")
        or rec.get("mid")
        or "unknown"
    )
    cid = rec.get("comment_id") or rec.get("id") or "c"
    text = (
        rec.get("content")
        or rec.get("comment_text")
        or rec.get("content_clean")
        or rec.get("text")
        or ""
    )
    return {
        **rec,
        "id": f"cmt-{parent}-{cid}",
        "text": str(text),
        "platform": platform,
        "topic": rec.get("topic") or f"评论/{parent}",
        "source_keyword": rec.get("source_keyword") or "评论",
    }


def convert_records(
    records: list[dict],
    *,
    platform: str,
    include_comments: bool,
) -> tuple[list[dict], dict]:
    platform = normalize_platform(platform)
    out: list[dict] = []
    stats = {
        "input": len(records),
        "content": 0,
        "comments": 0,
        "skipped": 0,
        "normalize_ok": 0,
        "normalize_fail": 0,
    }
    for rec in records:
        if not isinstance(rec, dict):
            stats["skipped"] += 1
            continue
        is_comment = _looks_like_comment(rec)
        if is_comment:
            if not include_comments:
                stats["skipped"] += 1
                continue
            row = _flatten_comment(rec, platform)
            stats["comments"] += 1
        elif _looks_like_content(rec):
            row = {**rec, "platform": platform}
            stats["content"] += 1
        else:
            # 尽量当内容帖试一次
            row = {**rec, "platform": platform}
            stats["content"] += 1
        try:
            normalized = normalize_post(row, platform=platform)
            # 导出为导入友好扁平结构（保留 raw 以外关键字段）
            out.append(
                {
                    "id": normalized["source_id"],
                    "platform": normalized["platform"],
                    "text": normalized["text"],
                    "author": normalized["author"],
                    "published_at": normalized["published_at"],
                    "topic": normalized["topic"],
                    "source_url": normalized["source_url"],
                    "likes": normalized["engagement"].get("likes", 0),
                    "comments": normalized["engagement"].get("comments", 0),
                    "reposts": normalized["engagement"].get("reposts", 0),
                }
            )
            stats["normalize_ok"] += 1
        except ValueError:
            stats["normalize_fail"] += 1
    return out, stats


def main() -> None:
    parser = argparse.ArgumentParser(description="MediaCrawler 导出 → Yuqing 导入 JSON")
    parser.add_argument("source", type=str, help="导出文件或目录（含 json/jsonl）")
    parser.add_argument(
        "--platform",
        type=str,
        default="",
        help="平台码 xhs|dy|wb|bili（可从目录名推断）",
    )
    parser.add_argument(
        "--include-comments",
        action="store_true",
        help="将评论展平为独立帖（默认忽略评论）",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="",
        help="输出 JSON 路径（默认 backend/data/imports/converted_*.json）",
    )
    args = parser.parse_args()

    source = Path(args.source).expanduser().resolve()
    if not source.exists():
        print(f"ERROR: 路径不存在: {source}")
        sys.exit(1)

    platform = args.platform.strip().lower()
    if not platform:
        for part in source.parts:
            key = part.lower()
            if key in DIR_TO_PLATFORM:
                platform = DIR_TO_PLATFORM[key]
                break
    if not platform:
        platform = "xhs"
        print(f"WARN: 未能推断平台，默认使用 {platform}")

    files = _iter_source_files(source)
    if not files:
        print("ERROR: 未找到 json/jsonl 文件")
        sys.exit(1)

    all_records: list[dict] = []
    for path in files:
        try:
            all_records.extend(_load_file(path))
        except Exception as exc:
            print(f"WARN: 跳过 {path.name}: {exc}")

    posts, stats = convert_records(
        all_records,
        platform=platform,
        include_comments=args.include_comments,
    )

    out_dir = DATA_DIR / "imports"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = (
        Path(args.output).expanduser().resolve()
        if args.output
        else out_dir / f"converted_{normalize_platform(platform)}_{stamp}.json"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as handle:
        json.dump(posts, handle, ensure_ascii=False, indent=2)

    print(f"platform={normalize_platform(platform)}")
    print(f"files={len(files)} stats={stats}")
    print(f"wrote {len(posts)} posts → {out_path}")
    print("下一步：监测页选择对应平台后上传该 JSON，再跑情感/预警。")


if __name__ == "__main__":
    main()
