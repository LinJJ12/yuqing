"""预警、趋势、敏感词设置 API。"""

from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from src.lib.http import ok
from src.services.forecast import (
    daily_volume_series,
    detect_alerts,
    get_alert_keywords,
    set_alert_keywords,
)

router = APIRouter(tags=["alerts"])


class AlertKeywordsIn(BaseModel):
    keywords: list[str] = Field(default_factory=list, max_length=200)


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


@router.get("/settings/alert-keywords")
def read_alert_keywords():
    return ok({"keywords": get_alert_keywords()})


@router.put("/settings/alert-keywords")
def write_alert_keywords(body: AlertKeywordsIn):
    keywords = set_alert_keywords(body.keywords)
    return ok({"keywords": keywords})
