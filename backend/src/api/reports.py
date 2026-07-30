"""报告 API：全局汇总、单视频口碑、导出。"""

from __future__ import annotations

from fastapi import APIRouter, Query
from fastapi.responses import Response
from pydantic import BaseModel

from src.lib.http import err, ok
from src.services.forecast import build_report_summary
from src.services.report import build_csv_bytes, build_pdf_bytes, generate_ai_summary
from src.services.video_report import build_video_report, list_video_summaries

router = APIRouter(tags=["reports"])


class ReportSummaryIn(BaseModel):
    with_ai: bool = False


class VideoReportIn(BaseModel):
    bvid: str
    with_ai: bool = False


@router.get("/reports/summary")
def report_summary():
    return ok(build_report_summary())


@router.post("/reports/summary")
def report_summary_post(body: ReportSummaryIn):
    data = build_report_summary()
    if body.with_ai:
        ai = generate_ai_summary(data)
        data["ai"] = ai
        if ai.get("summary"):
            data["ai_summary"] = ai["summary"]
    return ok(data)


@router.get("/reports/videos")
def report_videos(limit: int = Query(default=50, ge=1, le=200)):
    items = list_video_summaries(limit=limit)
    return ok({"items": items, "count": len(items)})


@router.get("/reports/video")
def report_video(
    bvid: str = Query(..., min_length=2, max_length=200),
    with_ai: bool = Query(default=False),
):
    try:
        data = build_video_report(bvid, with_ai=with_ai)
    except ValueError as exc:
        return err("invalid_bvid", str(exc), status=400)
    return ok(data)


@router.post("/reports/video")
def report_video_post(body: VideoReportIn):
    try:
        data = build_video_report(body.bvid, with_ai=body.with_ai)
    except ValueError as exc:
        return err("invalid_bvid", str(exc), status=400)
    return ok(data)


@router.get("/reports/export.csv")
def export_csv(with_ai: bool = Query(default=False)):
    data = build_report_summary()
    if with_ai:
        ai = generate_ai_summary(data)
        if ai.get("summary"):
            data["ai_summary"] = ai["summary"]
    content = build_csv_bytes(data)
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="zhiwei-report.csv"'
        },
    )


@router.get("/reports/export.pdf")
def export_pdf(with_ai: bool = Query(default=False)):
    data = build_report_summary()
    if with_ai:
        ai = generate_ai_summary(data)
        if ai.get("summary"):
            data["ai_summary"] = ai["summary"]
    try:
        content = build_pdf_bytes(data)
    except Exception as exc:
        return err("pdf_failed", f"PDF 生成失败: {exc}", status=500)
    return Response(
        content=content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="zhiwei-report.pdf"'
        },
    )
