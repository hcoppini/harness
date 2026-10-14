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

    target_direct = 88.0
    target_interview = 70.0
    target_german_gpa = 1.36

    points_to_direct = max(0.0, round(target_direct - total_score, 1))
    points_to_interview = max(0.0, round(target_interview - total_score, 1))
    gpa_gap = round(g_gpa - target_german_gpa, 2)

    if total_score >= target_direct:
        verdict = "DIRECT ADMISSION SAFE (Level 1)"
        status_level = "safe"
        distance_summary = f"+{round(total_score - target_direct, 1)} pts above Direct Admission (88.0)"
    elif total_score >= target_interview:
        verdict = "INTERVIEW THRESHOLD (Level 2)"
        status_level = "interview"
        distance_summary = f"{points_to_direct} pts to Direct Admission (88.0)"
    else:
        verdict = "DEFICIT: MATH/CS RECOVERY NEEDED"
        status_level = "deficit"
        distance_summary = f"{points_to_direct} pts to Direct Admission | {points_to_interview} pts to Interview"

    # Identify primary drags on score
    subject_drags = []
    if cs_pl < 5.0:
        cs_gain = round((5.0 - cs_pl) * 5.3, 1)
        subject_drags.append({
            "subject": "Informatyka",
            "current": cs_pl,
            "target": 5.0,
            "potential_gain_pts": cs_gain,
            "recommendation": f"Raise CS to 5.0 (+{cs_gain} pts)",
        })
    if math_pl < 5.0:
        math_gain = round((5.0 - math_pl) * 5.3, 1)
        subject_drags.append({
            "subject": "Matematyka",
            "current": math_pl,
            "target": 5.0,
            "potential_gain_pts": math_gain,
            "recommendation": f"Raise Math to 5.0 (+{math_gain} pts)",
        })
    if lang_pl < 5.0:
        lang_gain = round((5.0 - lang_pl) * 2.7, 1)
        subject_drags.append({
            "subject": "Język Angielski",
            "current": lang_pl,
            "target": 5.0,
            "potential_gain_pts": lang_gain,
            "recommendation": f"Raise English to 5.0 (+{lang_gain} pts)",
        })

    subject_drags.sort(key=lambda x: x["potential_gain_pts"], reverse=True)
    primary_action = subject_drags[0]["recommendation"] if subject_drags else "Maintain current trajectory across all 3 key subjects."

    return {
        "german_gpa": g_gpa,
        "target_german_gpa": target_german_gpa,
        "german_gpa_gap": gpa_gap,
        "total_tum_points": total_score,
        "target_direct_points": target_direct,
        "target_interview_points": target_interview,
        "points_to_direct": points_to_direct,
        "points_to_interview": points_to_interview,
        "distance_summary": distance_summary,
        "status_level": status_level,
        "primary_action": primary_action,
        "subject_drags": subject_drags,
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
