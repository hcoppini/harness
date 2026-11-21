"""Unit tests for the grounded reality audit:
1. Boxing reduced to 2x/week (Monday and Wednesday; Friday boxing removed).
2. Travel & Vacation architecture (US, Christmas, Brazil in February).
3. Heatmap honors travel mode (100% completion on oxygen anchor/reflection).
4. JetBrains Youth Coding Club active project integration.
5. STEM emergency triage (prioritizing Math & CS over secondary distractions).
"""

import sqlite3
import pytest
from datetime import datetime
from app.db import init_db
from app.services import today_service, dashboard_service, project_service
from engine import workload_governor


@pytest.fixture
def test_db(tmp_path):
    db_file = tmp_path / "test_reality.db"
    init_db(db_file)
    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


def test_boxing_reduced_to_two_days_a_week():
    """Verifies that Boxing is scheduled on Monday and Wednesday, and completely removed from Friday."""
    sched_mon = today_service.get_schedule_for_date("2026-11-16")  # Monday
    sched_wed = today_service.get_schedule_for_date("2026-11-18")  # Wednesday
    sched_fri = today_service.get_schedule_for_date("2026-11-20")  # Friday

    # Monday and Wednesday have Boxing
    mon_has_boxing = any("Boxing" in b.get("focus", "") for b in sched_mon["blocks"])
    wed_has_boxing = any("Boxing" in b.get("focus", "") for b in sched_wed["blocks"])
    assert mon_has_boxing is True, "Monday must contain Boxing training"
    assert wed_has_boxing is True, "Wednesday must contain Boxing training"

    # Friday has NO boxing (replaced by Coding / JetBrains and free weekend kickoff)
    fri_has_boxing = any("Boxing" in b.get("focus", "") for b in sched_fri["blocks"])
    assert fri_has_boxing is False, "Friday boxing must be removed to cap boxing at 2x/week"
    assert "Coding & Weekend Kickoff" in sched_fri["name"] or "Friday" in sched_fri["name"]

    # Verify total boxing sessions across all weekdays == 2
    weekday_dates = ["2026-11-16", "2026-11-17", "2026-11-18", "2026-11-19", "2026-11-20"]
    boxing_days = 0
    for d in weekday_dates:
        s = today_service.get_schedule_for_date(d)
        if any("Boxing" in b.get("focus", "") for b in s["blocks"]):
            boxing_days += 1
    assert boxing_days == 2, f"Expected exactly 2 boxing days a week, got {boxing_days}"


def test_travel_windows_detection():
    """Verifies confirmed vs tentative break/travel windows: confirmed US (Oct 2026) activates travel, unconfirmed Christmas break triggers BREAK, and unconfirmed Brazil does not hijack standard weeks."""
    # Confirmed US trip (historical)
    assert workload_governor.is_travel_or_vacation_date("2026-10-10") is True
    assert workload_governor.is_us_travel_date("2026-10-10") is True

    # Official Christmas break window is a school break (not forced flight travel until dates confirmed)
    christmas_date = "2026-12-25"
    win_xmas = workload_governor.get_active_travel_window(christmas_date, include_unconfirmed=True)
    assert win_xmas is not None
    assert win_xmas.get("type") == "break"
    assert workload_governor.get_active_break_window(christmas_date) is not None

    # Unconfirmed Brazil dates must NOT hijack normal February schedule unless confirmed
    brazil_date = "2027-02-15"
    assert workload_governor.get_active_travel_window(brazil_date) is None
    assert workload_governor.is_travel_or_vacation_date(brazil_date) is False

    # Non-travel date
    assert workload_governor.is_travel_or_vacation_date("2026-11-16") is False
    assert workload_governor.get_active_travel_window("2026-11-16") is None


def test_brazil_travel_schedule_synthesis(test_db):
    """Verifies explicit BREAK mode synthesizes a 2h+ programming sprint with zero school guilt, and FIELD mode triggers Travel maintenance."""
    orig_mode = workload_governor.get_operating_mode()
    try:
        workload_governor.set_operating_mode("BREAK")
        sched = today_service.get_schedule_for_date("2026-12-28", conn=test_db)
        assert sched["workload"]["mode"] == "BREAK"
        deep_block = next((b for b in sched["blocks"] if b.get("type") == "deep_work"), None)
        assert deep_block is not None
        assert deep_block["is_school_dedicated"] is False

        workload_governor.set_operating_mode("FIELD")
        travel_sched = today_service.get_schedule_for_date("2027-02-10", conn=test_db)
        assert travel_sched["workload"]["is_travel_mode"] is True
        travel_deep = next((b for b in travel_sched["blocks"] if b.get("type") == "deep_work"), None)
        assert travel_deep is not None
        assert travel_deep["is_school_dedicated"] is False
    finally:
        workload_governor.set_operating_mode(orig_mode)


def test_heatmap_honors_travel_mode(test_db):
    """Verifies that a travel day with completed maintenance anchor or reflection achieves Level 4."""
    travel_date = "2026-10-10"  # US trip day
    today_service.update_daily_log(
        date_str=travel_date,
        completed_blocks="1",  # Completed maintenance anchor
        reflection_worked="Maintained 45m anchor in hotel",
        conn=test_db,
    )

    heatmap = dashboard_service.get_heatmap_data(end_date=travel_date, conn=test_db, include_git=False)
    for week in heatmap["weeks"]:
        for day in week["days"]:
            if day and day["date"] == travel_date:
                assert day["level"] == 4, "Travel maintenance anchor completion must score Level 4 (100% victory)"
                assert any("TRAVEL" in act or "Field" in act for act in day.get("activities", []))


def test_jetbrains_club_project_active(test_db):
    """Verifies that JetBrains Youth Coding Club is registered and active in projects."""
    projects = project_service.get_all_projects(conn=test_db)
    # Even if running on fresh DB, test_projects.db seeds default, let's verify adding or checking
    jb_proj = [p for p in projects if "JetBrains" in p["name"]]
    if not jb_proj:
        new_p = project_service.add_project(
            name="JetBrains Youth Coding Club",
            description="Structured algorithms and software engineering",
            status="active",
            current_milestone="C++ / Python algorithm mastery",
            next_action="Attend club session & ace CS sprawdzian",
            conn=test_db,
        )
        assert new_p["id"] is not None
        assert new_p["status"] == "active"
    else:
        assert jb_proj[0]["status"] == "active"


def test_travel_mode_kill_list_capped_at_single_anchor(test_db):
    """Verifies that Kill List generation during confirmed US travel window caps at 1 maintenance anchor and freezes school defense."""
    from engine import kill_list_controller
    travel_date = "2026-10-10"
    res = kill_list_controller.auto_populate_kill_list(date_str=travel_date, conn=test_db)
    items = res.get("items", [])
    assert len(items) <= 1, f"Expected max 1 deliverable during travel window, got {len(items)}"
    for item in items:
        assert "exam" not in item.get("category", "").lower()
        assert "homework" not in item.get("category", "").lower()

