"""Unit tests for TUM Roadmap: grade tracking, Matura metrics, and German progression."""

import json
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
    orig_file = tum_service.DATA_DIR / "metro_roadmap.json"
    with open(orig_file, "r", encoding="utf-8") as f:
        orig_content = f.read()

    try:
        roadmap = tum_service.get_metro_roadmap()
        assert "TUM" in roadmap["title"]
        assert len(roadmap["stations"]) >= 20

        # Kickoff station is index 0, Sep '26 (Pure Syntax) is index 1
        first_station = roadmap["stations"][0]
        assert first_station["id"] == "kickoff-2026"
        assert "Class 3 Kickoff" in first_station["name"]

        sep_station = [s for s in roadmap["stations"] if s["id"] == "sep-2026"][0]
        assert "Pure Syntax" in sep_station["name"]
        assert "Academics" in sep_station["deliverables"]

        # Test status update
        updated = tum_service.update_station_status("sep-2026", "active")
        assert updated is True

        # Reset completed deliverables for test isolation
        for s in roadmap["stations"]:
            if s["id"] == "sep-2026":
                s["completed_deliverables"] = []
        with open(orig_file, "w", encoding="utf-8") as f:
            json.dump(roadmap, f)

        # Test deliverable toggling checklist
        deliv_keys = list(sep_station["deliverables"].keys())
        assert len(deliv_keys) > 0

        # Toggle one on
        res = tum_service.toggle_station_deliverable("sep-2026", deliv_keys[0])
        assert res["success"] is True
        assert res["is_checked"] is True
        assert deliv_keys[0] in res["completed_deliverables"]

        # Toggle all deliverables on to verify automatic completion
        for k in deliv_keys[1:]:
            res = tum_service.toggle_station_deliverable("sep-2026", k)
            assert res["success"] is True

        assert res["station_completed"] is True
        assert res["station_status"] == "completed"

        # Toggle one off to verify reversion
        res_off = tum_service.toggle_station_deliverable("sep-2026", deliv_keys[0])
        assert res_off["is_checked"] is False
        assert res_off["station_completed"] is False
        assert res_off["station_status"] == "active"

        # Test get all configs
        configs = tum_service.get_all_configs()
        assert "schedules" in configs
        assert "gym_routines" in configs
        assert "metro_roadmap" in configs
    finally:
        with open(orig_file, "w", encoding="utf-8") as f:
            f.write(orig_content)


def test_metro_roadmap_sqlite_deliverable_overlay(test_db):
    """Verify get_metro_roadmap overlays live SQLite deliverable progress without auto-seeding unvisited stations."""
    cursor = test_db.cursor()
    cursor.execute(
        """
        INSERT INTO station_deliverable_progress
        (station_id, stream, title, total_required, completed_count, unit_label, is_completed)
        VALUES ('nov-2026', 'Physical', 'Consistency streak', 30, 7, 'days', 0)
        """
    )
    test_db.commit()

    roadmap = tum_service.get_metro_roadmap(conn=test_db)
    nov_station = next(s for s in roadmap["stations"] if s["id"] == "nov-2026")
    phys_counts = nov_station.get("deliverable_counts", {}).get("Physical")
    assert phys_counts is not None
    assert phys_counts["count"] == 7
    assert phys_counts["total"] == 7  # Reconciled with leveled Nov 24-30 station ceiling


def test_metro_roadmap_sidequests_optional_and_toggleable():
    """Optional Sidequests render cleanly per station and never affect required station completion."""
    orig_file = tum_service.DATA_DIR / "metro_roadmap.json"
    orig_content = orig_file.read_text(encoding="utf-8")
    try:
        roadmap = tum_service.get_metro_roadmap()
        nov_station = next(s for s in roadmap["stations"] if s["id"] == "nov-2026")
        sidequests = nov_station.get("sidequests", [])
        assert len(sidequests) >= 2
        sq_id = sidequests[0]["id"]

        res_on = tum_service.toggle_station_sidequest("nov-2026", sq_id)
        assert res_on["success"] is True
        assert res_on["is_completed"] is True
        assert sq_id in res_on["completed_sidequests"]

        res_off = tum_service.toggle_station_sidequest("nov-2026", sq_id)
        assert res_off["success"] is True
        assert res_off["is_completed"] is False
        assert sq_id not in res_off["completed_sidequests"]
    finally:
        orig_file.write_text(orig_content, encoding="utf-8")

