"""
Harness 3.0 Autonomous Academic Workload Governor.
Analyzes school exam pressure, subject grade vulnerabilities, task archetypes (e.g. essays, exams),
and dynamically shapes daily SGH Library deep work blocks and weekend schedules.
Unifies school-first defense with long-term Matura Rozszerzona & TUM Heilbronn mastery.
"""

import re
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple

from app.db import get_connection
from engine import kill_list_controller
from engine import grade_parser

TIER_1_KEYWORDS = ["matematyka", "informatyka", "angielski", "math", "cs", "algorithm"]
ESSAY_KEYWORDS = ["esej", "rozprawka", "wypracowanie", "tekst", "opowiadanie", "charakterystyka", "analiza literacka", "praca pisemna"]
EXAM_MAJOR_KEYWORDS = ["sprawdzian", "praca klasowa", "test diagnostyczny", "arkusz", "matura", "egzamin"]
QUIZ_KEYWORDS = ["kartkówka", "kartkowka", "odpowiedź", "odpowiedz ustna", "wejściówka"]


def _is_tier_1(subject: str) -> bool:
    """Returns True if subject is a primary Matura Rozszerzona / TUM Heilbronn core pillar."""
    s = (subject or "").lower()
    return any(k in s for k in TIER_1_KEYWORDS)


def classify_obligation(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Classifies an academic obligation (homework or exam) into semantic archetypes:
    - type: 'essay', 'presentation', 'major_exam', 'quiz', 'homework'
    - is_writing_heavy: bool
    - is_stem: bool
    - title_clean: str
    """
    subject = (item.get("subject") or "").strip()
    title = (item.get("title") or "").strip()
    desc = (item.get("description") or item.get("scope") or "").strip()
    combined = f"{subject} {title} {desc}".lower()

    is_writing = any(k in combined for k in ESSAY_KEYWORDS)
    is_major = any(k in combined for k in EXAM_MAJOR_KEYWORDS)
    is_quiz = any(k in combined for k in QUIZ_KEYWORDS)
    is_pres = "prezentacja" in combined or "projekt" in combined
    is_stem = _is_tier_1(subject) or any(k in combined for k in ["fizyka", "chemia", "biologia"])

    if is_writing:
        ob_type = "essay"
    elif is_pres:
        ob_type = "presentation"
    elif is_major:
        ob_type = "major_exam"
    elif is_quiz:
        ob_type = "quiz"
    else:
        ob_type = "homework"

    return {
        "type": ob_type,
        "is_writing_heavy": is_writing or is_pres,
        "is_stem": is_stem,
        "subject": subject,
        "title": title,
    }


def get_subject_vulnerabilities(conn: Optional[sqlite3.Connection] = None) -> Dict[str, Dict[str, Any]]:
    """
    Queries tum_grade_entries to calculate live running GPAs and vulnerability flags per subject.
    A subject with GPA < 3.8 or any recent grade <= 2.0 is marked vulnerable.
    """
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    cursor = conn.cursor()
    try:
        cursor.execute("SELECT subject, raw_input, numeric_value, weight, date FROM tum_grade_entries ORDER BY date ASC")
        rows = cursor.fetchall()
    except Exception:
        rows = []

    subject_entries: Dict[str, List[Dict[str, Any]]] = {}
    for r in rows:
        subj = r["subject"]
        if not subj:
            continue
        val = r["numeric_value"]
        raw = r["raw_input"]
        if val is None and raw:
            parsed = grade_parser.parse_polish_grade(raw)
            val = parsed.get("numeric_value")
        weight = float(r["weight"] or 1.0)
        subject_entries.setdefault(subj, []).append({
            "numeric_value": val,
            "weight": weight,
            "counts_in_average": val is not None,
            "raw_grade": raw,
            "date": r["date"],
        })

    vulnerabilities: Dict[str, Dict[str, Any]] = {}
    for subj, entries in subject_entries.items():
        avg = grade_parser.calculate_subject_average(entries)
        has_low_grade = any(e.get("numeric_value") is not None and e["numeric_value"] <= 2.5 for e in entries)
        is_vulnerable = (avg is not None and avg < 3.8) or has_low_grade
        vulnerabilities[subj] = {
            "subject": subj,
            "gpa": round(avg, 2) if avg is not None else 4.0,
            "is_vulnerable": is_vulnerable,
            "entries_count": len(entries),
            "has_low_grade": has_low_grade,
        }

    if close_conn:
        conn.close()

    return vulnerabilities


def generate_phased_study_action(
    obligation: Dict[str, Any],
    days_left: int,
    subject_gpa: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Synthesizes concrete step-by-step guidance tailored to task archetype,
    days remaining until deadline, and current subject standing.
    """
    classification = classify_obligation(obligation)
    ob_type = classification["type"]
    subject = obligation.get("subject", "School")
    title = obligation.get("title", "")
    scope = obligation.get("scope", obligation.get("description", ""))

    is_vuln = subject_gpa is not None and subject_gpa < 3.8
    vuln_tag = f" [Grade Risk: {subject_gpa:.1f} GPA]" if is_vuln else ""

    if ob_type == "essay":
        if days_left <= 1:
            stage = "Final Polish & Submission"
            focus = f"Deep Work • Polish Essay: Final Review ({subject})"
            activity = (
                f"[Essay Sprint // {stage}{vuln_tag}] 30m verify thesis alignment, textual quotes & bibliography + "
                f"40m polish syntax, transition sentences & argument flow + 20m final formatting and word count check."
            )
        elif days_left == 2:
            stage = "Drafting Sprint"
            focus = f"Deep Work • Essay Drafting: {subject}"
            activity = (
                f"[Essay Sprint // {stage}{vuln_tag}] 40m draft core thesis & body paragraphs 1-2 + "
                f"45m integrate direct textual citations & analysis + 25m draft conclusion and review cohesion."
            )
        else:
            stage = "Outline & Textual Research"
            focus = f"Deep Work • Essay Structure & Thesis: {subject}"
            activity = (
                f"[Essay Prep // {stage}{vuln_tag}] 35m analyze prompt, formulate central thesis & select 3 arguments + "
                f"45m extract literary quotes and supporting evidence from source texts."
            )
    elif ob_type == "major_exam":
        if days_left <= 1:
            stage = "T-1 Rapid Error Blitz & Formula Mastery"
            focus = f"Deep Work • {subject} Exam: Error Blitz"
            activity = (
                f"[Exam Sprint // {stage}{vuln_tag}] 50m targeted formula recall & review past homework error log + "
                f"40m timed past-paper questions on {scope or title[:35]}."
            )
        elif days_left <= 3:
            stage = "T-3 High-Intensity Problem Drill"
            focus = f"Deep Work • {subject} Exam Prep"
            activity = (
                f"[Exam Sprint // {stage}{vuln_tag}] 60m solve 8 targeted exam problem sets ({scope or title[:35]}) + "
                f"30m self-correction and formula derivation."
            )
        else:
            stage = "T-5 Concept Mapping"
            focus = f"Deep Work • {subject} Concept Review"
            activity = (
                f"[Exam Prep // {stage}{vuln_tag}] 45m core theorem/concept mapping + 45m progressive diagnostic problems."
            )
    elif ob_type == "quiz":
        stage = "Quick Active Recall"
        focus = f"Deep Work • {subject} Kartkówka Drill"
        activity = (
            f"[Quiz Sprint // {stage}{vuln_tag}] 30m rapid active recall flashcards/formulas ({title}) + "
            f"25m practice exercises."
        )
    else:  # homework / presentation
        stage = "Submission Clearance"
        focus = f"Deep Work • Homework Clearance: {subject}"
        activity = (
            f"[Homework Sprint // {stage}{vuln_tag}] 45m complete {title} requirements + "
            f"30m answer verification and submission readiness."
        )

    return {
        "stage": stage,
        "focus": focus,
        "activity": activity,
        "is_school_dedicated": True,
        "obligation_type": ob_type,
    }


def get_workload_analysis(
    target_date_str: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, Any]:
    """
    Evaluates upcoming academic commitments over the active horizon (next 10 days for exams, next 7 days for homework).
    Incorporates subject grade vulnerability to calculate the composite academic pressure score.
    """
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    target_dt = datetime.strptime(target_date_str, "%Y-%m-%d").date() if target_date_str else datetime.now().date()
    end_dt = target_dt + timedelta(days=10)
    hw_end_dt = target_dt + timedelta(days=7)

    vulnerabilities = get_subject_vulnerabilities(conn=conn)

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
    immediate_exams = []
    week_exams = []

    for e in exams:
        try:
            ex_date = datetime.strptime(e["exam_date"], "%Y-%m-%d").date()
            days_left = (ex_date - target_dt).days
        except Exception:
            days_left = 0

        e["days_left"] = days_left
        e["is_tier_1"] = _is_tier_1(e["subject"])
        subj_vuln = vulnerabilities.get(e["subject"], {})
        e["is_vulnerable"] = subj_vuln.get("is_vulnerable", False)
        e["subject_gpa"] = subj_vuln.get("gpa", 4.0)

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

    urgent_homework = []
    active_homework = []

    for h in homework:
        try:
            h_date = datetime.strptime(h["due_date"], "%Y-%m-%d").date()
            days_left = (h_date - target_dt).days
        except Exception:
            days_left = 0
        h["days_left"] = days_left
        classification = classify_obligation(h)
        h["is_essay"] = (classification["type"] == "essay")
        subj_vuln = vulnerabilities.get(h["subject"], {})
        h["is_vulnerable"] = subj_vuln.get("is_vulnerable", False)
        h["subject_gpa"] = subj_vuln.get("gpa", 4.0)

        if days_left <= 1:
            urgent_homework.append(h)
        elif days_left <= 5:
            active_homework.append(h)

    # Composite Workload score calculation:
    # - Tier 1 exam: 2.5 pts
    # - Tier 2 exam: 1.0 pt
    # - Immediate exam (<= 2 days): +2.0 pts
    # - Vulnerable subject exam (GPA < 3.8): +2.0 pts booster
    # - Multiple exams this week booster: +1.5 pts per additional exam beyond the first
    # - Urgent homework (due today/tomorrow): +1.5 pts each
    # - Active essay (due in <= 3 days): +2.0 pts booster
    # - Active homework (due in 2-5 days): +0.5 pts each
    score = (len(tier_1_exams) * 2.5) + (len(tier_2_exams) * 1.0)
    if immediate_exams:
        score += 2.0
    for e in exams:
        if e.get("is_vulnerable"):
            score += 1.5
    if len(week_exams) > 1:
        score += (len(week_exams) - 1) * 1.5
    score += (len(urgent_homework) * 1.5)
    for h in homework:
        if h.get("is_essay") and h.get("days_left", 99) <= 3:
            score += 2.0
        elif h.get("is_vulnerable") and h.get("days_left", 99) <= 3:
            score += 1.0
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
        "vulnerabilities": vulnerabilities,
    }


def synthesize_adaptive_schedule(
    base_schedule: Dict[str, Any],
    date_str: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, Any]:
    """
    Takes the static base routine and dynamically shapes the daily plan and study blocks
    depending on upcoming tests, essays, homework deadlines, and live subject grades.
    Weekend schedules automatically inject focused study blocks when upcoming obligations demand defense.
    """
    schedule = dict(base_schedule)
    blocks = [dict(b) for b in schedule.get("blocks", [])]
    analysis = get_workload_analysis(date_str, conn=conn)

    schedule["workload"] = analysis

    target_dt = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else datetime.now().date()
    weekday = target_dt.weekday()  # Monday=0, ... Saturday=5, Sunday=6
    is_weekend = weekday in (5, 6)

    exams = analysis.get("upcoming_exams", [])
    homework = analysis.get("urgent_homework", []) + analysis.get("active_homework", [])

    # Identify acute writing tasks (essays due in <= 3 days)
    acute_essays = [h for h in homework if h.get("is_essay") and h.get("days_left", 99) <= 3]
    # Identify acute exams (exams due in <= 3 days)
    acute_exams = [e for e in exams if e.get("days_left", 99) <= 3]

    # --------------------------------------------------------------------------
    # 1. WEEKEND ADAPTATION: Inject structured study blocks if heavy load looms
    # --------------------------------------------------------------------------
    if is_weekend:
        # Check if tests or essays are scheduled for the coming week (days_left <= 5)
        impending_obligations = [e for e in exams if e.get("days_left", 99) <= 5] + [
            h for h in homework if h.get("days_left", 99) <= 5 and (h.get("is_essay") or h.get("is_vulnerable"))
        ]

        if impending_obligations or analysis["mode"] in ("BALANCED", "SURGE"):
            primary_ob = impending_obligations[0] if impending_obligations else (exams[0] if exams else (homework[0] if homework else None))
            if primary_ob:
                phased = generate_phased_study_action(
                    primary_ob,
                    days_left=primary_ob.get("days_left", 2),
                    subject_gpa=primary_ob.get("subject_gpa")
                )
                time_slot = "14:30 - 16:00" if weekday == 5 else "16:00 - 17:30"
                weekend_block = {
                    "time": time_slot,
                    "focus": f"Weekend Deep Work • {primary_ob['subject']} Defense",
                    "type": "study_block",
                    "activity": phased["activity"],
                    "is_school_dedicated": True,
                    "is_surge": analysis["mode"] == "SURGE",
                }

                # Insert cleanly before evening/recovery blocks
                inserted = False
                for idx, b in enumerate(blocks):
                    if b.get("type") in ("free", "recovery", "social"):
                        blocks.insert(idx, weekend_block)
                        inserted = True
                        break
                if not inserted:
                    blocks.append(weekend_block)

        schedule["blocks"] = blocks
        return schedule

    # --------------------------------------------------------------------------
    # 2. WEEKDAY SGH DEEP WORK SHAPING
    # --------------------------------------------------------------------------
    # If no upcoming exams and no urgent homework, return standard pre-calibrated schedule
    has_academic_commitments = bool(exams) or bool(homework)
    if analysis["mode"] == "CRUISE" and not has_academic_commitments:
        schedule["blocks"] = blocks
        return schedule

    for b in blocks:
        is_deep_work = b.get("type") == "deep_work" or "SGH Library" in b.get("focus", "")
        if not is_deep_work:
            continue

        b["is_surge"] = (analysis["mode"] == "SURGE")

        # Scenario A: Acute Essay Due in <= 2 days (e.g. Essay due after tomorrow -> Tomorrow dedicated to essay)
        if acute_essays:
            top_essay = acute_essays[0]
            phased = generate_phased_study_action(
                top_essay,
                days_left=top_essay.get("days_left", 1),
                subject_gpa=top_essay.get("subject_gpa")
            )
            b["focus"] = phased["focus"]
            b["activity"] = phased["activity"]
            b["is_school_dedicated"] = True

        # Scenario B: Acute Exam Due in <= 2 days
        elif acute_exams:
            top_exam = acute_exams[0]
            phased = generate_phased_study_action(
                top_exam,
                days_left=top_exam.get("days_left", 1),
                subject_gpa=top_exam.get("subject_gpa")
            )
            b["focus"] = phased["focus"]
            b["activity"] = phased["activity"]
            b["is_school_dedicated"] = True

        # Scenario C: Multiple Exams in Near Horizon (2+ upcoming)
        elif len(exams) >= 2:
            e1, e2 = exams[0], exams[1]
            b["focus"] = f"Deep Work • Dual Defense: {e1['subject']} + {e2['subject']}"
            b["activity"] = (
                f"[{analysis['mode']} // Dual Defense] 50m {e1['subject']} ({e1['title']}) problem drill + "
                f"45m {e2['subject']} ({e2['title']}) concept check + 25m TUM LeetCode anchor."
            )
            b["is_school_dedicated"] = True

        # Scenario D: Single Exam + Urgent Homework
        elif exams and analysis.get("urgent_homework"):
            e = exams[0]
            hw = analysis["urgent_homework"][0]
            b["focus"] = f"Deep Work • {e['subject']} Prep + [{hw['subject']}] Homework"
            b["activity"] = (
                f"[{analysis['mode']} // Exam & Submission Split] 45m clear {hw['subject']} assignment ({hw['title'][:35]}) + "
                f"55m {e['subject']} past paper & formula drill."
            )
            b["is_school_dedicated"] = True

        # Scenario E: Urgent Homework Only
        elif analysis.get("urgent_homework"):
            hw = analysis["urgent_homework"][0]
            phased = generate_phased_study_action(hw, days_left=hw.get("days_left", 1), subject_gpa=hw.get("subject_gpa"))
            b["focus"] = phased["focus"]
            b["activity"] = phased["activity"]
            b["is_school_dedicated"] = True

        # Scenario F: General Exam Further Out (3-10 days)
        elif exams:
            prio_exam = exams[0]
            phased = generate_phased_study_action(prio_exam, days_left=prio_exam.get("days_left", 4), subject_gpa=prio_exam.get("subject_gpa"))
            b["focus"] = phased["focus"]
            b["activity"] = phased["activity"]
            b["is_school_dedicated"] = (analysis["mode"] == "SURGE" or prio_exam.get("is_vulnerable", False))

    schedule["blocks"] = blocks
    return schedule


def get_recommended_kill_items(
    date_str: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> List[Dict[str, Any]]:
    """
    Generates the top actionable items for today's library session.
    Automatically prioritizes impending school exams, urgent essays/homework,
    next sequential LeetCode problem, and progressive Math R problem sets.
    """
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    analysis = get_workload_analysis(date_str, conn=conn)
    recommendations = []

    # 1. Urgent essays or homework (due in <= 2 days)
    urgent_hw = analysis.get("urgent_homework", []) + [h for h in analysis.get("active_homework", []) if h.get("is_essay")]
    if urgent_hw:
        for hw in urgent_hw[:2]:
            recommendations.append({
                "type": "homework_prep",
                "homework_id": hw["id"],
                "category": hw["subject"],
                "title": f"{'Essay' if hw.get('is_essay') else 'Homework'}: [{hw['subject']}] {hw['title']}",
                "target_spec": f"Due: {hw['due_date']} (Priority {hw.get('priority', 1)})",
                "quantity": 1,
                "action_type": "url",
                "target_path": "https://uonetplus.vulcan.net.pl",
                "days_left": hw["days_left"],
            })

    # 2. Impending exam prep
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

    # 3. Sequential Metro deliverable progression (LeetCode & Math R)
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

    if close_conn:
        conn.close()

    return recommendations[:4]
