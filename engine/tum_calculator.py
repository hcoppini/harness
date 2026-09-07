"""Bavarian Formula and TUM Aptitude Assessment Calculator.

Converts Polish high school grades (2.0 to 6.0) and Matura percentages (30% to 100%)
to the German grading scale (1.0 to 4.0) using the official "Modifizierte Bayerische Formel":
    N = 1 + 3 * (P_max - P) / (P_max - P_min)

Calculates the Technical University of Munich (TUM) Stage 1 Aptitude Assessment (0 to 100 pts)
for B.Sc. Management and Data Science (TUM Campus Heilbronn):
    - Overall GPA (German equivalent): 65% weight
    - Curricular subjects (Math 2x, CS 2x, Lang 1x): 35% weight
"""

from typing import Dict, Any


def calculate_bavarian_grade(p: float, p_max: float = 100.0, p_min: float = 30.0) -> float:
    """Converts a Polish score/percentage or grade to the German grading scale (1.0 to 4.0)."""
    if p >= p_max:
        return 1.0
    if p <= p_min:
        return 4.0
    grade = 1.0 + 3.0 * ((p_max - p) / (p_max - p_min))
    return round(grade, 2)


def calculate_tum_aptitude_score(
    gpa_pl: float,
    math_pl: float,
    cs_pl: float,
    lang_pl: float,
) -> Dict[str, Any]:
    """
    Computes TUM Stage 1 Aptitude Assessment points (0 to 100).
    Input grades on Polish scale (2.0 to 6.0).
    """
    # Convert Polish 1-6 scale to German 1-4 scale
    g_gpa = calculate_bavarian_grade(gpa_pl, p_max=6.0, p_min=2.0)
    g_math = calculate_bavarian_grade(math_pl, p_max=6.0, p_min=2.0)
    g_cs = calculate_bavarian_grade(cs_pl, p_max=6.0, p_min=2.0)
    g_lang = calculate_bavarian_grade(lang_pl, p_max=6.0, p_min=2.0)

    # Convert German grade (1.0 best, 4.0 worst) to TUM point equivalents (1.0 -> 100, 4.0 -> 0)
    def grade_to_points(g: float) -> float:
        return max(0.0, min(100.0, (4.0 - g) * (100.0 / 3.0)))

    pts_gpa = grade_to_points(g_gpa)
    pts_math = grade_to_points(g_math)
    pts_cs = grade_to_points(g_cs)
    pts_lang = grade_to_points(g_lang)

    # Curricular weighting: Math (2x), CS (2x), Lang (1x)
    subject_score = (pts_math * 2 + pts_cs * 2 + pts_lang * 1) / 5.0

    # TUM Weighted Total: 65% Overall GPA + 35% Curricular Subjects
    total_score = round(0.65 * pts_gpa + 0.35 * subject_score, 1)

    if total_score >= 88.0:
        verdict = "DIRECT ADMISSION SAFE (Level 1)"
    elif total_score >= 70.0:
        verdict = "INTERVIEW THRESHOLD (Level 2)"
    else:
        verdict = "DEFICIT: MATH/CS RECOVERY NEEDED"

    return {
        "german_gpa": g_gpa,
        "total_tum_points": total_score,
        "verdict": verdict,
        "gpa_pl": gpa_pl,
        "math_pl": math_pl,
        "cs_pl": cs_pl,
        "lang_pl": lang_pl,
        "german_math": g_math,
        "german_cs": g_cs,
        "german_lang": g_lang,
        "pts_gpa": round(pts_gpa, 1),
        "pts_subject": round(subject_score, 1),
        "pts_math": round(pts_math, 1),
        "pts_cs": round(pts_cs, 1),
        "pts_lang": round(pts_lang, 1),
    }
