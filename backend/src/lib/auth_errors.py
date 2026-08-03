"""鉴权相关异常（由 app 异常处理器转为 ok/err 信封）。"""

from __future__ import annotations


class UnauthorizedError(Exception):
    def __init__(
        self,
        message: str = "请先登录",
        *,
        code: str = "unauthorized",
    ) -> None:
        self.message = message
        self.code = code
        super().__init__(message)
