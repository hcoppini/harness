"""Unit tests for Today layer: task CRUD, rollover mechanics, and scratchpad logging."""

import os
import sqlite3
import pytest
from datetime import datetime, timedelta
from app.db import init_db
from app.services import today_service


@pytest.fixture
def test_db(tmp_path):
    """Creates an isolated temporary SQLite database for testing."""
    db_file = tmp_path / "test_harness.db"
    init_db(db_file)
    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


def test_add_and_get_tasks(test_db):
    today_str = datetime.now().strftime("%Y-%m-%d")
    task = today_service.add_task(
        title="Maths Rozszerzona: 5 combinatorics problems",
        category="study",
        is_tum=True,
        date_str=today_str,
        conn=test_db,
    )
    assert task["id"] is not None
    assert task["is_tum"] is True
    assert task["completed"] is False

    tasks = today_service.get_today_tasks(date_str=today_str, conn=test_db)
    assert len(tasks) == 1
    assert tasks[0]["title"] == "Maths Rozszerzona: 5 combinatorics problems"
    assert tasks[0]["is_tum"] is True


def test_toggle_task(test_db):
    today_str = datetime.now().strftime("%Y-%m-%d")
    task = today_service.add_task("Boxing training 60min", "fitness", False, today_str, conn=test_db)
    task_id = task["id"]

    res = today_service.toggle_task(task_id, conn=test_db)
    assert res["completed"] is True
    assert res["completed_at"] is not None

    res2 = today_service.toggle_task(task_id, conn=test_db)
    assert res2["completed"] is False
    assert res2["completed_at"] is None


def test_rollover_tasks(test_db):
    yesterday_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    today_str = datetime.now().strftime("%Y-%m-%d")

    # Add an uncompleted task yesterday
    task1 = today_service.add_task("Unfinished HackerRank problem", "code", False, yesterday_str, conn=test_db)
    # Add a completed task yesterday
    task2 = today_service.add_task("Completed English grammar", "study", False, yesterday_str, conn=test_db)
    today_service.toggle_task(task2["id"], conn=test_db)

    # Perform rollover to today
    rolled_count = today_service.rollover_tasks(target_date_str=today_str, conn=test_db)
    assert rolled_count == 1

    # Check today's tasks
    today_tasks = today_service.get_today_tasks(date_str=today_str, conn=test_db)
    assert len(today_tasks) == 1
    assert today_tasks[0]["id"] == task1["id"]
    assert today_tasks[0]["rollover_count"] == 1
    assert today_tasks[0]["date"] == today_str


def test_daily_log_scratchpad(test_db):
    today_str = datetime.now().strftime("%Y-%m-%d")
    log = today_service.get_daily_log(today_str, conn=test_db)
    assert log["date"] == today_str
    assert log["scratchpad"] == ""

    updated = today_service.update_daily_log(
        date_str=today_str,
        scratchpad="Focus today: pure recursion without helper libraries.",
        wake_time="06:30",
        sleep_time="22:45",
        reflection_worked="Completed all math sets.",
        conn=test_db,
    )
    assert "pure recursion" in updated["scratchpad"]
    assert updated["wake_time"] == "06:30"
    assert updated["reflection_worked"] == "Completed all math sets."


def test_schedule_and_gym_resolution():
    # 2026-08-31 is a Monday -> Schedule A
    sched_mon = today_service.get_schedule_for_date("2026-08-31")
    assert "Boxing" in sched_mon["name"]
    assert len(sched_mon["blocks"]) >= 5

    # 2026-09-01 is a Tuesday -> Schedule B & Tuesday Gym Routine
    sched_tue = today_service.get_schedule_for_date("2026-09-01")
    assert "Gym & TUM Sprint" in sched_tue["name"]

    gym_tue = today_service.get_gym_routine_for_date("2026-09-01")
    assert gym_tue is not None
    assert "Posterior Chain" in gym_tue["name"]
    assert len(gym_tue["exercises"]) == 6


def test_get_tasks_for_different_dates(test_db):
    date1 = "2026-09-02"
    date2 = "2026-09-03"

    t1 = today_service.add_task("Math test prep", "study", True, date1, conn=test_db)
    t2 = today_service.add_task("English vocabulary", "study", False, date2, conn=test_db)

    tasks1 = today_service.get_today_tasks(date1, conn=test_db)
    tasks2 = today_service.get_today_tasks(date2, conn=test_db)

    assert len(tasks1) == 1
    assert tasks1[0]["id"] == t1["id"]
    assert tasks1[0]["title"] == "Math test prep"

    assert len(tasks2) == 1
    assert tasks2[0]["id"] == t2["id"]
    assert tasks2[0]["title"] == "English vocabulary"


def test_historical_daily_log_isolation(test_db):
    past_date = "2026-09-01"
    today_date = "2026-09-03"

    # Update past date daily log (e.g. check routine block 0 and exercise 1)
    past_updated = today_service.update_daily_log(
        date_str=past_date,
        completed_blocks="0,1",
        completed_exercises="1",
        scratchpad="Past scratchpad notes",
        conn=test_db,
    )
    assert past_updated["date"] == past_date
    assert past_updated["completed_blocks"] == "0,1"
    assert past_updated["completed_exercises"] == "1"

    # Verify today's log is completely unaffected and distinct
    today_log = today_service.get_daily_log(today_date, conn=test_db)
    assert today_log["date"] == today_date
    assert today_log["completed_blocks"] == ""
    assert today_log["completed_exercises"] == ""
    assert today_log["scratchpad"] == ""

    # Check that retrieving past date log returns the persisted checks
    retrieved_past = today_service.get_daily_log(past_date, conn=test_db)
    assert retrieved_past["completed_blocks"] == "0,1"
    assert retrieved_past["completed_exercises"] == "1"
    assert retrieved_past["scratchpad"] == "Past scratchpad notes"


