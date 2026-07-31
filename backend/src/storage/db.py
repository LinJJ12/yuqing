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
                    sentiment_confidence REAL,
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
            self._ensure_schema(conn)

    @staticmethod
    def _ensure_schema(conn: sqlite3.Connection) -> None:
        """增量列迁移（已有库不会重建表）。"""
        cols = {row[1] for row in conn.execute("PRAGMA table_info(posts)").fetchall()}
        if "sentiment_confidence" not in cols:
            conn.execute("ALTER TABLE posts ADD COLUMN sentiment_confidence REAL")

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
                        topic, sentiment, sentiment_label, sentiment_method,
                        sentiment_confidence, raw_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
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
                        post.get("sentiment_confidence"),
                        _dump(post.get("raw", {})),
                    ),
                )
                inserted += max(cursor.rowcount, 0)
        return inserted

    @staticmethod
    def _append_bvid_clause(
        clauses: list[str], values: list[Any], bvid: str | None
    ) -> None:
        key = (bvid or "").strip()
        if not key:
            return
        clauses.append("json_extract(raw_json, '$.extra.bvid') = ?")
        values.append(key)

    def count_posts(
        self,
        *,
        topic: str | None = None,
        platform: str | None = None,
        label: str | None = None,
        bvid: str | None = None,
        q: str | None = None,
    ) -> int:
        clauses: list[str] = []
        values: list[Any] = []
        if topic and topic != "all":
            clauses.append("topic = ?")
            values.append(topic)
        if platform and platform != "all":
            clauses.append("platform = ?")
            values.append(platform)
        if label:
            clauses.append("sentiment_label = ?")
            values.append(label)
        self._append_bvid_clause(clauses, values, bvid)
        self._append_search_clause(clauses, values, q)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self.connect() as conn:
            row = conn.execute(
                f"SELECT COUNT(*) AS c FROM posts {where}",
                values,
            ).fetchone()
        return int(row["c"])

    @staticmethod
    def _append_search_clause(
        clauses: list[str], values: list[Any], q: str | None
    ) -> None:
        key = (q or "").strip()
        if not key:
            return
        # 用户输入按字面匹配，避免 % / _ 被当成 LIKE 通配符
        escaped = key.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        like = f"%{escaped}%"
        clauses.append(
            "(text LIKE ? ESCAPE '\\' OR IFNULL(topic, '') LIKE ? ESCAPE '\\' "
            "OR IFNULL(author, '') LIKE ? ESCAPE '\\' "
            "OR IFNULL(source_url, '') LIKE ? ESCAPE '\\')"
        )
        values.extend([like, like, like, like])

    def list_posts(
        self,
        *,
        topic: str | None = None,
        platform: str | None = None,
        limit: int = 100,
        offset: int = 0,
        method: str | None = None,
        only_pending_bert: bool = False,
        exclude_protected: bool = False,
        label: str | None = None,
        order: str = "fetched",
        bvid: str | None = None,
        q: str | None = None,
    ) -> list[dict]:
        clauses: list[str] = []
        values: list[Any] = []
        if topic and topic != "all":
            clauses.append("topic = ?")
            values.append(topic)
        if platform and platform != "all":
            clauses.append("platform = ?")
            values.append(platform)
        if method:
            clauses.append("sentiment_method = ?")
            values.append(method)
        if only_pending_bert:
            # 人工/LLM 改判视为已完成，不进待处理；也不被模型覆盖
            clauses.append(
                "(sentiment_method IS NULL OR sentiment_method NOT IN ('bert', 'manual', 'llm'))"
            )
        if exclude_protected:
            clauses.append(
                "(sentiment_method IS NULL OR sentiment_method NOT IN ('manual', 'llm'))"
            )
        if label:
            clauses.append("sentiment_label = ?")
            values.append(label)
        self._append_bvid_clause(clauses, values, bvid)
        self._append_search_clause(clauses, values, q)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        # 默认按入库时间，避免样例假发布时间压过真实采集
        if order == "published":
            order_sql = "COALESCE(published_at, fetched_at) DESC, id DESC"
        elif order == "confidence_asc":
            order_sql = (
                "CASE WHEN sentiment_confidence IS NULL THEN 1 ELSE 0 END, "
                "sentiment_confidence ASC, id DESC"
            )
        else:
            order_sql = "COALESCE(fetched_at, published_at) DESC, id DESC"
        values.extend([limit, offset])
        with self.connect() as conn:
            rows = conn.execute(
                f"""SELECT * FROM posts {where}
                    ORDER BY {order_sql}
                    LIMIT ? OFFSET ?""",
                values,
            ).fetchall()
        return [self._post_row(row) for row in rows]

    def get_post(self, post_id: int) -> dict | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM posts WHERE id = ?", (post_id,)
            ).fetchone()
        return self._post_row(row) if row else None

    def create_post(
        self,
        *,
        text: str,
        platform: str = "campus",
        topic: str | None = None,
        author: str = "",
        source_url: str | None = None,
        source_id: str | None = None,
        bvid: str | None = None,
        video_title: str | None = None,
        sentiment_label: str | None = None,
    ) -> dict:
        body = (text or "").strip()
        if not body:
            raise ValueError("正文不能为空")
        plat = (platform or "campus").strip() or "campus"
        sid = (source_id or "").strip() or f"manual-{uuid.uuid4().hex[:12]}"
        raw: dict[str, Any] = {"extra": {}}
        if (bvid or "").strip():
            raw["extra"]["bvid"] = bvid.strip()
        if (video_title or "").strip():
            raw["extra"]["video_title"] = video_title.strip()
        label = (sentiment_label or "").strip().lower() or None
        allowed = {"positive", "neutral", "negative", "uncertain"}
        if label and label not in allowed:
            raise ValueError("sentiment_label 必须是 positive / neutral / negative / uncertain")
        score_map = {"positive": 1, "neutral": 0, "negative": -1, "uncertain": 0}
        method = "manual" if label else None
        conf = 1.0 if label else None
        score = score_map[label] if label else None
        with self.connect() as conn:
            cur = conn.execute(
                """INSERT INTO posts(
                    platform, source_id, author, text, published_at,
                    engagement_json, fetched_at, import_job_id, source_url,
                    topic, sentiment, sentiment_label, sentiment_method,
                    sentiment_confidence, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    plat,
                    sid,
                    (author or "").strip(),
                    body,
                    None,
                    _dump({}),
                    utc_now(),
                    None,
                    (source_url or "").strip() or None,
                    (topic or "").strip() or None,
                    score,
                    label,
                    method,
                    conf,
                    _dump(raw),
                ),
            )
            post_id = int(cur.lastrowid)
        post = self.get_post(post_id)
        if not post:
            raise RuntimeError("创建后读取失败")
        return post

    def update_post(
        self,
        post_id: int,
        *,
        text: str | None = None,
        platform: str | None = None,
        topic: str | None = None,
        author: str | None = None,
        source_url: str | None = None,
        bvid: str | None = None,
        video_title: str | None = None,
        clear_topic: bool = False,
        clear_source_url: bool = False,
    ) -> dict | None:
        existing = self.get_post(post_id)
        if not existing:
            return None
        fields: list[str] = []
        values: list[Any] = []
        if text is not None:
            body = text.strip()
            if not body:
                raise ValueError("正文不能为空")
            fields.append("text = ?")
            values.append(body)
        if platform is not None:
            plat = platform.strip() or existing["platform"]
            fields.append("platform = ?")
            values.append(plat)
        if topic is not None or clear_topic:
            fields.append("topic = ?")
            values.append(None if clear_topic else ((topic or "").strip() or None))
        if author is not None:
            fields.append("author = ?")
            values.append(author.strip())
        if source_url is not None or clear_source_url:
            fields.append("source_url = ?")
            values.append(
                None if clear_source_url else ((source_url or "").strip() or None)
            )

        raw = dict(existing.get("raw") or {})
        extra = dict(raw.get("extra") or {})
        raw_changed = False
        if bvid is not None:
            key = bvid.strip()
            if key:
                extra["bvid"] = key
            else:
                extra.pop("bvid", None)
            raw_changed = True
        if video_title is not None:
            title = video_title.strip()
            if title:
                extra["video_title"] = title
            else:
                extra.pop("video_title", None)
            raw_changed = True
        if raw_changed:
            raw["extra"] = extra
            fields.append("raw_json = ?")
            values.append(_dump(raw))

        if not fields:
            return existing
        values.append(post_id)
        with self.connect() as conn:
            conn.execute(
                f"UPDATE posts SET {', '.join(fields)} WHERE id = ?",
                values,
            )
        return self.get_post(post_id)

    def delete_post(self, post_id: int) -> bool:
        with self.connect() as conn:
            cur = conn.execute("DELETE FROM posts WHERE id = ?", (post_id,))
            return cur.rowcount > 0

    def delete_posts_by_ids(self, ids: list[int]) -> dict:
        clean = sorted({int(i) for i in ids if int(i) > 0})
        if not clean:
            raise ValueError("请提供要删除的帖子 id")
        placeholders = ",".join("?" for _ in clean)
        with self.connect() as conn:
            matched = conn.execute(
                f"SELECT COUNT(*) AS c FROM posts WHERE id IN ({placeholders})",
                clean,
            ).fetchone()
            count = int(matched["c"] or 0)
            if count == 0:
                return {"deleted": 0, "matched": 0, "ids": clean}
            conn.execute(
                f"DELETE FROM posts WHERE id IN ({placeholders})",
                clean,
            )
        return {"deleted": count, "matched": count, "ids": clean}

    def list_review_posts(self, *, limit: int = 40, bvid: str | None = None) -> list[dict]:
        """难例优先：uncertain → 低置信 BERT → 最近帖。"""
        clauses: list[str] = []
        values: list[Any] = []
        self._append_bvid_clause(clauses, values, bvid)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        values.append(limit)
        with self.connect() as conn:
            rows = conn.execute(
                f"""
                SELECT * FROM posts
                {where}
                ORDER BY
                  CASE
                    WHEN sentiment_label = 'uncertain' THEN 0
                    WHEN sentiment_method = 'bert'
                         AND sentiment_confidence IS NOT NULL
                         AND sentiment_confidence < 0.65 THEN 1
                    ELSE 2
                  END,
                  CASE WHEN sentiment_confidence IS NULL THEN 1 ELSE 0 END,
                  sentiment_confidence ASC,
                  COALESCE(fetched_at, published_at) DESC,
                  id DESC
                LIMIT ?
                """,
                values,
            ).fetchall()
        return [self._post_row(row) for row in rows]

    def list_post_texts(
        self, limit: int = 5000, *, bvid: str | None = None
    ) -> list[dict]:
        clauses: list[str] = []
        values: list[Any] = []
        self._append_bvid_clause(clauses, values, bvid)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        values.append(limit)
        with self.connect() as conn:
            rows = conn.execute(
                f"""SELECT id, text, topic, sentiment_label, sentiment_method
                   FROM posts
                   {where}
                   ORDER BY id ASC
                   LIMIT ?""",
                values,
            ).fetchall()
        return [dict(row) for row in rows]

    def update_post_sentiment(
        self,
        post_id: int,
        *,
        sentiment: int,
        sentiment_label: str,
        sentiment_method: str,
        sentiment_confidence: float | None = None,
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """UPDATE posts
                   SET sentiment = ?, sentiment_label = ?, sentiment_method = ?,
                       sentiment_confidence = ?
                   WHERE id = ?""",
                (
                    sentiment,
                    sentiment_label,
                    sentiment_method,
                    sentiment_confidence,
                    post_id,
                ),
            )

    def update_post_sentiments(self, updates: list[dict]) -> int:
        if not updates:
            return 0
        with self.connect() as conn:
            conn.executemany(
                """UPDATE posts
                   SET sentiment = ?, sentiment_label = ?, sentiment_method = ?,
                       sentiment_confidence = ?
                   WHERE id = ?""",
                [
                    (
                        u["sentiment"],
                        u["sentiment_label"],
                        u["sentiment_method"],
                        u.get("sentiment_confidence"),
                        u["id"],
                    )
                    for u in updates
                ],
            )
        return len(updates)

    def sentiment_stats(self, *, bvid: str | None = None) -> dict:
        from src.services.sentiment import sentiment_model_status

        clauses: list[str] = []
        values: list[Any] = []
        self._append_bvid_clause(clauses, values, bvid)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        and_prefix = f"{where} AND" if where else "WHERE"

        with self.connect() as conn:
            by_label = conn.execute(
                f"""SELECT COALESCE(sentiment_label, 'unknown') AS label,
                          COALESCE(sentiment_method, 'none') AS method,
                          COUNT(*) AS c
                   FROM posts
                   {where}
                   GROUP BY label, method""",
                values,
            ).fetchall()
            total = conn.execute(
                f"SELECT COUNT(*) AS c FROM posts {where}", values
            ).fetchone()["c"]
            bert_done = conn.execute(
                f"SELECT COUNT(*) AS c FROM posts {and_prefix} sentiment_method = 'bert'",
                values,
            ).fetchone()["c"]
            uncertain = conn.execute(
                f"SELECT COUNT(*) AS c FROM posts {and_prefix} sentiment_label = 'uncertain'",
                values,
            ).fetchone()["c"]
            protected = conn.execute(
                f"""SELECT COUNT(*) AS c FROM posts
                   {and_prefix} sentiment_method IN ('manual', 'llm')""",
                values,
            ).fetchone()["c"]
        model = sentiment_model_status(self)
        stale = bool(model.get("model_stale"))
        total_i = int(total)
        bert_i = int(bert_done)
        protected_i = int(protected)
        # 人工/LLM 改判不进待处理，也不会被 BERT 覆盖
        updatable = max(total_i - protected_i, 0)
        pending = updatable if stale else max(updatable - bert_i, 0)
        return {
            "total": total_i,
            "bert_done": 0 if stale else bert_i,
            "bert_labeled": bert_i,
            "pending": pending,
            "protected": protected_i,
            "uncertain": int(uncertain),
            "model_stale": stale,
            "model_id": model.get("model_id"),
            "model_id_applied": model.get("model_id_applied"),
            "bvid": (bvid or "").strip() or None,
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
            by_platform = conn.execute(
                """SELECT COALESCE(platform, 'unknown') AS platform, COUNT(*) AS c
                   FROM posts GROUP BY COALESCE(platform, 'unknown')
                   ORDER BY c DESC"""
            ).fetchall()
            by_day = conn.execute(
                """SELECT substr(COALESCE(fetched_at, published_at), 1, 10) AS day,
                          COUNT(*) AS c
                   FROM posts
                   WHERE COALESCE(fetched_at, published_at) IS NOT NULL
                   GROUP BY day
                   ORDER BY day DESC
                   LIMIT 14"""
            ).fetchall()
            recent = conn.execute(
                """SELECT * FROM posts
                   ORDER BY COALESCE(fetched_at, published_at) DESC, id DESC
                   LIMIT 12"""
            ).fetchall()
        return {
            "total_posts": int(total),
            "by_topic": [{"topic": r["topic"], "count": int(r["c"])} for r in by_topic],
            "by_sentiment": [
                {"label": r["label"], "count": int(r["c"])} for r in by_sentiment
            ],
            "by_platform": [
                {"platform": r["platform"], "count": int(r["c"])} for r in by_platform
            ],
            "by_day": [
                {"day": r["day"], "count": int(r["c"])} for r in reversed(list(by_day))
            ],
            "recent_posts": [self._post_row(r) for r in recent],
        }

    def list_bilibili_videos(self, *, limit: int = 50) -> list[dict]:
        """按 raw.extra.bvid 聚合已入库的 B 站视频。"""
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT
                  json_extract(raw_json, '$.extra.bvid') AS bvid,
                  MAX(json_extract(raw_json, '$.extra.video_title')) AS video_title,
                  MAX(json_extract(raw_json, '$.extra.aid')) AS aid,
                  COUNT(*) AS comment_count,
                  SUM(CASE WHEN sentiment_label = 'positive' THEN 1 ELSE 0 END) AS positive,
                  SUM(CASE WHEN sentiment_label = 'neutral' THEN 1 ELSE 0 END) AS neutral,
                  SUM(CASE WHEN sentiment_label = 'negative' THEN 1 ELSE 0 END) AS negative,
                  MAX(COALESCE(fetched_at, published_at)) AS last_fetched_at
                FROM posts
                WHERE platform = 'bili'
                  AND json_extract(raw_json, '$.extra.bvid') IS NOT NULL
                  AND trim(json_extract(raw_json, '$.extra.bvid')) != ''
                GROUP BY json_extract(raw_json, '$.extra.bvid')
                ORDER BY MAX(COALESCE(fetched_at, published_at)) DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        result = []
        for row in rows:
            bvid = row["bvid"]
            result.append(
                {
                    "bvid": bvid,
                    "video_title": row["video_title"] or "",
                    "aid": row["aid"],
                    "comment_count": int(row["comment_count"] or 0),
                    "positive": int(row["positive"] or 0),
                    "neutral": int(row["neutral"] or 0),
                    "negative": int(row["negative"] or 0),
                    "last_fetched_at": row["last_fetched_at"],
                    "source_url": f"https://www.bilibili.com/video/{bvid}" if bvid else None,
                }
            )
        return result

    def list_posts_by_bvid(self, bvid: str, *, limit: int = 2000) -> list[dict]:
        key = (bvid or "").strip()
        if not key:
            return []
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM posts
                WHERE json_extract(raw_json, '$.extra.bvid') = ?
                ORDER BY COALESCE(fetched_at, published_at) DESC, id DESC
                LIMIT ?
                """,
                (key, limit),
            ).fetchall()
        return [self._post_row(row) for row in rows]

    def delete_posts(
        self,
        *,
        bvid: str | None = None,
        video_title_contains: str | None = None,
        topic: str | None = None,
        platform: str | None = None,
        ids: list[int] | None = None,
        dry_run: bool = False,
    ) -> dict:
        """按条件删除帖子。至少提供一个过滤条件。"""
        if ids:
            if dry_run:
                clean = sorted({int(i) for i in ids if int(i) > 0})
                with self.connect() as conn:
                    if not clean:
                        return {"deleted": 0, "matched": 0, "dry_run": True, "ids": []}
                    placeholders = ",".join("?" for _ in clean)
                    matched = conn.execute(
                        f"SELECT COUNT(*) AS c FROM posts WHERE id IN ({placeholders})",
                        clean,
                    ).fetchone()
                    return {
                        "deleted": 0,
                        "matched": int(matched["c"] or 0),
                        "dry_run": True,
                        "ids": clean,
                    }
            return {**self.delete_posts_by_ids(ids), "dry_run": False}
        clauses: list[str] = []
        values: list[Any] = []
        bvid_key = (bvid or "").strip()
        title_key = (video_title_contains or "").strip()
        topic_key = (topic or "").strip()
        platform_key = (platform or "").strip()
        if bvid_key:
            clauses.append("json_extract(raw_json, '$.extra.bvid') = ?")
            values.append(bvid_key)
        if title_key:
            clauses.append(
                "instr(COALESCE(json_extract(raw_json, '$.extra.video_title'), ''), ?) > 0"
            )
            values.append(title_key)
        if topic_key:
            clauses.append("topic = ?")
            values.append(topic_key)
        if platform_key:
            clauses.append("platform = ?")
            values.append(platform_key)
        if not clauses:
            raise ValueError("请至少指定 id、bvid、视频标题关键词、话题或平台之一")
        where = " AND ".join(clauses)
        with self.connect() as conn:
            matched = conn.execute(
                f"SELECT COUNT(*) AS c FROM posts WHERE {where}",
                values,
            ).fetchone()
            count = int(matched["c"] or 0)
            if dry_run or count == 0:
                return {"deleted": 0, "matched": count, "dry_run": dry_run}
            conn.execute(f"DELETE FROM posts WHERE {where}", values)
        return {"deleted": count, "matched": count, "dry_run": False}

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
