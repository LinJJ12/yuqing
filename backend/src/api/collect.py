"""内嵌采集 API（当前：B 站评论）。"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from src.lib.http import err, ok
from src.services.bilibili_collect import BilibiliCollectError, collect_bilibili

router = APIRouter(prefix="/collect", tags=["collect"])


class BilibiliCollectBody(BaseModel):
    keyword: str | None = Field(default=None, description="搜索关键词，如：数码评测")
    video: str | None = Field(
        default=None,
        description="视频 BV 号或链接（与 keyword 二选一或同时；有 video 时优先）",
    )
    topic: str | None = Field(default=None, max_length=100)
    max_videos: int = Field(default=3, ge=1, le=10)
    max_comments_per_video: int = Field(default=40, ge=1, le=200)
    include_video_title: bool = False


@router.post("/bilibili")
def collect_bilibili_endpoint(body: BilibiliCollectBody):
    if not (body.keyword or "").strip() and not (body.video or "").strip():
        return err("invalid_request", "请填写关键词或视频 BV/链接", status=400)
    try:
        job = collect_bilibili(
            keyword=body.keyword,
            video=body.video,
            topic=body.topic,
            max_videos=body.max_videos,
            max_comments_per_video=body.max_comments_per_video,
            include_video_title=body.include_video_title,
        )
    except BilibiliCollectError as exc:
        return err("collect_failed", str(exc), status=502)
    except Exception as exc:
        return err("collect_failed", f"B 站采集异常: {exc}", status=502)

    if job.get("status") == "failed":
        return err(
            "collect_failed",
            job.get("error_message") or "采集失败",
            status=502,
            job=job,
        )
    return ok(job)
