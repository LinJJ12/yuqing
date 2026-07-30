# -*- coding: utf-8 -*-
"""全量重跑情感（换模型 / 写入 confidence 后使用）。"""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from src.services.jobs import _run_sentiment
from src.storage.db import get_store


def main() -> None:
    store = get_store()
    store.initialize()
    before = store.sentiment_stats()
    print("before:", before)
    result = _run_sentiment(limit=5000, only_pending=False)
    print("result updated=", result.get("updated"), "elapsed_ms=", result.get("elapsed_ms"))
    print("after:", result.get("stats"))


if __name__ == "__main__":
    main()
