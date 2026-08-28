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
