"""Unit tests for Polish grade parser, grade ledger entries, and real-time Bavarian calculation."""

import sqlite3
import pytest
from app.db import init_db
from engine.grade_parser import parse_polish_grade, calculate_subject_average
from app.services import tum_service


@pytest.fixture
def test_db(tmp_path):
    db_file = tmp_path / "test_grades.db"
    init_db(db_file)
    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


def test_grade_parser_standard_and_modifiers():
    # Standard numbers
    assert parse_polish_grade("5")["numeric_value"] == 5.0
    assert parse_polish_grade("4.0")["numeric_value"] == 4.0
    assert parse_polish_grade("3")["numeric_value"] == 3.0

    # Pluses and minuses
    assert parse_polish_grade("4+")["numeric_value"] == 4.5
    assert parse_polish_grade("5-")["numeric_value"] == 4.75
    assert parse_polish_grade("3-")["numeric_value"] == 2.75
    assert parse_polish_grade("2+")["numeric_value"] == 2.5
    assert parse_polish_grade("6-")["numeric_value"] == 5.75
    assert parse_polish_grade("1+")["numeric_value"] == 1.5

    # Comma decimal
    assert parse_polish_grade("4,5")["numeric_value"] == 4.5


def test_grade_parser_fractions_and_points():
    # 17/17 is 100% -> 6.0
    p1 = parse_polish_grade("17/17")
    assert p1["valid"] is True
    assert p1["percentage"] == 100.0
    assert p1["numeric_value"] == 6.0

    # 18/20 is 90% -> 5.0
    p2 = parse_polish_grade("18/20")
    assert p2["valid"] is True
    assert p2["percentage"] == 90.0
    assert p2["numeric_value"] == 5.0

    # 15/20 is 75% -> 4.0
    p3 = parse_polish_grade("15/20")
    assert p3["valid"] is True
    assert p3["percentage"] == 75.0
    assert p3["numeric_value"] == 4.0


def test_grade_parser_percentages():
    # 85% -> 4.5 or 5.0
    p = parse_polish_grade("85%")
    assert p["valid"] is True
    assert p["percentage"] == 85.0
    assert p["numeric_value"] is not None

    # 95% -> 5.5
    p95 = parse_polish_grade("95%")
    assert p95["valid"] is True
    assert p95["percentage"] == 95.0
    assert p95["numeric_value"] >= 5.0

    # 40% -> 1.0
    p40 = parse_polish_grade("40%")
    assert p40["valid"] is True
    assert p40["numeric_value"] == 1.0


def test_grade_parser_non_ordinary_np_bz():
    # NP (nieprzygotowanie)
    p_np = parse_polish_grade("np")
    assert p_np["valid"] is True
    assert p_np["numeric_value"] is None
    assert p_np["counts_in_average"] is False
    assert p_np["display_label"] == "NP"

    # BZ (brak zadania)
    p_bz = parse_polish_grade("bz")
    assert p_bz["valid"] is True
    assert p_bz["numeric_value"] is None
    assert p_bz["counts_in_average"] is False
    assert p_bz["display_label"] == "BZ"


def test_singular_grade_impact_on_running_average(test_db):
    # Initial state
    tum_service.get_tum_overview(conn=test_db)
    
    # Add grade to Matematyka in Semester 1: singular 3
    res1 = tum_service.add_grade_entry(
        subject="Matematyka",
        semester=1,
        raw_input="3",
        weight=2.0,
        category="Sprawdzian",
        description="Funkcja kwadratowa",
        conn=test_db,
    )
    assert res1["success"] is True
    assert res1["running_average"] == 3.0

    # Check overview: Matematyka actual grade should now be 3.0 directly!
    ov1 = tum_service.get_tum_overview(conn=test_db)
    sem1_math = [g for g in ov1["semesters"][1] if g["subject"] == "Matematyka"][0]
    assert sem1_math["actual_grade"] == 3.0
    assert sem1_math["running_average"] == 3.0

    # Add second grade: 5 with weight 2.0 -> (3*2 + 5*2) / 4 = 4.0
    res2 = tum_service.add_grade_entry(
        subject="Matematyka",
        semester=1,
        raw_input="5",
        weight=2.0,
        category="Sprawdzian",
        description="Wielomiany",
        conn=test_db,
    )
    assert res2["success"] is True
    assert res2["running_average"] == 4.0

    # Add non-ordinary grade: 17/17 (100% -> 6.0) with weight 1.0
    # (3*2 + 5*2 + 6*1) / 5 = 22 / 5 = 4.40
    res3 = tum_service.add_grade_entry(
        subject="Matematyka",
        semester=1,
        raw_input="17/17",
        weight=1.0,
        category="Kartkówka",
        description="Wzory skróconego mnożenia",
        conn=test_db,
    )
    assert res3["running_average"] == 4.40

    # Add NP: should NOT change the running average
    res_np = tum_service.add_grade_entry(
        subject="Matematyka",
        semester=1,
        raw_input="np",
        weight=1.0,
        category="Nieprzygotowanie",
        conn=test_db,
    )
    assert res_np["running_average"] == 4.40

    # Delete first grade (the 3) -> average increases!
    deleted = tum_service.delete_grade_entry(res1["entry"]["id"], conn=test_db)
    assert deleted is True

    ov_after_del = tum_service.get_tum_overview(conn=test_db)
    sem1_math_del = [g for g in ov_after_del["semesters"][1] if g["subject"] == "Matematyka"][0]
    # Remaining: 5 (wt 2) + 6 (wt 1) = 16 / 3 = 5.33
    assert sem1_math_del["running_average"] == 5.33
