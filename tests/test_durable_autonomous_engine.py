"""
Unit tests for the 2-Year Durable Autonomous Harness Engine:
1. Dynamic Station Resolver across 2026-2028 timeline.
2. Autonomous US Travel Protocol (Oct 4–18, 2026).
3. 5-Stage Progressive Exam Preparation Syllabus & T-0 Post-Exam Suppression.
4. Non-Defense SGH Library TUM Roadmap Embedding.
5. Auto-seeding 2-year Metro deliverables from roadmap.
"""

import sqlite3
import pytest
from datetime import datetime, date

from app.db import init_db
from engine import workload_governor, kill_list_controller
from app.services import today_service, vulcan_service, homework_service


@pytest.fixture
def clean_db(tmp_path):
    db_file = tmp_path / "test_durable.db"
    init_db(db_file)
    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


def test_dynamic_station_resolver():
    """Verifies that get_active_station_id correctly resolves all dates across 2026-2028."""
    # Class 3 Liceum (2026-2027)
    assert workload_governor.get_active_station_id("2026-08-15") == "kickoff-2026"
    assert workload_governor.get_active_station_id("2026-09-15") == "sep-2026"
    assert workload_governor.get_active_station_id("2026-10-01") == "oct-2026"
    assert workload_governor.get_active_station_id("2026-11-20") == "nov-2026"
    assert workload_governor.get_active_station_id("2026-12-31") == "dec-2026"
    assert workload_governor.get_active_station_id("2027-01-10") == "jan-2027"
    assert workload_governor.get_active_station_id("2027-02-14") == "feb-2027"
    assert workload_governor.get_active_station_id("2027-03-01") == "mar-2027"
    assert workload_governor.get_active_station_id("2027-04-15") == "apr-2027"
    assert workload_governor.get_active_station_id("2027-05-01") == "may-2027"
    assert workload_governor.get_active_station_id("2027-06-30") == "jun-2027"

    # Combined Summer 2027 station
    assert workload_governor.get_active_station_id("2027-07-04") == "jul-aug-2027"
    assert workload_governor.get_active_station_id("2027-08-20") == "jul-aug-2027"

    # Class 4 Liceum & Matura Year (2027-2028)
    assert workload_governor.get_active_station_id("2027-09-01") == "sep-2027"
    assert workload_governor.get_active_station_id("2027-10-15") == "oct-2027"
    assert workload_governor.get_active_station_id("2027-11-10") == "nov-2027"
    assert workload_governor.get_active_station_id("2027-12-25") == "dec-2027"
    assert workload_governor.get_active_station_id("2028-01-15") == "jan-2028"
    assert workload_governor.get_active_station_id("2028-02-28") == "feb-2028"
    assert workload_governor.get_active_station_id("2028-03-15") == "mar-2028"
    assert workload_governor.get_active_station_id("2028-04-10") == "apr-2028"
    assert workload_governor.get_active_station_id("2028-05-05") == "may-2028"
    assert workload_governor.get_active_station_id("2028-06-20") == "jun-2028"
    assert workload_governor.get_active_station_id("2028-07-08") == "jul-2028"
    assert workload_governor.get_active_station_id("2028-08-15") == "jul-2028"


def test_us_travel_date_detection():
    """Verifies that is_us_travel_date accurately detects October 4th to 18th, 2026."""
    assert workload_governor.is_us_travel_date("2026-10-03") is False
    assert workload_governor.is_us_travel_date("2026-10-04") is True
    assert workload_governor.is_us_travel_date("2026-10-10") is True
    assert workload_governor.is_us_travel_date("2026-10-18") is True
    assert workload_governor.is_us_travel_date("2026-10-19") is False

    # Supports datetime and date objects
    assert workload_governor.is_us_travel_date(datetime(2026, 10, 5, 14, 0)) is True
    assert workload_governor.is_us_travel_date(date(2026, 10, 12)) is True


def test_us_travel_mode_schedule_and_exam_freezing(clean_db):
    """
    During US trip (Oct 4–18):
    1. Warsaw timetable/commute is replaced by flexible US hotel deep work.
    2. Scheduled school exams are travel-excused and do NOT trigger Surge mode.
    """
    travel_date = "2026-10-06"  # Tuesday

    # Insert an exam scheduled during the trip
    cursor = clean_db.cursor()
    cursor.execute(
        """
        INSERT INTO school_exams (subject, title, exam_date, scope, completed)
        VALUES ('Fizyka', 'Sprawdzian: Termodynamika', '2026-10-08', 'Ciepło właściwe', 0)
        """
    )
    clean_db.commit()

    # Workload analysis during trip
    analysis = workload_governor.get_workload_analysis(travel_date, conn=clean_db)
    assert analysis["is_us_travel_mode"] is True
    assert analysis["mode"] == "TRAVEL"
    assert analysis["badge_class"] == "travel"

    # Verify that the exam was marked travel-excused and did not cause Surge mode
    all_exams = analysis["all_exams"]
    assert len(all_exams) == 1
    assert all_exams[0]["is_travel_excused"] is True
    assert analysis["workload_score"] <= 2.5

    # Synthesize schedule for date
    sched = today_service.get_schedule_for_date(travel_date, conn=clean_db)
    blocks = sched["blocks"]

    # Verify absence of Warsaw school and presence of US Hotel Deep Work
    assert not any("Liceum" in b.get("focus", "") for b in blocks)
    hotel_block = next((b for b in blocks if "US Hotel Deep Work" in b.get("focus", "")), None)
    assert hotel_block is not None
    assert hotel_block["type"] == "deep_work"
    assert hotel_block["is_tum_roadmap"] is True
    assert hotel_block.get("is_us_travel") is True
    assert "deliverable" in hotel_block


def test_phased_exam_preparation_syllabus():
    """Verifies the 5-stage progressive exam preparation syllabus."""
    exam = {
        "subject": "Matematyka R",
        "title": "Sprawdzian: Ciągi Liczbowe i Granice",
        "scope": "Ciągi arytmetyczne, geometryczne, granice ciągów (zad. 4.1-4.30)",
    }

    # T-7 (Stage 1: Scope & Theorem Mapping)
    s1 = workload_governor.generate_phased_study_action(exam, days_left=7)
    assert "Stage 1" in s1["stage"]
    assert "Scope & Theorem Mapping" in s1["stage"]
    assert "concept/theorem map" in s1["activity"]
    assert s1["is_school_dedicated"] is True

    # T-4 (Stage 2: Foundational Problem Sets & Error Bank)
    s2 = workload_governor.generate_phased_study_action(exam, days_left=4)
    assert "Stage 2" in s2["stage"]
    assert "Foundational Problem Sets" in s2["stage"]
    assert "error bank" in s2["activity"]
    assert s2["is_school_dedicated"] is True

    # T-2 (Stage 3: Hard & Past-Paper Drills)
    s3 = workload_governor.generate_phased_study_action(exam, days_left=2)
    assert "Stage 3" in s3["stage"]
    assert "Hard & Past-Paper Drills" in s3["stage"]
    assert "unassisted CKE/operon" in s3["activity"]
    assert s3["is_school_dedicated"] is True

    # T-1 (Stage 4: Timed Mock Simulation & Rapid Blitz)
    s4 = workload_governor.generate_phased_study_action(exam, days_left=1)
    assert "Stage 4" in s4["stage"]
    assert "Timed Mock Simulation" in s4["stage"]
    assert "timed" in s4["activity"] and "mock exam simulation" in s4["activity"]
    assert s4["is_school_dedicated"] is True

    # T-0 (Stage 5: Post-Exam Clearance & Roadmap Advance)
    s5 = workload_governor.generate_phased_study_action(exam, days_left=0)
    assert "Stage 5" in s5["stage"]
    assert "Post-Exam Clearance" in s5["stage"]
    assert s5["is_school_dedicated"] is False
    assert "TUM Roadmap deliverable" in s5["activity"]


def test_post_exam_suppression_on_test_day(clean_db):
    """
    When an exam is on the current day (days_left == 0),
    afternoon SGH Library deep work must NOT tell the user to study for the test they already took.
    It must automatically pivot to the active TUM Roadmap deliverable.
    """
    exam_day = "2026-09-28"  # Monday

    cursor = clean_db.cursor()
    cursor.execute(
        """
        INSERT INTO school_exams (subject, title, exam_date, scope, completed)
        VALUES ('Informatyka R', 'Sprawdzian: Złożoność Obliczeniowa', '2026-09-28', 'Big-O', 0)
        """
    )
    clean_db.commit()

    analysis = workload_governor.get_workload_analysis(exam_day, conn=clean_db)
    assert len(analysis["today_exams"]) == 1
    assert len(analysis["upcoming_exams"]) == 0  # Today's test is not upcoming

    sched = today_service.get_schedule_for_date(exam_day, conn=clean_db)
    sgh_block = next((b for b in sched["blocks"] if "SGH Library" in b.get("focus", "")), None)
    assert sgh_block is not None

    # Deep work block must NOT tell user to study for Informatyka test written that morning
    assert "Złożoność Obliczeniowa" not in sgh_block["activity"]
    assert sgh_block["is_school_dedicated"] is False
    assert sgh_block["is_tum_roadmap"] is True
    assert "deliverable" in sgh_block


def test_non_defense_tum_roadmap_injection(clean_db):
    """
    On non-defense days (no acute exams/homework), SGH deep work blocks
    automatically embed the active station's TUM Roadmap deliverable with full action metadata.
    """
    non_defense_day = "2026-09-23"  # Wednesday
    sched = today_service.get_schedule_for_date(non_defense_day, conn=clean_db)
    sgh_block = next((b for b in sched["blocks"] if "SGH Library" in b.get("focus", "")), None)
    assert sgh_block is not None

    assert sgh_block["is_tum_roadmap"] is True
    assert sgh_block["is_school_dedicated"] is False
    assert "TUM Roadmap" in sgh_block["focus"] or "TUM Deep Work" in sgh_block["focus"]
    deliv = sgh_block.get("deliverable")
    assert deliv is not None
    assert "deliverable_id" in deliv
    assert "action_type" in deliv
    assert "target_path" in deliv
    assert "quantity" in deliv


def test_auto_seed_future_station_deliverables(clean_db):
    """
    When accessing a future station (e.g. 'oct-2026', 'nov-2026') that has no rows in SQLite yet,
    kill_list_controller.get_station_deliverables automatically seeds them from metro_roadmap.json.
    """
    # Verify no rows exist initially for oct-2026
    cursor = clean_db.cursor()
    cursor.execute("SELECT COUNT(*) AS cnt FROM station_deliverable_progress WHERE station_id = 'oct-2026'")
    assert cursor.fetchone()["cnt"] == 0

    # Calling get_station_deliverables seeds the station
    delivs = kill_list_controller.get_station_deliverables("oct-2026", conn=clean_db)
    assert len(delivs) >= 3

    # Check that they now exist in the database
    cursor.execute("SELECT COUNT(*) AS cnt FROM station_deliverable_progress WHERE station_id = 'oct-2026'")
    assert cursor.fetchone()["cnt"] >= 3

    # Verify deliverables have progressive specs
    for d in delivs:
        assert "next_spec" in d
        assert d["next_spec"]["target_spec"]
        assert d["next_spec"]["action_type"]
