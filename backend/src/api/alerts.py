"""预警与报告 API。"""

from __future__ import annotations

from fastapi import APIRouter, Query

from src.lib.http import ok
from src.services.forecast import (
    build_report_summary,
    daily_volume_series,
    detect_alerts,
)

router = APIRouter(tags=["alerts-reports"])


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
        }
    )


@router.get("/trends")
def trends(days: int = Query(default=14, ge=3, le=60)):
    return ok({"series": daily_volume_series(days)})


@router.get("/reports/summary")
def report_summary():
    return ok(build_report_summary())
