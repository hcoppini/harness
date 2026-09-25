"""Unit tests for Harness 3.0 Autonomous Academic Engine & Dynamic Study Block Governor."""

import sqlite3
import pytest
from datetime import datetime, timedelta
from app.db import init_db
from engine import workload_governor


@pytest.fixture
def academic_db(tmp_path):
    db_file = tmp_path / "test_academic.db"
    init_db(db_file)
    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


def test_subject_grade_vulnerability(academic_db):
    cursor = academic_db.cursor()
    # Insert low grades for History (GPA 2.5) and high for Maths (GPA 5.0)
    cursor.execute(
        "INSERT INTO tum_grade_entries (subject, semester, raw_input, numeric_value, weight, date) VALUES (?, ?, ?, ?, ?, ?)",
        ("Historia", 3, "2", 2.0, 2.0, "2026-09-10")
    )
    cursor.execute(
        "INSERT INTO tum_grade_entries (subject, semester, raw_input, numeric_value, weight, date) VALUES (?, ?, ?, ?, ?, ?)",
        ("Historia", 3, "3", 3.0, 1.0, "2026-09-15")
    )
    cursor.execute(
        "INSERT INTO tum_grade_entries (subject, semester, raw_input, numeric_value, weight, date) VALUES (?, ?, ?, ?, ?, ?)",
        ("Matematyka", 3, "5", 5.0, 3.0, "2026-09-12")
    )
    academic_db.commit()

    vulnerabilities = workload_governor.get_subject_vulnerabilities(conn=academic_db)
    assert "Historia" in vulnerabilities
    assert vulnerabilities["Historia"]["is_vulnerable"] is True
    assert vulnerabilities["Historia"]["gpa"] < 3.0

    assert "Matematyka" in vulnerabilities
    assert vulnerabilities["Matematyka"]["is_vulnerable"] is False
    assert vulnerabilities["Matematyka"]["gpa"] >= 5.0


def test_essay_classification_and_phased_synthesis():
    essay_hw = {
        "id": 1,
        "subject": "Język Polski",
        "title": "Rozprawka: Motyw cierpienia w Dziadach cz. III",
        "due_date": "2026-09-23",
        "notes": "Napisz esej argumentacyjny na minimum 400 słów",
        "priority": 1
    }
    classification = workload_governor.classify_obligation(essay_hw)
    assert classification["type"] == "essay"
    assert classification["is_writing_heavy"] is True

    # 2 days prior to deadline -> Drafting sprint
    plan_2d = workload_governor.generate_phased_study_action(essay_hw, days_left=2)
    assert "Drafting" in plan_2d["stage"] or "Draft" in plan_2d["focus"]
    assert plan_2d["is_school_dedicated"] is True

    # 1 day prior -> Polish & Review
    plan_1d = workload_governor.generate_phased_study_action(essay_hw, days_left=1)
    assert "Polish" in plan_1d["stage"] or "Review" in plan_1d["stage"] or "Final" in plan_1d["stage"]


def test_essay_due_in_two_days_commandeers_tomorrow_study_plan(academic_db):
    target_date = "2026-09-21"  # Monday
    essay_due = "2026-09-23"    # Wednesday (due in 2 days)

    cursor = academic_db.cursor()
    cursor.execute(
        "INSERT INTO homework_items (subject, title, due_date, notes, completed) VALUES (?, ?, ?, ?, 0)",
        ("Język Polski", "Esej: Romantyczna wizja narodu", essay_due, "Praca pisemna")
    )
    academic_db.commit()

    base_schedule = {
        "id": "A",
        "name": "Schedule A",
        "blocks": [
            {"time": "08:00 - 14:00", "focus": "TM1 Mechatronik Lessons", "type": "school"},
            {"time": "15:00 - 17:00", "focus": "SGH Library • Deep Work Sprint", "type": "deep_work", "activity": "LeetCode drills"},
            {"time": "18:00 - 19:30", "focus": "Legia Boxing", "type": "workout"}
        ]
    }

    adaptive = workload_governor.synthesize_adaptive_schedule(base_schedule, date_str=target_date, conn=academic_db)
    deep_work_blocks = [b for b in adaptive["blocks"] if b.get("type") == "deep_work"]
    assert len(deep_work_blocks) > 0

    sgh_block = deep_work_blocks[0]
    assert "Polski" in sgh_block["focus"] or "Esej" in sgh_block["focus"]
    assert sgh_block.get("is_school_dedicated") is True
    assert "draft" in sgh_block["activity"].lower() or "esej" in sgh_block["activity"].lower()


def test_heavy_load_weekend_study_block_injection(academic_db):
    # Saturday date
    saturday_str = "2026-09-26"

    cursor = academic_db.cursor()
    # 3 tests scheduled for the coming Monday and Tuesday
    cursor.execute(
        "INSERT INTO school_exams (subject, title, exam_date, scope, completed) VALUES (?, ?, ?, ?, 0)",
        ("Matematyka", "Sprawdzian: Ciągi", "2026-09-28", "Ciągi arytmetyczne")
    )
    cursor.execute(
        "INSERT INTO school_exams (subject, title, exam_date, scope, completed) VALUES (?, ?, ?, ?, 0)",
        ("Fizyka", "Sprawdzian: Termodynamika", "2026-09-29", "Zasady termodynamiki")
    )
    cursor.execute(
        "INSERT INTO school_exams (subject, title, exam_date, scope, completed) VALUES (?, ?, ?, ?, 0)",
        ("Historia", "Kartkówka: Powstanie", "2026-09-28", "Powstanie styczniowe")
    )
    academic_db.commit()

    base_saturday = {
        "id": "C_SAT",
        "name": "Schedule C (Saturday)",
        "blocks": [
            {"time": "09:00 - 10:30", "focus": "5k Recovery Run", "type": "recovery"},
            {"time": "11:00 - 13:00", "focus": "2h Timed Matura Paper", "type": "deep_work"},
            {"time": "14:00 - 22:00", "focus": "Free Afternoon & Social", "type": "free"}
        ]
    }

    adaptive_sat = workload_governor.synthesize_adaptive_schedule(base_saturday, date_str=saturday_str, conn=academic_db)
    # Check that a weekend study block was synthesized
    study_blocks = [b for b in adaptive_sat["blocks"] if "study_block" in b.get("type", "") or "Weekend Deep Work" in b.get("focus", "")]
    assert len(study_blocks) > 0
    assert any("Matematyka" in b["focus"] or "Fizyka" in b["focus"] for b in study_blocks)


def test_cruise_mode_preserves_standard_routine(academic_db):
    target_date = "2026-09-21"
    # Zero tests and zero homework
    base_schedule = {
        "id": "A",
        "name": "Schedule A",
        "blocks": [
            {"time": "15:00 - 17:00", "focus": "SGH Library • Deep Work Sprint", "type": "deep_work", "activity": "LeetCode drills and Math R"}
        ]
    }
    adaptive = workload_governor.synthesize_adaptive_schedule(base_schedule, date_str=target_date, conn=academic_db)
    sgh_block = adaptive["blocks"][0]
    assert "TUM Deep Work" in sgh_block["focus"]
    assert sgh_block["is_tum_roadmap"] is True
    assert sgh_block["is_school_dedicated"] is False
    assert sgh_block["deliverable"] is not None
