# Database Guidelines

> SQLite persistence for 知微 (no ORM in production path).

---

## Overview

- Engine: **sqlite3** via `src.storage.db.Store`
- Path: `settings.db_path` under `backend/data/`
- Access: **only** through `get_store()` / `Store` methods — routers and services must not open their own connections for product data
- JSON columns: `engagement_json`, `raw_json`, `stats_json`, … serialized with compact `json.dumps(..., ensure_ascii=False)`

There is **no Alembic migration flow in daily use**. Schema evolves with `CREATE TABLE IF NOT EXISTS` plus `_ensure_schema()` column patches (e.g. `sentiment_confidence`).

---

## Query Patterns

- One connection per `Store.connect()` context manager; commit on success, rollback on error; `PRAGMA foreign_keys=ON`, busy timeout set
- Inserts use `INSERT OR IGNORE` for posts (dedupe on `platform + source_id`)
- Filters for lists: optional `topic`, `platform`, `label`, `bvid` (`json_extract(raw_json, '$.extra.bvid')`), keyword `q` (LIKE with escaped `%`/`_`)
- Default list order: `COALESCE(fetched_at, published_at) DESC` so fake sample `published_at` does not bury fresh crawls
- Bilibili video aggregates: `list_bilibili_videos` / `list_posts_by_bvid` read `raw.extra.bvid`

When creating a post with `sentiment_label`, also set integer `sentiment` (`positive=1`, `neutral=0`, `negative=-1`, `uncertain=0`) and `sentiment_method='manual'`. Invalid labels raise `ValueError`.

---

## Migrations

1. Prefer additive columns in `_ensure_schema`
2. Do not drop/rename casually on developer DBs
3. Runtime DB files under `backend/data/*` are gitignored; ship fixtures under `backend/data/samples/`

---

## Naming Conventions

- Tables: plural snake_case (`posts`, `import_jobs`, `analysis_jobs`, `app_settings`)
- Timestamps: ISO-8601 UTC strings from `utc_now()`
- Soft settings: `app_settings.key` + `value_json`

---

## Common Mistakes

- Filtering Bilibili rows by `topic` alone instead of `raw.extra.bvid`
- Using `published_at` alone for “what came in today”
- Leaving `sentiment` NULL when writing a manual/LLM label
- Passing user search text into LIKE without escaping `%` / `_`
- Calling `sqlite3.connect` from a service instead of `Store`
