"""Unit tests for Layer 0 Dashboard: heatmap calculations, upcoming days schedule resolution, and summary stats."""

import sqlite3
import pytest
from datetime import datetime, timedelta
from app.db import init_db
from app.services import dashboard_service, today_service, body_service


@pytest.fixture
def test_db(tmp_path):
    """Creates an isolated temporary SQLite database for testing."""
    db_file = tmp_path / "test_dashboard.db"
    init_db(db_file)
    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


def test_heatmap_data_empty_db(test_db):
    """Verifies that heatmap data starts on August 30, 2026 and covers the 365-day full-year forward cycle."""
    today_str = "2026-08-30"  # Sunday
    heatmap = dashboard_service.get_heatmap_data(end_date=today_str, conn=test_db, include_git=False)
    
    assert "weeks" in heatmap
    assert len(heatmap["weeks"]) >= 52  # Full annual cycle (52-53 weeks)
    assert "total_contributions" in heatmap
    assert heatmap["total_contributions"] == 0
    assert heatmap["current_streak"] == 0
    assert "months" in heatmap
    assert len(heatmap["months"]) > 0
    assert heatmap["start_date"] == "2026-08-30"


def test_heatmap_activity_aggregation(test_db):
    """Verifies that checked boxes directly determine purple brightness levels (100% = level 4)."""
    today_str = "2026-08-30"  # Sunday Schedule C_SUN has 3 blocks
    
    # Add 3 completed tasks
    t1 = today_service.add_task("Solve 2 CS algorithms", "code", True, today_str, conn=test_db)
    t2 = today_service.add_task("Math past paper", "study", True, today_str, conn=test_db)
    t3 = today_service.add_task("German Anki review", "study", False, today_str, conn=test_db)
    today_service.toggle_task(t1["id"], conn=test_db)
    today_service.toggle_task(t2["id"], conn=test_db)
    today_service.toggle_task(t3["id"], conn=test_db)

    # Update daily log with all 3 Sunday routine blocks completed (3/3)
    today_service.update_daily_log(
        date_str=today_str,
        completed_blocks="0,1,2",
        reflection_worked="Focused on syntax",
        conn=test_db,
    )

    heatmap = dashboard_service.get_heatmap_data(end_date=today_str, conn=test_db, include_git=False)
    
    # 3 tasks checked + 3 routine blocks checked = 6 checked boxes
    assert heatmap["total_contributions"] == 6
    assert heatmap["current_streak"] >= 1

    # Find today's day cell in the heatmap weeks
    found_today = False
    for week in heatmap["weeks"]:
        for day in week["days"]:
            if day and day["date"] == today_str:
                found_today = True
                assert day["count"] == 6
                assert day["total_boxes"] == 6  # 3 routine blocks + 3 tasks
                assert day["level"] == 4  # 100% completion = Brightest Purple
                assert "activities" in day
                assert len(day["activities"]) >= 4
    assert found_today is True


def test_upcoming_days_resolution(test_db):
    """Verifies that upcoming 7 days are resolved correctly starting from tomorrow."""
    base_date = "2026-08-30"  # Sunday
    # Tomorrow is Monday 2026-08-31
    upcoming = dashboard_service.get_upcoming_days(days_count=7, start_date=base_date, conn=test_db)
    
    assert len(upcoming) == 7
    tomorrow = upcoming[0]
    assert tomorrow["date"] == "2026-08-31"
    assert tomorrow["day_name"] == "Monday"
    assert tomorrow["is_tomorrow"] is True
    assert "Schedule A" in tomorrow["schedule_name"]
    assert "Boxing" in tomorrow["key_highlight"]

    # Tuesday should have gym routine attached
    tuesday = upcoming[1]
    assert tuesday["day_name"] == "Tuesday"
    assert "Schedule B" in tuesday["schedule_name"]
    assert tuesday["gym_routine"] is not None
    assert "Posterior Chain" in tuesday["gym_routine"]["name"]

    # Saturday should be Schedule C
    saturday = upcoming[5]
    assert saturday["day_name"] == "Saturday"
    assert "Run" in saturday["key_highlight"] or "5k" in saturday["key_highlight"]


def test_dashboard_summary_structure(test_db):
    """Verifies dashboard summary payload contains all necessary UI widgets."""
    summary = dashboard_service.get_dashboard_summary(conn=test_db)
    
    assert "heatmap" in summary
    assert "upcoming" in summary
    assert "tum" in summary
    assert "body" in summary
    assert "projects" in summary
    assert "metrics" in summary


def test_heatmap_excludes_git_commits_from_boxes(test_db, monkeypatch):
    """Ensures git commits are never counted as checked boxes in heatmap."""
    today_str = "2026-08-30"
    
    # Mock git commits map returning commits for today
    monkeypatch.setattr(
        "app.services.github_service.get_daily_commits_map",
        lambda: {today_str: {"count": 10, "commits": [{"repo": "harness", "hash": "abc", "message": "test"}]}},
    )

    heatmap = dashboard_service.get_heatmap_data(end_date=today_str, conn=test_db)
    
    # Since no routine blocks or tasks are done, count and total should remain 0
    assert heatmap["total_contributions"] == 0
    for week in heatmap["weeks"]:
        for day in week["days"]:
            if day and day["date"] == today_str:
                assert day["count"] == 0
                assert day["level"] == 0
                assert not any("Git code commit" in act for act in day.get("activities", []))

