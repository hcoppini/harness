"""
JetBrains Youth Coding Club Service (v1.0)
Tracks Codeforces weekly contests, prerecorded lectures, 2-week penalty deadline,
and Semester 2 advancement criteria (>= 50% solved problems per contest + 1 TA interview).
"""

import json
import math
import os
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, Optional

from app.db import DATA_DIR

TRACKER_FILE = DATA_DIR / "jetbrains_tracker.json"

DEFAULT_TRACKER_DATA: Dict[str, Any] = {
    "status": "pending_admin",  # "pending_admin" | "active"
    "group_name": "Greek Letter Group (Pending Admin)",
    "ta_name": "Assigned upon group join",
    "current_topic": "Foundations & Codeforces Contest 1",
    "current_contest": "Contest #1",
    "codeforces_url": "https://codeforces.com/group/",
    "lecture_url": "",
    "release_date": "2026-11-19",
    "deadline_date": "2026-12-03",
    "problems_total": 6,
    "problems_solved": 0,
    "interview_completed": False,
    "notes": "Rules: New topic every Thursday. 2 weeks per contest. Solve >=50% + complete 1 TA interview to move to Semester 2.",
}


def _load_tracker() -> Dict[str, Any]:
    if not TRACKER_FILE.exists():
        _save_tracker(DEFAULT_TRACKER_DATA)
        return dict(DEFAULT_TRACKER_DATA)
    try:
        with open(TRACKER_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            merged = dict(DEFAULT_TRACKER_DATA)
            merged.update(data)
            return merged
    except Exception:
        return dict(DEFAULT_TRACKER_DATA)


def _save_tracker(data: Dict[str, Any]) -> None:
    TRACKER_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(TRACKER_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_jetbrains_status(ref_date: Optional[date] = None) -> Dict[str, Any]:
    """Returns enriched status of JetBrains Youth Coding Club tracking."""
    data = _load_tracker()
    today = ref_date or date.today()

    total = max(1, int(data.get("problems_total", 6)))
    solved = max(0, int(data.get("problems_solved", 0)))
    pass_threshold = math.ceil(total * 0.5)

    progress_pct = round((solved / total) * 100, 1)
    meets_problem_quota = solved >= pass_threshold
    interview_done = bool(data.get("interview_completed", False))

    deadline_str = data.get("deadline_date", "")
    days_left = 0
    penalty_active = False
    if deadline_str:
        try:
            dl_date = datetime.strptime(deadline_str, "%Y-%m-%d").date()
            delta = (dl_date - today).days
            days_left = delta
            if delta < 0:
                penalty_active = True
        except Exception:
            pass

    data["problems_total"] = total
    data["problems_solved"] = solved
    data["pass_threshold_problems"] = pass_threshold
    data["progress_percentage"] = progress_pct
    data["meets_problem_quota"] = meets_problem_quota
    data["interview_completed"] = interview_done
    data["days_left"] = days_left
    data["penalty_active"] = penalty_active
    data["is_semester_2_eligible"] = meets_problem_quota and interview_done

    return data


def update_jetbrains_status(updates: Dict[str, Any]) -> Dict[str, Any]:
    """Applies partial updates to tracker data."""
    current = _load_tracker()
    current.update(updates)
    _save_tracker(current)
    return get_jetbrains_status()


def approve_group_access(group_name: str, ta_name: str = "") -> Dict[str, Any]:
    """Transitions tracker from pending_admin to active upon Codeforces approval."""
    return update_jetbrains_status({
        "status": "active",
        "group_name": group_name or "Assigned Group",
        "ta_name": ta_name or "Assigned TA",
    })


def set_problems_solved(count: int) -> Dict[str, Any]:
    """Updates solved problem count for the active contest."""
    return update_jetbrains_status({"problems_solved": max(0, count)})


def toggle_interview(completed: bool) -> Dict[str, Any]:
    """Toggles solution interview completion."""
    return update_jetbrains_status({"interview_completed": bool(completed)})
