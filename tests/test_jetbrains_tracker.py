"""Tests for JetBrains Youth Coding Club Tracker."""

import json
from datetime import date, timedelta
from pathlib import Path
import pytest

from app.services import jetbrains_service


@pytest.fixture
def jb_env(tmp_path, monkeypatch):
    data_file = tmp_path / "jetbrains_tracker.json"
    monkeypatch.setattr(jetbrains_service, "TRACKER_FILE", data_file)
    return data_file


def test_default_jetbrains_status(jb_env):
    """Initial state reflects pending admin approval with 50% semester 2 target."""
    status = jetbrains_service.get_jetbrains_status()
    assert status["status"] == "pending_admin"
    assert status["problems_solved"] == 0
    assert status["problems_total"] >= 1
    assert status["pass_threshold_problems"] == 3  # >=50% of 6
    assert status["is_semester_2_eligible"] is False
    assert "Greek Letter" in status["group_name"] or "Pending" in status["group_name"]


def test_approve_admin_access_and_set_solved(jb_env):
    """Admin approval transitions status to active and solved counter updates eligibility."""
    jetbrains_service.approve_group_access("Omega Group", "Pavel (TA)")
    status = jetbrains_service.get_jetbrains_status()
    assert status["status"] == "active"
    assert status["group_name"] == "Omega Group"
    assert status["ta_name"] == "Pavel (TA)"

    # Solve 3 out of 6 problems (50%)
    res = jetbrains_service.set_problems_solved(3)
    assert res["problems_solved"] == 3
    assert res["progress_percentage"] == 50.0
    assert res["meets_problem_quota"] is True
    # Still needs interview
    assert res["is_semester_2_eligible"] is False

    # Complete interview
    res2 = jetbrains_service.toggle_interview(True)
    assert res2["interview_completed"] is True
    assert res2["is_semester_2_eligible"] is True


def test_deadline_and_penalty_calculation(jb_env):
    """Calculates days left until 40% penalty threshold."""
    today = date.today()
    in_5_days = (today + timedelta(days=5)).isoformat()
    past_2_days = (today - timedelta(days=2)).isoformat()

    jetbrains_service.update_jetbrains_status({
        "status": "active",
        "deadline_date": in_5_days,
        "problems_solved": 1,
        "problems_total": 6
    })

    status1 = jetbrains_service.get_jetbrains_status()
    assert status1["days_left"] == 5
    assert status1["penalty_active"] is False

    # Past deadline
    jetbrains_service.update_jetbrains_status({"deadline_date": past_2_days})
    status2 = jetbrains_service.get_jetbrains_status()
    assert status2["days_left"] <= 0
    assert status2["penalty_active"] is True
