"""
Harness 3.0 Adaptive Workload Governor.
Analyzes school exam pressure, computes cognitive load, and dynamically shapes
daily SGH Library deep work blocks and week schedules to prevent burnout and ace exams.
"""

import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from app.db import get_connection
from engine import kill_list_controller

TIER_1_KEYWORDS = ["matematyka", "informatyka", "angielski", "math", "cs", "algorithm"]


def _is_tier_1(subject: str) -> bool:
    """Returns True if subject is a primary Matura Rozszerzona / TUM Heilbronn core pillar."""
    s = (subject or "").lower()
    return any(k in s for k in TIER_1_KEYWORDS)


def get_workload_analysis(
    target_date_str: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, Any]:
    """
    Evaluates upcoming academic commitments over the active horizon (next 10 days for exams, next 7 days for homework).
    Calculates composite academic pressure score and determines operational mode (Cruise vs Balanced vs Surge).
    """
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    target_dt = datetime.strptime(target_date_str, "%Y-%m-%d").date() if target_date_str else datetime.now().date()
    end_dt = target_dt + timedelta(days=10)
    hw_end_dt = target_dt + timedelta(days=7)

    cursor = conn.cursor()
    
    # 1. Fetch upcoming exams
    cursor.execute(
        """
        SELECT * FROM school_exams
        WHERE completed = 0 AND exam_date >= ? AND exam_date <= ?
        ORDER BY exam_date ASC
        """,
        (target_dt.strftime("%Y-%m-%d"), end_dt.strftime("%Y-%m-%d")),
    )
    exams = [dict(r) for r in cursor.fetchall()]

    tier_1_exams = []
    tier_2_exams = []
    immediate_exams = []  # Due in <= 2 days
    week_exams = []       # Due in <= 5 days

    for e in exams:
        try:
            ex_date = datetime.strptime(e["exam_date"], "%Y-%m-%d").date()
            days_left = (ex_date - target_dt).days
        except Exception:
            days_left = 0

        e["days_left"] = days_left
        e["is_tier_1"] = _is_tier_1(e["subject"])

        if days_left <= 2:
            immediate_exams.append(e)
        if days_left <= 5:
            week_exams.append(e)

        if e["is_tier_1"]:
            tier_1_exams.append(e)
        else:
            tier_2_exams.append(e)

    # 2. Fetch pending homework
    cursor.execute(
        """
        SELECT * FROM homework_items
        WHERE completed = 0 AND due_date >= ? AND due_date <= ?
        ORDER BY due_date ASC
        """,
        (target_dt.strftime("%Y-%m-%d"), hw_end_dt.strftime("%Y-%m-%d")),
    )
    homework = [dict(r) for r in cursor.fetchall()]

    urgent_homework = []  # Due in 0-1 days (today or tomorrow)
    active_homework = []  # Due in 2-5 days

    for h in homework:
        try:
            h_date = datetime.strptime(h["due_date"], "%Y-%m-%d").date()
            days_left = (h_date - target_dt).days
        except Exception:
            days_left = 0
        h["days_left"] = days_left
        if days_left <= 1:
            urgent_homework.append(h)
        elif days_left <= 5:
            active_homework.append(h)

    # Composite Workload score calculation:
    # - Tier 1 exam: 2.5 pts
    # - Tier 2 exam: 1.0 pt
    # - Immediate exam (<= 2 days): +2.0 pts
    # - Multiple exams this week booster: +1.5 pts per additional exam beyond the first
    # - Urgent homework (due today/tomorrow): +1.5 pts each
    # - Active homework (due in 2-5 days): +0.5 pts each
    score = (len(tier_1_exams) * 2.5) + (len(tier_2_exams) * 1.0)
    if immediate_exams:
        score += 2.0
    if len(week_exams) > 1:
        score += (len(week_exams) - 1) * 1.5
    score += (len(urgent_homework) * 1.5)
    score += (len(active_homework) * 0.5)

    if score <= 2.5:
        mode = "CRUISE"
        mode_label = "Cruise Mode • TUM Acceleration"
        badge_class = "optimal"
        desc = "Standard academic load. Maximum capacity allocated to raw LeetCode coding, Math R diagnostic mastery, and SIGG scanner."
    elif score <= 6.0:
        mode = "BALANCED"
        mode_label = "Balanced Mode • Dual Track Focus"
        badge_class = "lavender"
        hw_info = f", {len(urgent_homework)} urgent hw" if urgent_homework else ""
        desc = f"Moderate academic load ({len(exams)} exam(s){hw_info}). SGH library deep work calibrated between test prep and core TUM deliverables."
    else:
        mode = "SURGE"
        mode_label = "Surge Protocol • High Academic Density"
        badge_class = "amber"
        hw_info = f", {len(urgent_homework)} urgent homework" if urgent_homework else ""
        desc = f"High academic load ({len(exams)} upcoming test(s){hw_info}). SGH deep work blocks dynamically re-routed to phased exam defense and submission clearance."

    if close_conn:
        conn.close()

    return {
        "date": target_dt.strftime("%Y-%m-%d"),
        "mode": mode,
        "mode_label": mode_label,
        "badge_class": badge_class,
        "description": desc,
        "workload_score": round(score, 1),
        "total_exams": len(exams),
        "week_exams_count": len(week_exams),
        "tier_1_count": len(tier_1_exams),
        "tier_2_count": len(tier_2_exams),
        "immediate_count": len(immediate_exams),
        "upcoming_exams": exams,
        "homework_count": len(homework),
        "urgent_homework_count": len(urgent_homework),
        "urgent_homework": urgent_homework,
        "active_homework": active_homework,
    }


def synthesize_adaptive_schedule(
    base_schedule: Dict[str, Any],
    date_str: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, Any]:
    """
    Takes the static base routine and dynamically synthesizes the deep work session
    to match real-time test density and urgent homework deadlines without
    violating commute, gym, or recovery constraints.
    """
    schedule = dict(base_schedule)
    blocks = [dict(b) for b in schedule.get("blocks", [])]
    analysis = get_workload_analysis(date_str, conn=conn)

    schedule["workload"] = analysis

    # If no upcoming exams and no urgent homework, return standard pre-calibrated schedule
    has_academic_commitments = bool(analysis["upcoming_exams"]) or bool(analysis.get("urgent_homework"))
    if analysis["mode"] == "CRUISE" and not has_academic_commitments:
        schedule["blocks"] = blocks
        return schedule

    exams = analysis["upcoming_exams"]
    urgent_hw = analysis.get("urgent_homework", [])

    for b in blocks:
        is_deep_work = b.get("type") == "deep_work" or "SGH Library" in b.get("focus", "")
        if not is_deep_work:
            continue

        b["is_surge"] = (analysis["mode"] == "SURGE")

        # Case 1: Multiple exams in the near week (2+ upcoming)
        if len(exams) >= 2:
            e1, e2 = exams[0], exams[1]
            b["focus"] = f"Deep Work • Dual Defense: {e1['subject']} + {e2['subject']}"
            b["activity"] = (
                f"[{analysis['mode']} // Dual Exam Split] 45m {e1['subject']} ({e1['title']}) + "
                f"45m {e2['subject']} ({e2['title']}) + 30m TUM anchor problem set."
            )
        # Case 2: Single acute exam + urgent homework
        elif exams and urgent_hw:
            e = exams[0]
            hw = urgent_hw[0]
            b["focus"] = f"Deep Work • {e['subject']} Prep + [{hw['subject']}] Homework"
            b["activity"] = (
                f"[{analysis['mode']} // Exam & Submission Split] 40m clear {hw['subject']} homework ({hw['title'][:35]}) + "
                f"50m {e['subject']} past paper & formulas + 30m TUM sprint."
            )
        # Case 3: Urgent homework only (no exams in next 10 days)
        elif not exams and urgent_hw:
            hw = urgent_hw[0]
            b["focus"] = f"Deep Work • Homework Sprint: [{hw['subject']}]"
            b["activity"] = (
                f"[{analysis['mode']} // Homework Clearance] 50m complete {hw['subject']} assignment ({hw['title'][:40]}) + "
                f"40m TUM LeetCode / Math R sprint."
            )
        # Case 4: Single exam
        elif exams:
            prio_exam = exams[0]
            days_left = prio_exam.get("days_left", 1)
            if days_left <= 1:
                stage = "T-1 Error Blitz & Formula Mastery"
                prep_focus = f"60m {prio_exam['subject']} ({prio_exam['title']}) past arkusz + 30m rapid formula recall."
            elif days_left <= 3:
                stage = "T-3 Focused Problem Sets"
                prep_focus = f"50m {prio_exam['subject']} problem sets ({prio_exam.get('scope', 'Core topics')[:40]}...) + 40m LeetCode drill."
            else:
                stage = "T-5 Concept Mapping"
                prep_focus = f"45m {prio_exam['subject']} concept review + 45m Math R problem sets."

            b["activity"] = f"[{analysis['mode']} // {stage}] {prep_focus} Commute cutoff locked at 16:30 for evening recovery."
            b["focus"] = f"{b.get('focus', 'Deep Work')} • {prio_exam['subject']} Prep"

    schedule["blocks"] = blocks
    return schedule


def get_recommended_kill_items(
    date_str: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> List[Dict[str, Any]]:
    """
    Generates the top 3 high-impact actionable items for today's library session.
    Automatically prioritizes impending school exams, next sequential LeetCode problem,
    and progressive Math R problem sets.
    """
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    analysis = get_workload_analysis(date_str, conn=conn)
    recommendations = []

    # 1. Urgent homework (due today/tomorrow)
    if analysis.get("urgent_homework"):
        for hw in analysis["urgent_homework"][:2]:
            recommendations.append({
                "type": "homework_prep",
                "homework_id": hw["id"],
                "category": hw["subject"],
                "title": f"Homework: [{hw['subject']}] {hw['title']}",
                "target_spec": f"Due: {hw['due_date']} (Priority {hw.get('priority', 1)})",
                "quantity": 1,
                "action_type": "url",
                "target_path": "https://uonetplus.vulcan.net.pl",
                "days_left": hw["days_left"],
            })

    # 2. Impending exam prep (if in Surge or Balanced)
    if analysis["upcoming_exams"]:
        for ex in analysis["upcoming_exams"][:2]:
            scope_desc = f" ({ex.get('scope', '')[:35]}...)" if ex.get("scope") else ""
            recommendations.append({
                "type": "exam_prep",
                "exam_id": ex["id"],
                "category": ex["subject"],
                "title": f"Prep: {ex['subject']} — {ex['title']}",
                "target_spec": f"Zadania z zakresu{scope_desc}",
                "quantity": 1,
                "action_type": "pdf",
                "target_path": "https://cke.gov.pl",
                "days_left": ex["days_left"],
            })

    # 2. Sequential Metro deliverable progression (LeetCode & Math R)
    deliverables = kill_list_controller.get_station_deliverables("sep-2026", conn=conn)
    for d in deliverables:
        d_id = d["deliverable_id"]
        next_spec = d.get("next_spec")
        if not next_spec or d["is_completed"]:
            continue

        if "leetcode" in d_id or "code" in d_id:
            recommendations.append({
                "type": "metro_deliverable",
                "deliverable_id": d_id,
                "category": next_spec["category"],
                "title": next_spec["title"],
                "target_spec": next_spec["target_spec"],
                "quantity": next_spec["quantity"],
                "action_type": next_spec["action_type"],
                "target_path": next_spec["target_path"],
                "stream": d["stream"],
            })
        elif "math" in d_id:
            recommendations.append({
                "type": "metro_deliverable",
                "deliverable_id": d_id,
                "category": next_spec["category"],
                "title": next_spec["title"],
                "target_spec": next_spec["target_spec"],
                "quantity": next_spec["quantity"],
                "action_type": next_spec["action_type"],
                "target_path": next_spec["target_path"],
                "stream": d["stream"],
            })

    # Cap to top 4 recommendations
    if close_conn:
        conn.close()

    return recommendations[:4]
