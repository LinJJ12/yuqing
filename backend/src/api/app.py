"""FastAPI 应用组装（HTTP 入口层）。"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config.settings import settings
from src.lib.http import err, ok
from src.storage.db import get_store
from src.api.alerts import router as alerts_router
from src.api.analysis import router as analysis_router
from src.api.agent import router as agent_router
from src.api.collect import router as collect_router
from src.api.data import router as data_router
from src.api.health import router as health_router


@asynccontextmanager
async def lifespan(_app: FastAPI):
    get_store().initialize()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="社交媒体舆情监测：BERT 情感 + BERTopic 主题 + 趋势预警；支持 B 站评论口碑分析（Python + Vue + GPU）",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_request, exc: Exception):
        # 避免返回纯文本 Internal Server Error，统一 JSON 契约
        return err("internal_error", f"服务器内部错误: {exc}", status=500)

    app.include_router(health_router, prefix="/api/v1")
    app.include_router(data_router, prefix="/api/v1")
    app.include_router(collect_router, prefix="/api/v1")
    app.include_router(analysis_router, prefix="/api/v1")
    app.include_router(alerts_router, prefix="/api/v1")
    app.include_router(agent_router, prefix="/api/v1")

    @app.get("/")
    def root():
        return ok(
            {
                "name": settings.app_name,
                "version": settings.app_version,
                "docs": "/docs",
            }
        )

    return app


app = create_app()
