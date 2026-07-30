"""Yuqing backend 入口。

用法（仓库根目录，沿用根 .venv）：
  uv run python backend/main.py
  uv run python backend/main.py --reload

或在 backend/ 目录：
  cd backend
  uv run --project .. python main.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import uvicorn

from src.config.settings import settings


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Yuqing opinion / audience-feedback API")
    parser.add_argument("--host", default=settings.host)
    parser.add_argument("--port", type=int, default=settings.port)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args(argv)
    print(f"[main] http://{args.host}:{args.port}")
    uvicorn.run(
        "src.api.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        reload_dirs=[str(BACKEND_ROOT / "src")] if args.reload else None,
    )


if __name__ == "__main__":
    main()
