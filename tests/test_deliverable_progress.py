"""Unit tests for Deliverable Progress, study volume logging, and German deficit resolution."""

import sqlite3
import pytest
from app.db import init_db
from engine import kill_list_controller


@pytest.fixture
def test_db(tmp_path):
    db_file = tmp_path / "test_deliv_progress.db"
    init_db(db_file)
    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


def test_update_deliverable_progress_and_completion(test_db):
    # Check initial German words deliverable (sep26_german_anki, total=100)
    delivs = kill_list_controller.get_station_deliverables("sep-2026", conn=test_db)
    german = [d for d in delivs if d["deliverable_id"] == "sep26_german_anki"][0]
    assert german["completed_count"] == 0
    assert german["is_completed"] is False

    # Update to 35 words completed
    res = kill_list_controller.update_deliverable_progress("sep26_german_anki", new_count=35, conn=test_db)
    assert res["success"] is True
    assert res["completed_count"] == 35
    assert res["is_completed"] is False

    # Increment by 65 words -> total 100 -> should be completed
    res2 = kill_list_controller.update_deliverable_progress("sep26_german_anki", delta=65, conn=test_db)
    assert res2["success"] is True
    assert res2["completed_count"] == 100
    assert res2["is_completed"] is True


def test_log_study_reps_and_deficit_resolution(test_db):
    # Check pace velocity before logging
    test_date = "2026-09-15"
    vel_before = kill_list_controller.get_station_pace_velocity("sep-2026", date_str=test_date, conn=test_db)
    # On day 15/30, required is 50 words -> deficit should be 50.0
    german_before = [d for d in vel_before["deliverables"] if d["deliverable_id"] == "sep26_german_anki"][0]
    assert german_before["is_behind"] is True
    assert german_before["deficit"] == 50.0

    # Log 60 German words studied
    log_res = kill_list_controller.log_study_reps(
        deliverable_id="sep26_german_anki",
        count=60,
        notes="Anki DW A2 Unit 3",
        conn=test_db,
    )
    assert log_res["success"] is True
    assert log_res["completed_count"] == 60

    # Check pace velocity after logging: 60 > 50 -> German is no longer behind!
    vel_after = kill_list_controller.get_station_pace_velocity("sep-2026", date_str=test_date, conn=test_db)
    german_after = [d for d in vel_after["deliverables"] if d["deliverable_id"] == "sep26_german_anki"][0]
    assert german_after["is_behind"] is False
    assert german_after["deficit"] == 0.0


def test_kill_item_with_custom_quantity(test_db):
    test_date = "2026-09-08"
    # Queue a kill item with 15 leetcode problems
    item = kill_list_controller.add_kill_item(
        category="Algorithms",
        title="LeetCode Arrays & Two Pointers Drill",
        action_type="url",
        target_path="https://leetcode.com",
        target_spec="5 problems",
        station_deliverable_id="sep26_hackerrank_15",
        quantity=5,
        date_str=test_date,
        conn=test_db,
    )
    assert item["quantity"] == 5

    # Toggle complete -> increments deliverable by 5 (4 initial + 5 = 9)
    res = kill_list_controller.toggle_kill_item(item["id"], conn=test_db)
    assert res["success"] is True
    assert res["completed"] is True
    assert res["deliverable"]["completed_count"] == 9

    # Toggle incomplete -> decrements deliverable by 5 back to initial 4
    res_undo = kill_list_controller.toggle_kill_item(item["id"], conn=test_db)
    assert res_undo["success"] is True
    assert res_undo["completed"] is False
    assert res_undo["deliverable"]["completed_count"] == 4


def test_progressive_deliverable_enqueue_and_advance(test_db):
    test_date = "2026-09-14"

    # Initial state seeded in DB: LeetCode has completed_count = 4
    delivs = kill_list_controller.get_station_deliverables("sep-2026", conn=test_db)
    leetcode = next(d for d in delivs if d["deliverable_id"] == "sep26_leetcode_15")
    assert leetcode["completed_count"] == 4
    assert "Problem #5" in leetcode["next_spec"]["target_spec"]

    # 1-Click enqueue progressive deliverable
    item = kill_list_controller.enqueue_progressive_deliverable("sep26_leetcode_15", date_str=test_date, conn=test_db)
    assert "Problem #5" in item["target_spec"]
    assert item["station_deliverable_id"] == "sep26_leetcode_15"
    assert item["quantity"] == 1

    # Mark item completed in SGH Library session
    res = kill_list_controller.toggle_kill_item(item["id"], conn=test_db)
    assert res["completed"] is True
    assert res["deliverable"]["completed_count"] == 5

    # Check that next progression auto-advanced to Problem #6!
    delivs_after = kill_list_controller.get_station_deliverables("sep-2026", conn=test_db)
    leetcode_after = next(d for d in delivs_after if d["deliverable_id"] == "sep26_leetcode_15")
    assert leetcode_after["completed_count"] == 5
    assert "Problem #6" in leetcode_after["next_spec"]["target_spec"]

    # Enqueueing next day naturally gets Problem #6
    item_next = kill_list_controller.enqueue_progressive_deliverable("sep26_leetcode_15", date_str="2026-09-15", conn=test_db)
    assert "Problem #6" in item_next["target_spec"]


def test_progressive_math_diag_enqueue_and_advance(test_db):
    test_date = "2026-09-14"

    # Initial state: Math R Diagnostic has completed_count = 0
    delivs = kill_list_controller.get_station_deliverables("sep-2026", conn=test_db)
    math_d = next(d for d in delivs if d["deliverable_id"] == "sep26_math_diag")
    assert math_d["completed_count"] == 0
    assert "Zadania 1–5" in math_d["next_spec"]["target_spec"]

    # Enqueue first 5
    item = kill_list_controller.enqueue_progressive_deliverable("sep26_math_diag", date_str=test_date, conn=test_db)
    assert "Zadania 1–5" in item["target_spec"]
    assert item["quantity"] == 5

    # Complete it
    res = kill_list_controller.toggle_kill_item(item["id"], conn=test_db)
    assert res["completed"] is True
    assert res["deliverable"]["completed_count"] == 5

    # Check next auto-advanced to 6–10
    delivs_after = kill_list_controller.get_station_deliverables("sep-2026", conn=test_db)
    math_after = next(d for d in delivs_after if d["deliverable_id"] == "sep26_math_diag")
    assert math_after["completed_count"] == 5
    assert "Zadania 6–10" in math_after["next_spec"]["target_spec"]

