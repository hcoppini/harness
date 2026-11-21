"""Test HarnessAPI integration for JetBrains Youth Coding Club."""

from app.api import HarnessAPI
from app.services import jetbrains_service


def test_api_jetbrains_methods(tmp_path, monkeypatch):
    data_file = tmp_path / "test_jetbrains.json"
    monkeypatch.setattr(jetbrains_service, "TRACKER_FILE", data_file)

    api = HarnessAPI()

    # 1. Get default status
    status = api.get_jetbrains_tracker()
    assert status["status"] == "pending_admin"
    assert status["problems_solved"] == 0

    # 2. Approve admin
    approved = api.approve_jetbrains_admin("Epsilon Group", "Livia (TA)")
    assert approved["status"] == "active"
    assert approved["group_name"] == "Epsilon Group"
    assert approved["ta_name"] == "Livia (TA)"

    # 3. Increment solved problems
    res_solved = api.set_jetbrains_problems_solved(4)
    assert res_solved["problems_solved"] == 4
    assert res_solved["meets_problem_quota"] is True

    # 4. Toggle interview
    res_interview = api.toggle_jetbrains_interview(True)
    assert res_interview["interview_completed"] is True
    assert res_interview["is_semester_2_eligible"] is True
