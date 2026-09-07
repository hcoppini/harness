"""Unit tests for Kill List & Metro Auto-Increment Controller (Harness 2.1)."""

import sqlite3
import pytest
from app.db import init_db
from engine import kill_list_controller


@pytest.fixture
def test_db(tmp_path):
    db_file = tmp_path / "test_kill_list.db"
    init_db(db_file)
    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


def test_kill_list_seeding_and_deliverables(test_db):
    deliverables = kill_list_controller.get_station_deliverables("sep-2026", conn=test_db)
    assert len(deliverables) == 5
    ids = [d["deliverable_id"] for d in deliverables]
    assert "sep26_math_diag" in ids
    assert "sep26_hackerrank_15" in ids
    assert "sep26_sigg_setup" in ids


def test_three_item_rule_enforcement(test_db):
    test_date = "2026-09-04"
    # Add Item 1: Math R
    item1 = kill_list_controller.add_kill_item(
        category="Math R",
        title="Math R Diagnostic Problem Sets 1-5",
        action_type="pdf",
        target_path="arkusze/matura_math.pdf",
        target_spec="Problems 1-5",
        station_deliverable_id="sep26_math_diag",
        date_str=test_date,
        conn=test_db,
    )
    assert item1["id"] is not None

    # Add Item 2: Algorithms
    item2 = kill_list_controller.add_kill_item(
        category="Algorithms",
        title="HackerRank: Dynamic Array Drill",
        action_type="url",
        target_path="https://www.hackerrank.com/challenges/dynamic-array",
        target_spec="Zero AI unassisted",
        station_deliverable_id="sep26_hackerrank_15",
        date_str=test_date,
        conn=test_db,
    )
    assert item2["id"] is not None

    # Add Item 3: German
    item3 = kill_list_controller.add_kill_item(
        category="German",
        title="Nicos Weg A2 Vocabulary Drill",
        action_type="url",
        target_path="https://learngerman.dw.com",
        target_spec="20 vocab cards",
        station_deliverable_id="sep26_german_anki",
        date_str=test_date,
        conn=test_db,
    )
    assert item3["id"] is not None

    # Attempting to add Item 4 MUST raise ValueError (3-Item Rule Enforced)
    with pytest.raises(ValueError, match="3-Item Rule Enforced"):
        kill_list_controller.add_kill_item(
            category="SIGG",
            title="Extra Task",
            action_type="workspace",
            target_path="c:\\workspace",
            date_str=test_date,
            conn=test_db,
        )

    # Verify get_kill_list returns all 3
    kl = kill_list_controller.get_kill_list(date_str=test_date, conn=test_db)
    assert kl["count"] == 3
    assert len(kl["items"]) == 3
    assert kl["items"][0]["deliverable"] is not None
    assert kl["items"][0]["deliverable"]["id"] == "sep26_math_diag"


def test_metro_auto_link_and_completion_gate(test_db):
    test_date = "2026-09-04"

    # Add 1 gate deliverable item (sep26_sigg_setup requires 1 to complete)
    item = kill_list_controller.add_kill_item(
        category="SIGG",
        title="Register Team & Test Environment",
        action_type="workspace",
        target_path="c:\\harness",
        target_spec="Gra Testowa Gate",
        station_deliverable_id="sep26_sigg_setup",
        date_str=test_date,
        conn=test_db,
    )

    # Initial deliverable check: 0 / 1, is_completed = 0
    delivs_before = {d["deliverable_id"]: d for d in kill_list_controller.get_station_deliverables("sep-2026", conn=test_db)}
    assert delivs_before["sep26_sigg_setup"]["completed_count"] == 0
    assert delivs_before["sep26_sigg_setup"]["is_completed"] is False

    # Complete the kill item
    res = kill_list_controller.complete_kill_item(item["id"], conn=test_db)
    assert res["success"] is True
    assert res["deliverable"]["completed_count"] == 1
    assert res["deliverable"]["is_completed"] is True

    # Check updated database state
    delivs_after = {d["deliverable_id"]: d for d in kill_list_controller.get_station_deliverables("sep-2026", conn=test_db)}
    assert delivs_after["sep26_sigg_setup"]["completed_count"] == 1
    assert delivs_after["sep26_sigg_setup"]["is_completed"] is True

    # Toggle off -> counter decrements and is_completed reverts to False
    toggle_res = kill_list_controller.toggle_kill_item(item["id"], conn=test_db)
    assert toggle_res["completed"] is False
    assert toggle_res["deliverable"]["completed_count"] == 0
    assert toggle_res["deliverable"]["is_completed"] is False


def test_station_pace_velocity_calculation(test_db):
    # Test on Day 15 of September (30 days total)
    test_date = "2026-09-15"

    # Initially 0 completed on sep26_hackerrank_15 (15 required)
    # Expected target pace on day 15 = (15 / 30) * 15 = 7.5
    # Deficit = 7.5 exercises behind
    velocity = kill_list_controller.get_station_pace_velocity("sep-2026", date_str=test_date, conn=test_db)
    assert velocity["is_behind"] is True
    assert "Pace Deficit" in velocity["status_text"]

    # Now simulate completing HackerRank exercises
    cursor = test_db.cursor()
    cursor.execute("UPDATE station_deliverable_progress SET completed_count = 10 WHERE deliverable_id = 'sep26_hackerrank_15'")
    cursor.execute("UPDATE station_deliverable_progress SET completed_count = 25 WHERE deliverable_id = 'sep26_math_diag'")
    cursor.execute("UPDATE station_deliverable_progress SET completed_count = 1 WHERE deliverable_id = 'sep26_sigg_setup'")
    cursor.execute("UPDATE station_deliverable_progress SET completed_count = 60 WHERE deliverable_id = 'sep26_german_anki'")
    cursor.execute("UPDATE station_deliverable_progress SET completed_count = 16 WHERE deliverable_id = 'sep26_phys_protein'")
    test_db.commit()

    # With completed >= target_pace across all:
    velocity_optimal = kill_list_controller.get_station_pace_velocity("sep-2026", date_str=test_date, conn=test_db)
    assert velocity_optimal["is_behind"] is False
    assert "Pace Velocity: Optimal" in velocity_optimal["status_text"]
