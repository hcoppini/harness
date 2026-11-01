"""
Tests for October reality audit, deliverable reallocation, and dynamic operating modes (Fortress, Field, Surge/Recovery).
"""

import json
import sqlite3
import pytest
from pathlib import Path

from app.db import init_db
from app.services import tum_service
from engine import workload_governor, kill_list_controller


@pytest.fixture
def test_env(tmp_path, monkeypatch):
    # Setup temporary db and operating mode file
    db_file = tmp_path / "test_harness.db"
    init_db(db_file)
    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row

    temp_op_file = tmp_path / "operating_mode.json"
    monkeypatch.setattr(workload_governor, "OPERATING_MODE_FILE", temp_op_file)
    monkeypatch.setattr(workload_governor, "DATA_DIR", tmp_path)

    yield conn, tmp_path
    conn.close()


def test_station_states_and_reallocation():
    roadmap = tum_service.get_metro_roadmap()
    stations = {s["id"]: s for s in roadmap.get("stations", [])}

    assert "sep-2026" in stations
    assert stations["sep-2026"]["status"] == "completed"

    assert "oct-2026" in stations
    assert stations["oct-2026"]["status"] == "completed"
    assert "Academics" in stations["oct-2026"].get("passed_over_deliverables", [])

    assert "nov-2026" in stations
    assert stations["nov-2026"]["status"] == "active"
    assert stations["nov-2026"]["deliverable_counts"]["Academics"]["total"] == 42
    assert stations["nov-2026"]["deliverable_counts"]["Code"]["total"] == 17

    # Dec 2026
    assert stations["dec-2026"]["deliverable_counts"]["Academics"]["total"] == 42
    assert stations["dec-2026"]["deliverable_counts"]["German"]["total"] == 110

    # Summer months
    assert stations["jun-2027"]["deliverable_counts"]["Academics"]["total"] == 46
    assert stations["jun-2027"]["deliverable_counts"]["Code"]["total"] == 21

    assert stations["jul-aug-2027"]["deliverable_counts"]["Academics"]["total"] == 54
    assert stations["jul-aug-2027"]["deliverable_counts"]["German"]["total"] == 165

    assert stations["sep-2027"]["deliverable_counts"]["Academics"]["total"] == 46
    assert stations["sep-2027"]["deliverable_counts"]["Code"]["total"] == 22


def test_operating_mode_toggle_and_governor(test_env):
    conn, tmp_path = test_env

    # 1. Default mode is FORTRESS
    assert workload_governor.get_operating_mode() == "FORTRESS"

    # 2. Toggle to FIELD mode
    res_field = workload_governor.set_operating_mode("FIELD")
    assert res_field["success"] is True
    assert workload_governor.get_operating_mode() == "FIELD"

    # In FIELD mode, workload governor sets mode to TRAVEL (Minimal Maintenance Floor)
    analysis_field = workload_governor.get_workload_analysis("2026-11-02", conn=conn)
    assert analysis_field["mode"] == "TRAVEL"
    assert "Field Mode" in analysis_field["mode_label"]
    assert analysis_field["is_us_travel_mode"] is True

    # 3. Toggle to SURGE_RECOVERY mode
    res_rec = workload_governor.set_operating_mode("SURGE_RECOVERY")
    assert res_rec["success"] is True
    assert workload_governor.get_operating_mode() == "SURGE_RECOVERY"

    # In SURGE_RECOVERY mode, workload governor sets mode to SURGE_RECOVERY (Biological Baseline)
    analysis_rec = workload_governor.get_workload_analysis("2026-11-02", conn=conn)
    assert analysis_rec["mode"] == "SURGE_RECOVERY"
    assert "Biological Baseline" in analysis_rec["mode_label"]
    assert analysis_rec["is_recovery_mode"] is True

    # Study plan synthesis generates Recovery Protocol
    plan_rec = workload_governor.synthesize_adaptive_schedule({"blocks": []}, date_str="2026-11-02", conn=conn)
    assert "Recovery Protocol" in plan_rec["name"]
    block_foci = [b["focus"] for b in plan_rec["blocks"]]
    assert any("Biological Floor" in f for f in block_foci)

    # 4. Toggle back to FORTRESS mode
    res_fortress = workload_governor.set_operating_mode("FORTRESS")
    assert res_fortress["success"] is True
    assert workload_governor.get_operating_mode() == "FORTRESS"

    # In FORTRESS mode on an empty test_db, mode returns to normal adaptive (CRUISE)
    analysis_fortress = workload_governor.get_workload_analysis("2026-11-02", conn=conn)
    assert analysis_fortress["mode"] == "CRUISE"


def test_invalid_operating_mode(test_env):
    res = workload_governor.set_operating_mode("INVALID_MODE")
    assert res["success"] is False
    assert "Invalid mode" in res["error"]
