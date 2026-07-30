"""统一 API 响应。"""

from __future__ import annotations

from typing import Any

from fastapi.responses import JSONResponse


def ok(data: Any = None, status: int = 200) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"ok": True, "data": data if data is not None else {}},
    )


def err(
    code: str,
    message: str,
    status: int = 400,
    **details: Any,
) -> JSONResponse:
    payload: dict[str, Any] = {
        "ok": False,
        "error": {"code": code, "message": message},
    }
    if details:
        payload["error"]["details"] = details
    return JSONResponse(status_code=status, content=payload)
