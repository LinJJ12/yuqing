"""本地单管理员凭证校验与 JWT 签发。"""

from __future__ import annotations

import hmac
import time
from typing import Any

import jwt

from src.config.settings import settings


def verify_credentials(username: str, password: str) -> bool:
    expected_user = (settings.auth_username or "").strip()
    expected_pass = settings.auth_password or ""
    if not expected_user or not expected_pass:
        return False
    user_ok = hmac.compare_digest((username or "").strip(), expected_user)
    pass_ok = hmac.compare_digest(password or "", expected_pass)
    return user_ok and pass_ok


def create_access_token(username: str) -> str:
    now = int(time.time())
    expire_hours = max(1, int(settings.jwt_expire_hours or 24))
    payload: dict[str, Any] = {
        "sub": username.strip(),
        "iat": now,
        "exp": now + expire_hours * 3600,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_access_token(token: str) -> str | None:
    if not token or not (settings.jwt_secret or "").strip():
        return None
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None
    sub = payload.get("sub")
    if not isinstance(sub, str) or not sub.strip():
        return None
    expected = (settings.auth_username or "").strip()
    if expected and not hmac.compare_digest(sub.strip(), expected):
        return None
    return sub.strip()


def extract_bearer(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    token = parts[1].strip()
    return token or None
