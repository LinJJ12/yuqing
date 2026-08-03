"""登录与当前用户。"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Header
from pydantic import BaseModel, Field

from src.lib.http import err, ok
from src.services.auth import (
    create_access_token,
    decode_access_token,
    extract_bearer,
    verify_credentials,
)

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginBody(BaseModel):
    username: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=1, max_length=200)


@router.post("/login")
def login(body: LoginBody):
    if not verify_credentials(body.username, body.password):
        return err("invalid_credentials", "用户名或密码错误", status=401)
    username = body.username.strip()
    token = create_access_token(username)
    return ok(
        {
            "access_token": token,
            "token_type": "bearer",
            "user": {"username": username},
        }
    )


@router.get("/me")
def me(authorization: Annotated[str | None, Header()] = None):
    token = extract_bearer(authorization)
    if not token:
        return err("unauthorized", "请先登录", status=401)
    username = decode_access_token(token)
    if not username:
        return err("unauthorized", "登录已失效，请重新登录", status=401)
    return ok({"username": username})


@router.post("/logout")
def logout() -> Any:
    """无状态 JWT：服务端无会话可清；客户端丢弃令牌即可。"""
    return ok({"logged_out": True})
