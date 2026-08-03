"""FastAPI 依赖（鉴权等）。"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import Header

from src.config.settings import settings
from src.lib.auth_errors import UnauthorizedError
from src.services.auth import decode_access_token, extract_bearer


def require_user(
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """业务路由依赖：无效令牌时抛出 UnauthorizedError → 401。"""
    if settings.auth_disabled:
        name = (settings.auth_username or "anonymous").strip() or "anonymous"
        return {"username": name}

    token = extract_bearer(authorization)
    if not token:
        raise UnauthorizedError("请先登录")

    username = decode_access_token(token)
    if not username:
        raise UnauthorizedError("登录已失效，请重新登录")

    return {"username": username}
