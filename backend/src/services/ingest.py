"""文件导入：JSON / JSONL / CSV → SQLite。"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from src.config.settings import settings
from src.storage.db import get_store
from src.services.normalize import normalize_post


def load_records(path: Path) -> list[dict]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))
    if suffix in {".jsonl", ".ndjson"}:
        records = []
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    records.append(json.loads(line))
        return records
    if suffix == ".json":
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for key in ("posts", "data", "items", "records"):
                if isinstance(data.get(key), list):
                    return data[key]
            return [data]
        raise ValueError("JSON 根节点必须是数组或含 posts/data 的对象")
    raise ValueError("仅支持 JSON、JSONL、CSV")


def import_file(
    path: Path,
    *,
    filename: str,
    topic: str | None = None,
    platform: str | None = None,
) -> dict:
    store = get_store()
    platform = platform or settings.default_platform
    topic = (topic or "").strip()[:100] or "文件导入"
    job = store.create_import_job(filename=filename, topic=topic, platform=platform)

    try:
        raw_records = load_records(path)
    except Exception as exc:
        return store.finish_import_job(
            job["id"],
            status="failed",
            error_message=f"解析失败: {exc}",
        )

    accepted: list[dict] = []
    rejected = 0
    errors: list[str] = []
    for idx, record in enumerate(raw_records):
        if not isinstance(record, dict):
            rejected += 1
            continue
        try:
            accepted.append(
                normalize_post(record, platform=platform, topic=topic if topic != "文件导入" else None)
            )
        except ValueError as exc:
            rejected += 1
            if len(errors) < 5:
                errors.append(f"第{idx + 1}条: {exc}")

    inserted = store.insert_posts(job["id"], accepted)
    stats = {
        "total": len(raw_records),
        "accepted": len(accepted),
        "inserted": inserted,
        "duplicates": max(len(accepted) - inserted, 0),
        "rejected": rejected,
        "errors": errors,
    }
    return store.finish_import_job(job["id"], status="succeeded", stats=stats)
