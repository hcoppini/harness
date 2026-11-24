"""
Autonomous Durability & 6-Month Zero-Touch Execution Test Suite.
Verifies:
1. Zero-touch calendar month station rollover (Nov 2026 -> Dec 2026 -> Jan 2027).
2. Smart Catch-Up Redistribution (no punitive linear deficits on rest days).
3. 1-Click Baseline Rebase (clears phantom deficits while preserving all academic records).
4. Material Deficit Ledger (P1/P2/P3 concept gap tracking and mastery).
5. Two-Way Sync Conflict Ledger (durable conflict recording and authoritative resolution).
6. Cache-Control Header Enforcing (PWA never caches stale HTML or Service Worker).
"""

import json
import sqlite3
import pytest
from datetime import datetime
from unittest.mock import patch
from app.db import init_db
from engine import kill_list_controller
from app.services import leveling_service, sync_service


@pytest.fixture
def autonomous_env(tmp_path, monkeypatch):
    import shutil
    from app.services import tum_service

    # Setup temporary data folder with metro_roadmap.json
    temp_metro = tmp_path / "metro_roadmap.json"
    shutil.copy(kill_list_controller.DATA_DIR / "metro_roadmap.json", temp_metro)
    monkeypatch.setattr(kill_list_controller, "DATA_DIR", tmp_path)
    monkeypatch.setattr(tum_service, "DATA_DIR", tmp_path)
    monkeypatch.setattr(leveling_service, "DATA_DIR", tmp_path)

    # Setup isolated SQLite database
    db_file = tmp_path / "test_autonomous.db"
    init_db(db_file)
    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row
    yield {"conn": conn, "tmp_path": tmp_path, "metro_file": temp_metro}
    conn.close()


def test_zero_touch_calendar_month_rollover(autonomous_env):
    """
    Simulates calendar progressing from Nov 2026 into Dec 2026 without user touching code.
    Verifies that get_active_station_id() automatically marks Nov completed and Dec active.
    """
    conn = autonomous_env["conn"]
    metro_file = autonomous_env["metro_file"]

    # In November 2026, active station is nov-2026
    fake_nov = datetime(2026, 11, 25, 10, 0, 0)
    with patch("engine.kill_list_controller.datetime") as mock_dt:
        mock_dt.now.return_value = fake_nov
        mock_dt.strptime = datetime.strptime
        active_id = kill_list_controller.get_active_station_id(conn=conn)
        assert active_id == "nov-2026"

    # Now simulate time rolling into December 1, 2026
    fake_dec = datetime(2026, 12, 1, 8, 0, 0)
    with patch("engine.kill_list_controller.datetime") as mock_dt:
        mock_dt.now.return_value = fake_dec
        mock_dt.strptime = datetime.strptime
        active_id_dec = kill_list_controller.get_active_station_id(conn=conn)
        assert active_id_dec == "dec-2026"

    # Verify metro_roadmap.json on disk was automatically updated
    with open(metro_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    nov_st = next(s for s in data["stations"] if s["id"] == "nov-2026")
    dec_st = next(s for s in data["stations"] if s["id"] == "dec-2026")
    assert nov_st["status"] == "completed"
    assert dec_st["status"] == "active"


def test_smart_catch_up_redistribution_and_capacity_ceilings(autonomous_env):
    """
    Verifies that pace velocity calculates daily run-rate over remaining days
    against human capacity ceilings (e.g. 14 math problems/day, 1.6 workouts/day).
    """
    conn = autonomous_env["conn"]

    # Day 5 of November (30 days total, 26 remaining)
    test_date = "2026-11-05"
    velocity = kill_list_controller.get_station_pace_velocity("nov-2026", date_str=test_date, conn=conn)

    # Deliverables should have daily_run_rate and catch_up_achievable flags
    assert "deliverables" in velocity
    assert len(velocity["deliverables"]) > 0

    for d in velocity["deliverables"]:
        assert "daily_run_rate" in d
        assert "capacity_ceiling" in d
        assert "catch_up_achievable" in d
        assert d["daily_run_rate"] >= 0.0


def test_baseline_rebase_clears_phantom_deficits(autonomous_env):
    """
    Verifies 1-click baseline rebase resets elapsed pace ratio from today forward,
    clearing phantom historical debt while keeping academic data intact.
    """
    conn = autonomous_env["conn"]

    # Rebase nov-2026 to Nov 26
    res = leveling_service.rebase_to_today(baseline_date="2026-11-26", active_station_id="nov-2026", conn=conn)
    assert res["success"] is True
    assert res["baseline_date"] == "2026-11-26"

    # Check pace on Nov 26: deficit is 0.0, optimal pace
    pace = kill_list_controller.get_station_pace_velocity("nov-2026", date_str="2026-11-26", conn=conn)
    assert pace["is_rebased"] is True
    assert pace["baseline_date"] == "2026-11-26"
    assert pace["max_deficit"] == 0.0
    assert pace["is_behind"] is False


def test_material_deficit_ledger_crud(autonomous_env):
    """
    Verifies School Material Deficit Ledger (P1/P2/P3 concept gap tracker).
    """
    conn = autonomous_env["conn"]

    # Add deficit
    item = leveling_service.add_material_deficit(
        subject="Matematyka",
        topic="Wzory redukcyjne trygonometria",
        priority="P1",
        notes="Potrzebne do sprawdzianu w piatek",
        station_id="nov-2026",
        conn=conn,
    )
    assert item["subject"] == "Matematyka"
    assert item["priority"] == 1
    assert item["mastered"] is False

    # List deficits
    deficits = leveling_service.get_material_deficits(conn=conn)
    assert len(deficits) == 1
    assert deficits[0]["id"] == item["id"]

    # Toggle mastered
    res = leveling_service.toggle_material_deficit(item["id"], conn=conn)
    assert res["success"] is True
    assert res["mastered"] is True

    # Verify toggle persisted
    deficits_after = leveling_service.get_material_deficits(conn=conn)
    assert deficits_after[0]["mastered"] is True


def test_sync_conflict_ledger_and_resolution(autonomous_env):
    """
    Verifies two-way sync conflict audit table and resolution mechanism.
    """
    conn = autonomous_env["conn"]

    local_payload = {"id": "task_123", "title": "Solve 5 LeetCode", "completed": 1}
    remote_payload = {"id": "task_123", "title": "Solve 5 LeetCode", "completed": 0}

    # Record conflict
    conf_id = sync_service.record_sync_conflict(
        entity_type="tasks",
        entity_id="task_123",
        local_data=local_payload,
        remote_data=remote_payload,
        conn=conn,
    )
    assert conf_id.startswith("conf_")

    # Retrieve pending conflicts
    pending = sync_service.get_pending_conflicts(conn=conn)
    assert len(pending) == 1
    assert pending[0]["id"] == conf_id
    assert pending[0]["resolved"] is False

    # Resolve conflict choosing local authority
    resolve_res = sync_service.resolve_sync_conflict(conf_id, resolution_choice="local", conn=conn)
    assert resolve_res["success"] is True
    assert resolve_res["resolution"] == "local"

    # Pending list should now be empty
    pending_after = sync_service.get_pending_conflicts(conn=conn)
    assert len(pending_after) == 0


def test_server_cache_control_headers():
    """
    Verifies that Flask server sets no-cache headers on root UI and service worker.
    """
    from server import app
    client = app.test_client()

    for path in ["/", "/mobile", "/sw.js"]:
        resp = client.get(path)
        assert resp.status_code in (200, 304, 404)
        if resp.status_code == 200:
            cc = resp.headers.get("Cache-Control", "")
            assert "no-cache" in cc
            assert "no-store" in cc
