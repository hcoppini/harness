"""Unit tests for Body/Life and Knowledge layers."""

import sqlite3
import pytest
from app.db import init_db
from app.services import body_service, knowledge_service


@pytest.fixture
def test_db(tmp_path):
    db_file = tmp_path / "test_body_know.db"
    init_db(db_file)
    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


def test_body_metric_and_workout_logging(test_db):
    # Log bodyweight
    metric = body_service.log_body_metric(
        weight_kg=69.5,
        calories_met=True,
        protein_met=True,
        notes="Clean bulk target hit",
        date_str="2026-08-29",
        conn=test_db,
    )
    assert metric["weight_kg"] == 69.5

    # Log workouts
    body_service.log_workout("boxing", "6 rounds sparring + heavy bag", intensity=8, date_str="2026-08-29", conn=test_db)
    body_service.log_workout("gym", "Upper body hypertrophy: bench 4x8, rows 4x10", intensity=7, date_str="2026-08-29", conn=test_db)

    summary = body_service.get_weekly_workout_summary(conn=test_db)
    assert summary["current_weight"] == 69.5
    assert summary["weekly_counts"]["boxing"] >= 1
    assert summary["weekly_counts"]["gym"] >= 1
    assert summary["progress_percentage"] > 0


def test_knowledge_crud(test_db):
    items = knowledge_service.get_all_knowledge(conn=test_db)
    assert len(items) >= 3

    # Add custom note
    new_note = knowledge_service.save_knowledge_item(
        title="Dynamic Programming: 0/1 Knapsack",
        category="algorithm",
        content="State: dp[i][w] = max value using first i items with weight limit w.",
        tags="algorithms, dp, matura",
        conn=test_db,
    )
    assert new_note["id"] is not None

    fetched = knowledge_service.get_all_knowledge(category="algorithm", conn=test_db)
    titles = [n["title"] for n in fetched]
    assert "Dynamic Programming: 0/1 Knapsack" in titles
