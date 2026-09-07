"""Unit tests for Bavarian Formula and TUM Aptitude Assessment calculator."""

import pytest
from engine.tum_calculator import calculate_bavarian_grade, calculate_tum_aptitude_score


def test_bavarian_grade_percentage_scale():
    # 100% -> 1.0 (German best)
    assert calculate_bavarian_grade(100.0, p_max=100.0, p_min=30.0) == 1.0
    # 30% -> 4.0 (German minimum pass)
    assert calculate_bavarian_grade(30.0, p_max=100.0, p_min=30.0) == 4.0
    # Scores outside bounds
    assert calculate_bavarian_grade(105.0, p_max=100.0, p_min=30.0) == 1.0
    assert calculate_bavarian_grade(25.0, p_max=100.0, p_min=30.0) == 4.0
    # Midpoint (65%)
    # 1 + 3 * (100 - 65) / 70 = 1 + 3 * 35 / 70 = 2.5
    assert calculate_bavarian_grade(65.0, p_max=100.0, p_min=30.0) == 2.5


def test_bavarian_grade_polish_scale():
    # Polish scale: 6.0 max, 2.0 min
    assert calculate_bavarian_grade(6.0, p_max=6.0, p_min=2.0) == 1.0
    assert calculate_bavarian_grade(2.0, p_max=6.0, p_min=2.0) == 4.0
    # 5.0 -> 1 + 3 * 1 / 4 = 1.75
    assert calculate_bavarian_grade(5.0, p_max=6.0, p_min=2.0) == 1.75
    # 4.0 -> 1 + 3 * 2 / 4 = 2.5
    assert calculate_bavarian_grade(4.0, p_max=6.0, p_min=2.0) == 2.5


def test_tum_aptitude_score_direct_admission():
    # Polish grades: GPA 5.5, Math 6.0, CS 6.0, Lang 5.5
    res = calculate_tum_aptitude_score(gpa_pl=5.5, math_pl=6.0, cs_pl=6.0, lang_pl=5.5)
    assert res["total_tum_points"] >= 88.0
    assert res["verdict"] == "DIRECT ADMISSION SAFE (Level 1)"
    assert res["german_gpa"] == 1.38


def test_tum_aptitude_score_perfect():
    # Perfect Polish 6.0 across the board -> 100 TUM points
    res = calculate_tum_aptitude_score(gpa_pl=6.0, math_pl=6.0, cs_pl=6.0, lang_pl=6.0)
    assert res["total_tum_points"] == 100.0
    assert res["german_gpa"] == 1.0
    assert res["verdict"] == "DIRECT ADMISSION SAFE (Level 1)"


def test_tum_aptitude_score_interview_threshold():
    # Polish grades: GPA 5.0, Math 5.0, CS 5.0, Lang 5.0
    res = calculate_tum_aptitude_score(gpa_pl=5.0, math_pl=5.0, cs_pl=5.0, lang_pl=5.0)
    assert 70.0 <= res["total_tum_points"] < 88.0
    assert res["verdict"] == "INTERVIEW THRESHOLD (Level 2)"


def test_tum_aptitude_score_deficit():
    # Polish grades: GPA 3.5, Math 3.0, CS 3.5, Lang 3.0
    res = calculate_tum_aptitude_score(gpa_pl=3.5, math_pl=3.0, cs_pl=3.5, lang_pl=3.0)
    assert res["total_tum_points"] < 70.0
    assert res["verdict"] == "DEFICIT: MATH/CS RECOVERY NEEDED"
