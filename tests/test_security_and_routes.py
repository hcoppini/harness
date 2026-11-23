"""Security, route hardening, and diagnostics tests for Harness server.py (TD-02, TD-03, TD-17)."""

import shutil
import pytest

from app.db import init_db, DEFAULT_DB_PATH
from app.services import sync_service
import server
from server import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    test_db = tmp_path / "test_sec.db"
    test_data = tmp_path / "data"
    test_data.mkdir(parents=True, exist_ok=True)
    init_db(test_db)

    src_data = DEFAULT_DB_PATH.parent
    for jf in src_data.glob("*.json"):
        shutil.copy2(jf, test_data / jf.name)

    monkeypatch.setenv("HARNESS_DB_PATH", str(test_db))
    monkeypatch.setattr("app.db.DEFAULT_DB_PATH", test_db)
    monkeypatch.setattr(sync_service, "DATA_DIR", test_data)
    monkeypatch.setattr(server, "DATA_DIR", test_data)
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_data_route_blocks_sensitive_files_and_allows_public_json(client):
    """TD-02: /data/ must never expose SQLite DBs, credentials, or traversal paths."""
    for blocked in (
        "/data/harness.db",
        "/data/sync_config.json",
        "/data/vulcan_config.json",
        "/data/gcalendar_config.json",
        "/data/../server.py",
        "/mobile/data/harness.db",
        "/mobile/data/sync_config.json",
    ):
        res = client.get(blocked)
        assert res.status_code in (403, 404), f"Expected 403/404 for {blocked}, got {res.status_code}"

    # Allowlisted public JSON must succeed
    res_ok = client.get("/data/schedules.json")
    assert res_ok.status_code == 200
    assert "schedules" in res_ok.get_json()


def test_api_key_auth_enforced_when_configured(client, monkeypatch):
    """TD-03: X-Harness-Key / Bearer token is enforced on /api/* when HARNESS_API_KEY is set."""
    monkeypatch.setenv("HARNESS_API_KEY", "super-secret-harness-key")

    # Public /api/health remains open
    assert client.get("/api/health").status_code == 200

    # Missing key -> 401
    assert client.get("/api/health/diagnostics").status_code == 401
    assert client.post("/api/rpc/get_dashboard", json={}).status_code == 401

    # Wrong key -> 401
    assert client.get("/api/health/diagnostics", headers={"X-Harness-Key": "wrong"}).status_code == 401

    # Correct X-Harness-Key -> 200
    res = client.get("/api/health/diagnostics", headers={"X-Harness-Key": "super-secret-harness-key"})
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "healthy"
    assert data["database"]["ok"] is True

    # Correct Bearer token -> 200
    res_bearer = client.get(
        "/api/health/diagnostics",
        headers={"Authorization": "Bearer super-secret-harness-key"},
    )
    assert res_bearer.status_code == 200


def test_desktop_only_rpc_blocked_in_headless_mode(client, monkeypatch):
    """TD-03: Desktop OS-launch RPC methods must return 403 in hosted/serverless mode."""
    monkeypatch.setenv("HARNESS_HEADLESS", "1")
    res = client.post(
        "/api/rpc/launch_kill_item",
        json={"args": ["url", "https://example.com"]},
    )
    assert res.status_code == 403
    assert "disabled" in res.get_json()["error"].lower()


def test_diagnostics_and_leveling_routes(client):
    """TD-17: Diagnostics and Material Deficit endpoints return structured telemetry."""
    diag = client.get("/api/health/diagnostics")
    assert diag.status_code == 200
    body = diag.get_json()
    assert "database" in body and body["database"]["ok"] is True
    assert "timetable" in body
    assert "engine" in body
    assert "recent_errors" in body

    # Add and toggle material deficit item via REST
    add_res = client.post(
        "/api/leveling/deficit",
        json={"subject": "Matematyka", "topic": "Funkcje wymierne", "priority": 1},
    )
    assert add_res.status_code == 200
    created = add_res.get_json()
    assert created["status"] == "open"

    tog_res = client.post(f"/api/leveling/deficit/{created['id']}/toggle")
    assert tog_res.status_code == 200
    assert tog_res.get_json()["item"]["status"] == "resolved"
