"""Unit tests for Daily Book Reading Protocol and AI Diary & Reflection Companion."""

import sqlite3
import pytest
from app.db import init_db
from app.services import book_service, diary_service, tum_service
from engine.tum_calculator import calculate_tum_aptitude_score


@pytest.fixture
def test_db(tmp_path):
    db_file = tmp_path / "test_book_diary.db"
    init_db(db_file)
    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


def test_book_service_lifecycle_and_pace(test_db):
    """Verifies monthly book target, required pace, and page logging."""
    status = book_service.get_active_book("2026-10-19", conn=test_db)
    assert status["book"] is not None
    book = status["book"]
    assert "Deep Work" in book["title"] or book["total_pages"] >= 300
    assert status["required_daily_pace"] > 0
    assert status["start_page_today"] == book["current_page"]

    # Log 25 pages read
    logged = book_service.log_reading_progress(
        end_page=25,
        start_page=0,
        book_id=book["id"],
        notes="Chapter 1 finished",
        date_str="2026-10-19",
        conn=test_db,
    )
    assert logged["pages_read_today"] == 25
    assert logged["current_page"] == 25
    assert logged["percent_completed"] > 0.0

    # Verify query again
    refreshed = book_service.get_active_book("2026-10-19", conn=test_db)
    assert refreshed["current_page"] == 25
    assert refreshed["pages_read_today"] == 25


def test_book_service_update_book_details(test_db):
    """Verifies updating book title, author, and page targets."""
    status = book_service.get_active_book("2026-10-19", conn=test_db)
    book_id = status["book"]["id"]

    updated = book_service.update_book_details(
        book_id=book_id,
        title="Dune",
        author="Frank Herbert",
        total_pages=412,
        current_page=50,
        conn=test_db,
    )
    assert updated["book"]["title"] == "Dune"
    assert updated["book"]["author"] == "Frank Herbert"
    assert updated["book"]["total_pages"] == 412
    assert updated["book"]["current_page"] == 50

    new_status = book_service.get_active_book("2026-10-19", conn=test_db)
    assert new_status["book"]["title"] == "Dune"
    assert new_status["start_page_today"] == 50


def test_diary_conversation_stances_and_persistence(test_db):
    """Verifies sending messages with Coach, Friend, and Mirror stances and retrieving history."""
    date_str = "2026-10-19"

    # Send message with coach stance
    conv_coach = diary_service.send_diary_message(
        user_message="Felt completely wiped after school, had zero focus for math.",
        stance="coach",
        date_str=date_str,
        conn=test_db,
    )
    assert conv_coach["stance"] == "coach"
    assert len(conv_coach["messages"]) == 2  # user + assistant
    assert conv_coach["messages"][0]["role"] == "user"
    assert conv_coach["messages"][1]["role"] == "assistant"
    assert conv_coach["messages"][1]["stance"] == "coach"

    # Send follow-up with friend stance
    conv_friend = diary_service.send_diary_message(
        user_message="I need a break tonight honestly.",
        stance="friend",
        date_str=date_str,
        conn=test_db,
    )
    assert len(conv_friend["messages"]) == 4  # 2 previous + 2 new
    assert conv_friend["messages"][3]["stance"] == "friend"

    # Retrieve conversation
    retrieved = diary_service.get_diary_conversation(date_str, conn=test_db)
    assert len(retrieved["messages"]) == 4


def test_diary_synthesis_into_daily_log_and_tasks(test_db):
    """Verifies synthesizing thoughts into structured reflections and auto-extracting actions."""
    date_str = "2026-10-19"

    # Seed thoughts
    diary_service.send_diary_message(
        user_message="I must solve 10 combinatorics problems tomorrow before gym. Need to talk to CS teacher about project.",
        stance="coach",
        date_str=date_str,
        conn=test_db,
    )

    synthesis = diary_service.synthesize_diary_session(date_str=date_str, auto_push_tasks=True, conn=test_db)
    assert synthesis["structured_entry"] is not None
    assert "Executive Diary Synthesis" in synthesis["structured_entry"]
    assert synthesis["actions_created"] >= 1

    # Verify daily_logs reflection was committed
    cursor = test_db.cursor()
    cursor.execute("SELECT reflection_worked FROM daily_logs WHERE date = ?", (date_str,))
    row = cursor.fetchone()
    assert row is not None
    assert "Executive Diary Synthesis" in row["reflection_worked"]


def test_tum_grade_entry_deduplication(test_db):
    """Verifies that duplicate grades cannot be logged or repeated in the ledger."""
    # Ensure subjects exist in database first
    tum_service.get_tum_overview(conn=test_db)

    # Add initial grade entry
    e1 = tum_service.add_grade_entry(
        subject="Fizyka",
        semester=1,
        raw_input="nb",
        weight=2.0,
        category="Sprawdzian",
        description="Termodynamika",
        date_str="2026-10-05",
        conn=test_db,
    )
    assert e1["entry"]["id"] is not None

    # Attempt to insert identical grade entry
    e2 = tum_service.add_grade_entry(
        subject="Fizyka",
        semester=1,
        raw_input="nb",
        weight=2.0,
        category="Sprawdzian",
        description="Termodynamika",
        date_str="2026-10-05",
        conn=test_db,
    )
    # Deduplication should return the existing entry id
    assert e2["entry"]["id"] == e1["entry"]["id"]

    # Verify overview does not repeat duplicate items
    overview = tum_service.get_tum_overview(conn=test_db)
    sem1 = overview["semesters"][1]
    fizyka = [s for s in sem1 if s["subject"] == "Fizyka"]
    assert len(fizyka) == 1
    # Check entries count
    assert len(fizyka[0]["entries"]) == 1


def test_tum_distance_to_goal_engine():
    """Verifies distance-to-goal points, German GPA gap, and subject drag calculations."""
    calc = calculate_tum_aptitude_score(gpa_pl=4.5, math_pl=4.0, cs_pl=4.5, lang_pl=5.0)
    assert "points_to_direct" in calc
    assert "points_to_interview" in calc
    assert "german_gpa_gap" in calc
    assert "primary_action" in calc
    assert "subject_drags" in calc
    assert calc["target_direct_points"] == 88.0
    assert calc["target_interview_points"] == 70.0
    assert calc["points_to_direct"] > 0
    # Math is 4.0 so it should be flagged as potential gain
    math_drags = [d for d in calc["subject_drags"] if d["subject"] == "Matematyka"]
    assert len(math_drags) == 1
    assert math_drags[0]["potential_gain_pts"] > 0
