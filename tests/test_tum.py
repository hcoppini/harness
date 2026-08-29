"""Unit tests for TUM Roadmap: grade tracking, Matura metrics, and German progression."""

import sqlite3
import pytest
from app.db import init_db
from app.services import tum_service


@pytest.fixture
def test_db(tmp_path):
    db_file = tmp_path / "test_tum.db"
    init_db(db_file)
    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


def test_tum_overview_seeding_and_gpa(test_db):
    overview = tum_service.get_tum_overview(conn=test_db)
    assert overview["overall_gpa"] == 0.0
    assert len(overview["matura"]) >= 3
    assert len(overview["language"]) >= 4

    # Update some grades
    first_sem_grades = overview["semesters"][1]
    math_grade_id = first_sem_grades[0]["id"]
    tum_service.update_grade(math_grade_id, actual_grade=6.0, percentage=98.0, conn=test_db)

    it_grade_id = first_sem_grades[1]["id"]
    tum_service.update_grade(it_grade_id, actual_grade=5.5, percentage=92.0, conn=test_db)

    new_overview = tum_service.get_tum_overview(conn=test_db)
    assert new_overview["overall_gpa"] == 5.75
    assert new_overview["grades_under_four"] == 0


def test_matura_update(test_db):
    overview = tum_service.get_tum_overview(conn=test_db)
    math_r = [m for m in overview["matura"] if "Matematyka Rozszerzona" in m["subject"]][0]

    updated = tum_service.update_matura(math_r["id"], current_mock_percentage=84.0, notes="Scored 42/50 on CKE 2024 sample", conn=test_db)
    assert updated is True

    new_overview = tum_service.get_tum_overview(conn=test_db)
    updated_math_r = [m for m in new_overview["matura"] if "Matematyka Rozszerzona" in m["subject"]][0]
    assert updated_math_r["current_mock_percentage"] == 84.0


def test_german_ladder_transition(test_db):
    tum_service.get_tum_overview(conn=test_db)
    updated = tum_service.update_language_status("A2", "completed", conn=test_db)
    assert updated is True

    updated_b1 = tum_service.update_language_status("B1", "in_progress", conn=test_db)
    assert updated_b1 is True

    new_overview = tum_service.get_tum_overview(conn=test_db)
    a2_status = [l for l in new_overview["language"] if l["level"] == "A2"][0]["status"]
    b1_status = [l for l in new_overview["language"] if l["level"] == "B1"][0]["status"]
    assert a2_status == "completed"
    assert b1_status == "in_progress"


def test_metro_roadmap():
    roadmap = tum_service.get_metro_roadmap()
    assert "TUM" in roadmap["title"]
    assert len(roadmap["stations"]) >= 20

    # First station is Sep '26
    first_station = roadmap["stations"][0]
    assert first_station["id"] == "sep-2026"
    assert "Pure Syntax" in first_station["name"]
    assert "Academics" in first_station["deliverables"]

    # Test status update
    updated = tum_service.update_station_status("sep-2026", "active")
    assert updated is True

    # Test get all configs
    configs = tum_service.get_all_configs()
    assert "schedules" in configs
    assert "gym_routines" in configs
    assert "metro_roadmap" in configs
