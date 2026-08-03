"""鉴权 API 契约。"""

from __future__ import annotations

TEST_USER = "testadmin"
TEST_PASS = "testpass-secret"


def test_health_ready_public(raw_client):
    r = raw_client.get("/api/v1/health/ready")
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_protected_without_token(raw_client):
    r = raw_client.get("/api/v1/dashboard/overview")
    assert r.status_code == 401
    body = r.json()
    assert body["ok"] is False
    assert body["error"]["code"] == "unauthorized"


def test_login_success_and_me(raw_client):
    r = raw_client.post(
        "/api/v1/auth/login",
        json={"username": TEST_USER, "password": TEST_PASS},
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["token_type"] == "bearer"
    assert data["user"]["username"] == TEST_USER
    token = data["access_token"]

    r = raw_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["data"]["username"] == TEST_USER

    r = raw_client.get(
        "/api/v1/dashboard/overview",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_login_invalid_credentials(raw_client):
    r = raw_client.post(
        "/api/v1/auth/login",
        json={"username": TEST_USER, "password": "wrong"},
    )
    assert r.status_code == 401
    body = r.json()
    assert body["ok"] is False
    assert body["error"]["code"] == "invalid_credentials"


def test_logout_ok(client):
    r = client.post("/api/v1/auth/logout")
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_report_export_requires_auth(raw_client):
    r = raw_client.get("/api/v1/reports/export.csv")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "unauthorized"


def test_report_export_with_token(client):
    r = client.get("/api/v1/reports/export.csv")
    assert r.status_code == 200
    assert "text/csv" in r.headers.get("content-type", "")
