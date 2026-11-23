"""Tests for the Nov 24 Final Leveling, weekly 40-exercise math cadence, gym/boxing schedule, Vulcan dedup, and timetable freshness."""

import sqlite3
from datetime import datetime, timedelta
import pytest

from app.db import init_db
from app.services import leveling_service, school_service, today_service, vulcan_service
from engine import kill_list_controller, workload_governor


@pytest.fixture
def test_db(tmp_path, monkeypatch):
    db_file = tmp_path / "test_leveling.db"
    init_db(db_file)
    op_file = tmp_path / "operating_mode.json"
    monkeypatch.setattr(leveling_service, "OPERATING_MODE_FILE", op_file)
    monkeypatch.setattr(workload_governor, "OPERATING_MODE_FILE", op_file)
    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


def test_monday_and_tuesday_online_math_and_gym_schedule(test_db):
    """Verifies Mon 15:00 online Matura math + preserved Boxing, Tue no-Religia 14:15 end + afternoon Gym + 19:00 online Math, and 40 exercises/wk split."""
    # Monday Nov 23 / Nov 30
    mon = today_service.get_schedule_for_date("2026-11-30", conn=test_db)
    mon_math = next((b for b in mon["blocks"] if "15:00" in b["time"] and b.get("type") == "class"), None)
    mon_boxing = next((b for b in mon["blocks"] if b.get("type") == "training" and "Boxing" in b["focus"]), None)
    assert mon_math is not None, "Monday must include 15:00 Online Matura Math class at home"
    assert mon_math.get("protected") is True
    assert mon_boxing is not None and "17:20" in mon_boxing["time"], "Monday Boxing must remain protected"

    # Tuesday Nov 24
    tue = today_service.get_schedule_for_date("2026-11-24", conn=test_db)
    tue_school = next((b for b in tue["blocks"] if b.get("type") == "school"), None)
    tue_gym = next((b for b in tue["blocks"] if "Gym" in b["focus"]), None)
    tue_math = next((b for b in tue["blocks"] if "19:00" in b["time"] and b.get("type") == "class"), None)
    assert tue_school is not None and "14:15" in tue_school["time"], "Tuesday school must end at 14:15 (no Religia)"
    assert tue_gym is not None and "15:30" in tue_gym["time"], "Tuesday must fit afternoon Gym Day 1"
    assert tue_math is not None and tue_math.get("protected") is True, "Tuesday must include 19:00 Online Math class"

    # Verify weekly math split sums to exactly 40 exercises across Tue-Sat
    week_dates = [
        "2026-11-23",  # Mon: 0
        "2026-11-24",  # Tue: 5
        "2026-11-25",  # Wed: 8
        "2026-11-26",  # Thu: 9
        "2026-11-27",  # Fri: 9
        "2026-11-28",  # Sat: 9
        "2026-11-29",  # Sun: 0
    ]
    slices = [leveling_service.get_weekly_math_slice(d)["daily_target"] for d in week_dates]
    assert slices == [0, 5, 8, 9, 9, 9, 0]
    assert sum(slices) == 40

    # Verify 2x Boxing (Mon/Wed) + 2x Gym (Tue/Thu)
    boxing_days = sum(
        1 for d in week_dates
        if any("Boxing" in b.get("focus", "") for b in today_service.get_schedule_for_date(d, conn=test_db)["blocks"])
    )
    gym_days = sum(
        1 for d in week_dates
        if any("Gym" in b.get("focus", "") for b in today_service.get_schedule_for_date(d, conn=test_db)["blocks"])
    )
    assert boxing_days == 2
    assert gym_days == 2


def test_rebase_to_today_clears_ghost_debt_and_preserves_grades(test_db):
    """TD-06 & TD-07: rebase_to_today resets pace to 0.0 deficit without touching any grades."""
    cur = test_db.cursor()
    # Insert grades that must remain 100% untouched
    cur.execute(
        """
        INSERT INTO tum_grade_entries (subject, semester, raw_input, numeric_value, weight, category, description, date, counts_in_average)
        VALUES ('Matematyka', 1, '1', 1.0, 1.0, 'Sprawdzian', 'geometria płaska', '2026-10-26', 1)
        """
    )
    # Insert ghost debt: unclosed past station, junk kill_list item, expired homework, duplicate exams
    cur.execute(
        """
        INSERT INTO station_deliverable_progress (deliverable_id, station_id, stream, title, total_required, completed_count, unit_label, is_completed)
        VALUES
            ('sep26_ghost', 'sep-2026', 'german', 'Old German', 100, 20, 'words', 0),
            ('nov2026_acad', 'nov-2026', 'academics', 'Old Nov', 18, 0, 'sessions', 0)
        """
    )
    cur.execute(
        """
        INSERT INTO kill_list_items (id, date, category, title, action_type, target_path, target_spec, completed)
        VALUES ('k_junk', '2026-09-12', 'Raw CS', 'Cross-sync test', 'workspace', 'c:/Users/heito/Desktop/harness', 'tests', 1)
        """
    )
    cur.execute(
        """
        INSERT INTO homework_items (subject, title, due_date, completed, source, priority)
        VALUES ('Matematyka', '4.90', '2026-09-18', 0, 'vulcan', 1)
        """
    )
    cur.execute(
        """
        INSERT INTO school_exams (subject, title, exam_date, scope, completed)
        VALUES
            ('Język niemiecki', 'Kartkówka: Pogoda', '2026-11-20', '', 1),
            ('Język niemiecki', 'Kartkówka: Pogoda!', '2026-11-20', '', 1),
            ('Informatyka', 'Sprawdzian: NWD', '2026-11-23', '', 0),
            ('Matematyka', 'Sprawdzian: trygonometria', '2026-11-27', '', 0)
        """
    )
    test_db.commit()

    res = leveling_service.rebase_to_today(
        baseline_date="2026-11-24",
        active_station_id="nov-2026",
        conn=test_db,
    )
    assert res["grades_untouched"] is True
    assert res["past_deliverables_closed"] >= 1
    assert cur.execute(
        "SELECT COUNT(*) FROM station_deliverable_progress WHERE station_id IN ('kickoff-2026', 'sep-2026', 'oct-2026') AND is_completed = 0"
    ).fetchone()[0] == 0
    assert res["junk_kill_items_removed"] == 1
    assert res["expired_homework_pruned"] == 1
    assert res["duplicate_exams_removed"] == 1
    assert res["past_exams_completed"] == 1
    assert res["material_deficit_seeded"] == 7

    # Grades must be 100% untouched
    grades = cur.execute("SELECT subject, raw_input, numeric_value FROM tum_grade_entries").fetchall()
    assert len(grades) == 1
    assert grades[0]["raw_input"] == "1"

    # Pace velocity on baseline date (Nov 24) must be 0.0 deficit / optimal!
    pace = kill_list_controller.get_station_pace_velocity(
        station_id="nov-2026",
        date_str="2026-11-24",
        conn=test_db,
    )
    assert pace["baseline_date"] == "2026-11-24"
    assert pace["is_behind"] is False
    assert pace["max_deficit"] == 0.0

    # Switching operating mode must preserve station_baselines
    workload_governor.set_operating_mode("SURGE_RECOVERY")
    assert leveling_service.get_station_baseline_date("nov-2026") == "2026-11-24"


def test_vulcan_canonical_exam_deduplication(test_db, monkeypatch):
    """TD-11: Vulcan sync deduplicates exams even when punctuation or casing differs."""
    payload = {
        "exams": [
            {"subject": "Język niemiecki", "title": "Kartkówka: Pogoda", "exam_date": "2026-12-01", "scope": ""},
            {"subject": "Język niemiecki", "title": "Kartkówka - Pogoda!", "exam_date": "2026-12-01", "scope": "Wetter"},
        ],
        "homework": [
            {"subject": "Fizyka", "title": "Prezentacja: Topnienie.", "due_date": "2026-12-05", "priority": 1},
            {"subject": "Fizyka", "title": "Prezentacja; topnienie", "due_date": "2026-12-05", "priority": 1},
        ],
        "grades": [],
    }
    monkeypatch.setattr(vulcan_service, "_get_demo_school_data", lambda d: payload)
    vulcan_service.sync_vulcan_data(client_date="2026-11-24", conn=test_db)

    exams = test_db.execute("SELECT * FROM school_exams WHERE exam_date = '2026-12-01'").fetchall()
    hw = test_db.execute("SELECT * FROM homework_items WHERE due_date = '2026-12-05'").fetchall()
    assert len(exams) == 1
    assert len(hw) == 1


def test_timetable_staleness_helper():
    """TD-11: Detects stale (>7d) vs fresh cached timetables."""
    stale = {"fetched_at": (datetime.now() - timedelta(days=10)).isoformat()}
    fresh = {"fetched_at": (datetime.now() - timedelta(days=1)).isoformat()}
    assert school_service._is_cached_plan_stale(stale) is True
    assert school_service._is_cached_plan_stale(fresh) is False
    assert school_service._is_cached_plan_stale({}) is True
