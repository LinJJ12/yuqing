"""pytest 夹具：临时 SQLite + TestClient，不污染开发库。"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


@pytest.fixture()
def store(tmp_path, monkeypatch):
    from src.storage import db as dbmod
    from src.storage.db import Store

    db_path = tmp_path / "test.db"
    s = Store(str(db_path))
    s.initialize()
    monkeypatch.setattr(dbmod, "_store", s)
    return s


@pytest.fixture()
def client(store):
    from src.api.app import app

    with TestClient(app) as c:
        yield c
