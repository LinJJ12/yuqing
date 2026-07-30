"""预警、趋势、报告、设置 API。"""

from __future__ import annotations

from fastapi import APIRouter, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field

from src.lib.http import err, ok
from src.services.forecast import (
    build_report_summary,
    daily_volume_series,
    detect_alerts,
    get_alert_keywords,
    set_alert_keywords,
)
from src.services.report import build_csv_bytes, build_pdf_bytes, generate_ai_summary

router = APIRouter(tags=["alerts-reports"])


class AlertKeywordsIn(BaseModel):
    keywords: list[str] = Field(default_factory=list, max_length=200)


class ReportSummaryIn(BaseModel):
    with_ai: bool = False


@router.get("/alerts")
def list_alerts(limit: int = Query(default=50, ge=1, le=200)):
    items = detect_alerts()[:limit]
    return ok(
        {
            "items": items,
            "count": len(items),
            "high": sum(1 for a in items if a["severity"] == "high"),
            "medium": sum(1 for a in items if a["severity"] == "medium"),
            "low": sum(1 for a in items if a["severity"] == "low"),
            "keywords": get_alert_keywords(),
        }
    )


@router.get("/trends")
def trends(
    days: int = Query(default=14, ge=3, le=60),
    use_prophet: bool = Query(default=True),
    prophet_horizon: int = Query(default=7, ge=1, le=30),
):
    return ok(
        daily_volume_series(
            days,
            use_prophet=use_prophet,
            prophet_horizon=prophet_horizon,
        )
    )


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
            "Content-Disposition": 'attachment; filename="yuqing-report.csv"'
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
            "Content-Disposition": 'attachment; filename="yuqing-report.pdf"'
        },
    )


@router.get("/settings/alert-keywords")
def read_alert_keywords():
    return ok({"keywords": get_alert_keywords()})


@router.put("/settings/alert-keywords")
def write_alert_keywords(body: AlertKeywordsIn):
    keywords = set_alert_keywords(body.keywords)
    return ok({"keywords": keywords})
