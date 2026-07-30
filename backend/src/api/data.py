"""导入与帖子、总览 API。"""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, Query, UploadFile

from src.config.settings import settings
from src.lib.http import err, ok
from src.services.ingest import import_file
from src.storage.db import get_store

router = APIRouter(tags=["data"])

ALLOWED = {".json", ".jsonl", ".ndjson", ".csv"}


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
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    posts = get_store().list_posts(topic=topic, limit=limit, offset=offset)
    return ok({"items": posts, "count": len(posts), "total": get_store().count_posts()})


@router.get("/dashboard/overview")
def dashboard_overview():
    return ok(get_store().overview())
