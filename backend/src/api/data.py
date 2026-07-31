"""导入与帖子、总览 API。"""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, Query, UploadFile
from pydantic import BaseModel, Field

from src.config.settings import settings
from src.lib.http import err, ok
from src.services.bilibili_collect import normalize_bvid, resolve_bvid
from src.services.ingest import import_file
from src.storage.db import get_store

router = APIRouter(tags=["data"])

ALLOWED = {".json", ".jsonl", ".ndjson", ".csv"}


class DeletePostsBody(BaseModel):
    ids: list[int] | None = Field(default=None, description="按帖子 id 批量删除")
    bvid: str | None = Field(default=None, max_length=200)
    title_contains: str | None = Field(default=None, max_length=200)
    topic: str | None = Field(default=None, max_length=100)
    platform: str | None = Field(default=None, max_length=40)
    dry_run: bool = False


class SentimentOverrideIn(BaseModel):
    label: str = Field(description="positive | neutral | negative | uncertain")
    method: str = Field(default="manual", description="manual | llm")
    confidence: float | None = Field(default=1.0, ge=0.0, le=1.0)


class PostCreateIn(BaseModel):
    text: str = Field(min_length=1, max_length=8000)
    platform: str = Field(default="campus", max_length=40)
    topic: str | None = Field(default=None, max_length=100)
    author: str = Field(default="", max_length=120)
    source_url: str | None = Field(default=None, max_length=500)
    bvid: str | None = Field(default=None, max_length=200)
    video_title: str | None = Field(default=None, max_length=300)
    sentiment_label: str | None = Field(
        default=None, description="可选：positive | neutral | negative | uncertain"
    )


class PostUpdateIn(BaseModel):
    text: str | None = Field(default=None, min_length=1, max_length=8000)
    platform: str | None = Field(default=None, max_length=40)
    topic: str | None = Field(default=None, max_length=100)
    author: str | None = Field(default=None, max_length=120)
    source_url: str | None = Field(default=None, max_length=500)
    bvid: str | None = Field(default=None, max_length=200)
    video_title: str | None = Field(default=None, max_length=300)
    clear_topic: bool = False
    clear_source_url: bool = False


@router.post("/imports")
async def create_import(
    file: UploadFile = File(...),
    topic: str = Form(default="文件导入"),
    platform: str = Form(default=""),
):
    if not file.filename:
        return err("missing_file", "请选择文件", status=400)
    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED:
        return err("unsupported_file", "仅支持 JSON、JSONL、CSV", status=400)

    import_dir = Path(settings.import_dir)
    import_dir.mkdir(parents=True, exist_ok=True)
    dest = import_dir / f"{uuid.uuid4().hex}{suffix}"

    size = 0
    try:
        with dest.open("wb") as handle:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > settings.max_upload_bytes:
                    dest.unlink(missing_ok=True)
                    return err("file_too_large", "文件超过 10MB 限制", status=413)
                handle.write(chunk)
    except Exception as exc:
        dest.unlink(missing_ok=True)
        return err("upload_failed", f"保存上传文件失败: {exc}", status=500)

    job = import_file(
        dest,
        filename=file.filename,
        topic=topic,
        platform=platform or settings.default_platform,
    )
    status = 200 if job.get("status") == "succeeded" else 500
    if job.get("status") == "failed":
        return err(
            "import_failed",
            job.get("error_message") or "导入失败",
            status=500,
            job=job,
        )
    return ok(job, status=status)


@router.get("/imports")
def list_imports(limit: int = Query(default=20, ge=1, le=100)):
    return ok(get_store().list_import_jobs(limit=limit))


@router.get("/imports/{job_id}")
def get_import(job_id: str):
    job = get_store().get_import_job(job_id)
    if not job:
        return err("not_found", "导入任务不存在", status=404)
    return ok(job)


@router.get("/posts")
def list_posts(
    topic: str | None = None,
    platform: str | None = None,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    order: str = Query(default="fetched", pattern="^(fetched|published)$"),
    label: str | None = Query(default=None),
    bvid: str | None = Query(default=None, max_length=200),
    q: str | None = Query(default=None, max_length=200, description="关键词搜索"),
):
    store = get_store()
    key = resolve_bvid(bvid)
    posts = store.list_posts(
        topic=topic,
        platform=platform,
        limit=limit,
        offset=offset,
        order=order,
        label=label,
        bvid=key,
        q=q,
    )
    total = store.count_posts(
        topic=topic, platform=platform, label=label, bvid=key, q=q
    )
    return ok(
        {
            "items": posts,
            "count": len(posts),
            "total": total,
            "platform": platform or "all",
            "order": order,
            "label": label,
            "bvid": key,
            "q": q,
        }
    )


@router.post("/posts")
def create_post(body: PostCreateIn):
    """手工新增一条入库帖子。"""
    try:
        post = get_store().create_post(
            text=body.text,
            platform=body.platform,
            topic=body.topic,
            author=body.author,
            source_url=body.source_url,
            bvid=resolve_bvid(body.bvid) or body.bvid,
            video_title=body.video_title,
            sentiment_label=body.sentiment_label,
        )
    except ValueError as exc:
        return err("invalid_request", str(exc), status=400)
    except Exception as exc:
        msg = str(exc)
        if "UNIQUE" in msg.upper():
            return err("duplicate", "同平台 source_id 已存在", status=409)
        return err("create_failed", msg, status=500)
    return ok(post, status=201)


@router.get("/posts/review")
def list_review_posts(
    limit: int = Query(default=40, ge=1, le=200),
    bvid: str | None = Query(default=None, max_length=200),
):
    """难例列表：uncertain / 低置信优先，供人工改判。"""
    key = resolve_bvid(bvid)
    items = get_store().list_review_posts(limit=limit, bvid=key)
    return ok({"items": items, "count": len(items), "bvid": key})


@router.get("/posts/{post_id}")
def get_post(post_id: int):
    post = get_store().get_post(post_id)
    if not post:
        return err("not_found", "帖子不存在", status=404)
    return ok(post)


@router.patch("/posts/{post_id}")
def update_post(post_id: int, body: PostUpdateIn):
    """更新帖子正文 / 话题 / 平台等字段。"""
    payload = body.model_dump(exclude_unset=True)
    if not payload:
        return err("empty_update", "没有可更新字段", status=400)
    try:
        if "bvid" in payload and payload["bvid"]:
            payload["bvid"] = resolve_bvid(payload["bvid"]) or payload["bvid"]
        post = get_store().update_post(post_id, **payload)
    except ValueError as exc:
        return err("invalid_request", str(exc), status=400)
    if not post:
        return err("not_found", "帖子不存在", status=404)
    return ok(post)


@router.delete("/posts/{post_id}")
def delete_post(post_id: int):
    ok_del = get_store().delete_post(post_id)
    if not ok_del:
        return err("not_found", "帖子不存在", status=404)
    return ok({"deleted": 1, "id": post_id})


@router.patch("/posts/{post_id}/sentiment")
def override_post_sentiment(post_id: int, body: SentimentOverrideIn):
    from src.services.sentiment_review import apply_sentiment_override

    try:
        post = apply_sentiment_override(
            post_id,
            body.label,
            method=body.method or "manual",
            confidence=body.confidence,
        )
    except LookupError:
        return err("not_found", "帖子不存在", status=404)
    except ValueError as exc:
        return err("invalid_label", str(exc), status=400)
    return ok(post)


@router.post("/posts/delete")
def delete_posts(body: DeletePostsBody):
    """按 id / BV / 视频标题包含 / 话题 清理噪声帖。默认 dry_run=false 真删。"""
    bvid = normalize_bvid(body.bvid) if body.bvid else None
    if body.bvid and body.bvid.strip() and not bvid:
        bvid = body.bvid.strip()
    try:
        result = get_store().delete_posts(
            ids=body.ids,
            bvid=bvid,
            video_title_contains=body.title_contains,
            topic=body.topic,
            platform=body.platform,
            dry_run=body.dry_run,
        )
    except ValueError as exc:
        return err("invalid_request", str(exc), status=400)
    return ok(result)


@router.get("/dashboard/overview")
def dashboard_overview():
    return ok(get_store().overview())
