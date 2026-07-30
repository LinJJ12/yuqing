"""SQLite 持久化（一期：帖子 + 导入/分析任务 + 设置）。"""

from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config.settings import settings


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _load(value: Any, default: Any) -> Any:
    if value in (None, ""):
        return default
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return default


class Store:
    def __init__(self, path: str | None = None) -> None:
        self.path = str(Path(path or settings.db_path).resolve())

    @contextmanager
    def connect(self):
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 10000")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def initialize(self) -> None:
        with self.connect() as conn:
            conn.execute("PRAGMA journal_mode = WAL")
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS import_jobs (
                    id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    status TEXT NOT NULL,
                    stats_json TEXT NOT NULL DEFAULT '{}',
                    error_message TEXT,
                    created_at TEXT NOT NULL,
                    finished_at TEXT
                );

                CREATE TABLE IF NOT EXISTS posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    platform TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    author TEXT NOT NULL DEFAULT '',
                    text TEXT NOT NULL,
                    published_at TEXT,
                    engagement_json TEXT NOT NULL DEFAULT '{}',
                    fetched_at TEXT NOT NULL,
                    import_job_id TEXT,
                    source_url TEXT,
                    topic TEXT,
                    sentiment INTEGER,
                    sentiment_label TEXT,
                    sentiment_method TEXT,
                    raw_json TEXT NOT NULL DEFAULT '{}',
                    UNIQUE(platform, source_id)
                );
                CREATE INDEX IF NOT EXISTS idx_posts_published
                    ON posts(published_at DESC);
                CREATE INDEX IF NOT EXISTS idx_posts_topic
                    ON posts(topic);

                CREATE TABLE IF NOT EXISTS analysis_jobs (
                    id TEXT PRIMARY KEY,
                    kind TEXT NOT NULL,
                    status TEXT NOT NULL,
                    params_json TEXT NOT NULL DEFAULT '{}',
                    result_json TEXT NOT NULL DEFAULT '{}',
                    error_message TEXT,
                    created_at TEXT NOT NULL,
                    finished_at TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_analysis_jobs_created
                    ON analysis_jobs(created_at DESC);

                CREATE TABLE IF NOT EXISTS app_settings (
                    key TEXT PRIMARY KEY,
                    value_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )

    def create_import_job(self, filename: str, topic: str, platform: str) -> dict:
        job_id = uuid.uuid4().hex
        now = utc_now()
        with self.connect() as conn:
            conn.execute(
                """INSERT INTO import_jobs(
                    id, filename, topic, platform, status, stats_json, created_at
                ) VALUES (?, ?, ?, ?, 'running', '{}', ?)""",
                (job_id, filename, topic, platform, now),
            )
        return self.get_import_job(job_id)

    def finish_import_job(
        self,
        job_id: str,
        *,
        status: str,
        stats: dict | None = None,
        error_message: str | None = None,
    ) -> dict:
        with self.connect() as conn:
            conn.execute(
                """UPDATE import_jobs
                   SET status = ?, stats_json = ?, error_message = ?, finished_at = ?
                   WHERE id = ?""",
                (status, _dump(stats or {}), error_message, utc_now(), job_id),
            )
        return self.get_import_job(job_id)

    def get_import_job(self, job_id: str) -> dict | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM import_jobs WHERE id = ?", (job_id,)
            ).fetchone()
        if row is None:
            return None
        data = dict(row)
        data["stats"] = _load(data.pop("stats_json"), {})
        return data

    def list_import_jobs(self, limit: int = 50) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM import_jobs ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        result = []
        for row in rows:
            data = dict(row)
            data["stats"] = _load(data.pop("stats_json"), {})
            result.append(data)
        return result

    def insert_posts(self, job_id: str | None, posts: list[dict]) -> int:
        inserted = 0
        with self.connect() as conn:
            for post in posts:
                cursor = conn.execute(
                    """INSERT OR IGNORE INTO posts(
                        platform, source_id, author, text, published_at,
                        engagement_json, fetched_at, import_job_id, source_url,
                        topic, sentiment, sentiment_label, sentiment_method, raw_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        post["platform"],
                        post["source_id"],
                        post.get("author", ""),
                        post["text"],
                        post.get("published_at"),
                        _dump(post.get("engagement", {})),
                        post.get("fetched_at") or utc_now(),
                        job_id,
                        post.get("source_url"),
                        post.get("topic"),
                        post.get("sentiment"),
                        post.get("sentiment_label"),
                        post.get("sentiment_method"),
                        _dump(post.get("raw", {})),
                    ),
                )
                inserted += max(cursor.rowcount, 0)
        return inserted

    def count_posts(self) -> int:
        with self.connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS c FROM posts").fetchone()
        return int(row["c"])

    def list_posts(
        self,
        *,
        topic: str | None = None,
        limit: int = 100,
        offset: int = 0,
        method: str | None = None,
        only_pending_bert: bool = False,
    ) -> list[dict]:
        clauses: list[str] = []
        values: list[Any] = []
        if topic and topic != "all":
            clauses.append("topic = ?")
            values.append(topic)
        if method:
            clauses.append("sentiment_method = ?")
            values.append(method)
        if only_pending_bert:
            clauses.append(
                "(sentiment_method IS NULL OR sentiment_method != 'bert')"
            )
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        values.extend([limit, offset])
        with self.connect() as conn:
            rows = conn.execute(
                f"""SELECT * FROM posts {where}
                    ORDER BY COALESCE(published_at, fetched_at) DESC
                    LIMIT ? OFFSET ?""",
                values,
            ).fetchall()
        return [self._post_row(row) for row in rows]

    def list_post_texts(self, limit: int = 5000) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute(
                """SELECT id, text, topic, sentiment_label, sentiment_method
                   FROM posts
                   ORDER BY id ASC
                   LIMIT ?""",
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def update_post_sentiment(
        self,
        post_id: int,
        *,
        sentiment: int,
        sentiment_label: str,
        sentiment_method: str,
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """UPDATE posts
                   SET sentiment = ?, sentiment_label = ?, sentiment_method = ?
                   WHERE id = ?""",
                (sentiment, sentiment_label, sentiment_method, post_id),
            )

    def update_post_sentiments(self, updates: list[dict]) -> int:
        if not updates:
            return 0
        with self.connect() as conn:
            conn.executemany(
                """UPDATE posts
                   SET sentiment = ?, sentiment_label = ?, sentiment_method = ?
                   WHERE id = ?""",
                [
                    (
                        u["sentiment"],
                        u["sentiment_label"],
                        u["sentiment_method"],
                        u["id"],
                    )
                    for u in updates
                ],
            )
        return len(updates)

    def sentiment_stats(self) -> dict:
        with self.connect() as conn:
            by_label = conn.execute(
                """SELECT COALESCE(sentiment_label, 'unknown') AS label,
                          COALESCE(sentiment_method, 'none') AS method,
                          COUNT(*) AS c
                   FROM posts
                   GROUP BY label, method"""
            ).fetchall()
            total = conn.execute("SELECT COUNT(*) AS c FROM posts").fetchone()["c"]
            bert_done = conn.execute(
                "SELECT COUNT(*) AS c FROM posts WHERE sentiment_method = 'bert'"
            ).fetchone()["c"]
        return {
            "total": int(total),
            "bert_done": int(bert_done),
            "pending": max(int(total) - int(bert_done), 0),
            "breakdown": [
                {
                    "label": r["label"],
                    "method": r["method"],
                    "count": int(r["c"]),
                }
                for r in by_label
            ],
        }

    def create_analysis_job(self, kind: str, params: dict | None = None) -> dict:
        job_id = uuid.uuid4().hex
        now = utc_now()
        with self.connect() as conn:
            conn.execute(
                """INSERT INTO analysis_jobs(
                    id, kind, status, params_json, result_json, created_at
                ) VALUES (?, ?, 'queued', ?, '{}', ?)""",
                (job_id, kind, _dump(params or {}), now),
            )
        return self.get_analysis_job(job_id)  # type: ignore[return-value]

    def update_analysis_job(
        self,
        job_id: str,
        *,
        status: str,
        result: dict | None = None,
        error_message: str | None = None,
    ) -> dict | None:
        finished = utc_now() if status in {"succeeded", "failed"} else None
        with self.connect() as conn:
            if result is not None:
                conn.execute(
                    """UPDATE analysis_jobs
                       SET status = ?, result_json = ?, error_message = ?,
                           finished_at = COALESCE(?, finished_at)
                       WHERE id = ?""",
                    (status, _dump(result), error_message, finished, job_id),
                )
            else:
                conn.execute(
                    """UPDATE analysis_jobs
                       SET status = ?, error_message = ?,
                           finished_at = COALESCE(?, finished_at)
                       WHERE id = ?""",
                    (status, error_message, finished, job_id),
                )
        return self.get_analysis_job(job_id)

    def get_analysis_job(self, job_id: str) -> dict | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM analysis_jobs WHERE id = ?", (job_id,)
            ).fetchone()
        if row is None:
            return None
        data = dict(row)
        data["params"] = _load(data.pop("params_json"), {})
        data["result"] = _load(data.pop("result_json"), {})
        return data

    def list_analysis_jobs(self, limit: int = 20) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM analysis_jobs ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        result = []
        for row in rows:
            data = dict(row)
            data["params"] = _load(data.pop("params_json"), {})
            data["result"] = _load(data.pop("result_json"), {})
            result.append(data)
        return result

    def get_setting(self, key: str, default: Any = None) -> Any:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT value_json FROM app_settings WHERE key = ?", (key,)
            ).fetchone()
        if row is None:
            return default
        return _load(row["value_json"], default)

    def set_setting(self, key: str, value: Any) -> Any:
        with self.connect() as conn:
            conn.execute(
                """INSERT INTO app_settings(key, value_json, updated_at)
                   VALUES (?, ?, ?)
                   ON CONFLICT(key) DO UPDATE SET
                     value_json = excluded.value_json,
                     updated_at = excluded.updated_at""",
                (key, _dump(value), utc_now()),
            )
        return value

    def overview(self) -> dict:
        with self.connect() as conn:
            total = conn.execute("SELECT COUNT(*) AS c FROM posts").fetchone()["c"]
            by_topic = conn.execute(
                """SELECT COALESCE(topic, '未分类') AS topic, COUNT(*) AS c
                   FROM posts GROUP BY COALESCE(topic, '未分类')
                   ORDER BY c DESC LIMIT 12"""
            ).fetchall()
            by_sentiment = conn.execute(
                """SELECT COALESCE(sentiment_label, 'unknown') AS label, COUNT(*) AS c
                   FROM posts GROUP BY COALESCE(sentiment_label, 'unknown')"""
            ).fetchall()
            by_day = conn.execute(
                """SELECT substr(COALESCE(published_at, fetched_at), 1, 10) AS day,
                          COUNT(*) AS c
                   FROM posts
                   WHERE COALESCE(published_at, fetched_at) IS NOT NULL
                   GROUP BY day
                   ORDER BY day DESC
                   LIMIT 14"""
            ).fetchall()
            recent = conn.execute(
                """SELECT * FROM posts
                   ORDER BY COALESCE(published_at, fetched_at) DESC
                   LIMIT 8"""
            ).fetchall()
        return {
            "total_posts": int(total),
            "by_topic": [{"topic": r["topic"], "count": int(r["c"])} for r in by_topic],
            "by_sentiment": [
                {"label": r["label"], "count": int(r["c"])} for r in by_sentiment
            ],
            "by_day": [
                {"day": r["day"], "count": int(r["c"])} for r in reversed(list(by_day))
            ],
            "recent_posts": [self._post_row(r) for r in recent],
        }

    @staticmethod
    def _post_row(row: sqlite3.Row) -> dict:
        data = dict(row)
        data["engagement"] = _load(data.pop("engagement_json"), {})
        data["raw"] = _load(data.pop("raw_json"), {})
        return data


_store: Store | None = None


def get_store() -> Store:
    global _store
    if _store is None:
        _store = Store()
        _store.initialize()
    return _store
