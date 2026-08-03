"""pytest 夹具：临时 SQLite + TestClient，不污染开发库。"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

TEST_USER = "testadmin"
TEST_PASS = "testpass-secret"
TEST_JWT_SECRET = "test-jwt-secret-for-pytest-32by!"


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
def auth_settings(monkeypatch):
    from src.config.settings import settings

    monkeypatch.setattr(settings, "auth_username", TEST_USER)
    monkeypatch.setattr(settings, "auth_password", TEST_PASS)
    monkeypatch.setattr(settings, "jwt_secret", TEST_JWT_SECRET)
    monkeypatch.setattr(settings, "jwt_expire_hours", 24)
    monkeypatch.setattr(settings, "auth_disabled", False)
    return settings


@pytest.fixture()
def raw_client(store, auth_settings):
    from src.api.app import app

    with TestClient(app) as c:
        yield c


@pytest.fixture()
def client(raw_client):
    """已登录的 TestClient（业务 API 测试默认带 Bearer）。"""
    r = raw_client.post(
        "/api/v1/auth/login",
        json={"username": TEST_USER, "password": TEST_PASS},
    )
    assert r.status_code == 200, r.text
    token = r.json()["data"]["access_token"]
    raw_client.headers.update({"Authorization": f"Bearer {token}"})
    yield raw_client
