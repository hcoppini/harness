"""
Harness 3.0 Autonomous Academic Workload Governor.
Analyzes school exam pressure, subject grade vulnerabilities, task archetypes (e.g. essays, exams),
and dynamically shapes daily SGH Library deep work blocks and weekend schedules.
Unifies school-first defense with long-term Matura Rozszerzona & TUM Heilbronn mastery.
"""

import re
import sqlite3
from datetime import datetime, timedelta, date
from typing import Dict, Any, List, Optional, Tuple

from app.db import get_connection
from engine import kill_list_controller
from engine import grade_parser

TIER_1_KEYWORDS = ["matematyka", "informatyka", "angielski", "math", "cs", "algorithm"]
ESSAY_KEYWORDS = ["esej", "rozprawka", "wypracowanie", "tekst", "opowiadanie", "charakterystyka", "analiza literacka", "praca pisemna"]
EXAM_MAJOR_KEYWORDS = ["sprawdzian", "praca klasowa", "test diagnostyczny", "arkusz", "matura", "egzamin"]
QUIZ_KEYWORDS = ["kartkówka", "kartkowka", "odpowiedź", "odpowiedz ustna", "wejściówka"]


def is_us_travel_date(target_date: Optional[Any] = None) -> bool:
    """
    Returns True if target_date falls within the autonomous US trip window (October 4th - 18th, 2026).
    During this window, Warsaw Liceum timetables and alarms are suspended, school surge mode
    is frozen, and flexible hotel deep work blocks are scheduled.
    """
    if target_date is None:
        dt = datetime.now().date()
    elif isinstance(target_date, str):
        try:
            dt = datetime.strptime(target_date[:10], "%Y-%m-%d").date()
        except Exception:
            dt = datetime.now().date()
    elif isinstance(target_date, datetime):
        dt = target_date.date()
    elif isinstance(target_date, date):
        dt = target_date
    else:
        dt = datetime.now().date()

    return date(2026, 10, 4) <= dt <= date(2026, 10, 18)


def get_active_station_id(target_date: Optional[Any] = None) -> str:
    """
    Dynamically maps any target date between 2026 and 2028 to its active TUM Metro station ID.
    Handles the combined summer station 'jul-aug-2027', boundaries, and monthly progression.
    Guarantees autonomous operation for the next two years through July 2028 graduation.
    """
    if target_date is None:
        dt = datetime.now().date()
    elif isinstance(target_date, str):
        try:
            dt = datetime.strptime(target_date[:10], "%Y-%m-%d").date()
        except Exception:
            dt = datetime.now().date()
    elif isinstance(target_date, datetime):
        dt = target_date.date()
    elif isinstance(target_date, date):
        dt = target_date
    else:
        dt = datetime.now().date()

    year = dt.year
    month = dt.month

    # Boundary conditions
    if year < 2026 or (year == 2026 and month <= 8):
        return "kickoff-2026"
    if year > 2028 or (year == 2028 and month >= 7):
        return "jul-2028"

    month_names = {
        1: "jan", 2: "feb", 3: "mar", 4: "apr",
        5: "may", 6: "jun", 7: "jul", 8: "aug",
        9: "sep", 10: "oct", 11: "nov", 12: "dec"
    }

    # Year 2027 special case: July & August combined
    if year == 2027 and month in (7, 8):
        return "jul-aug-2027"

    m_abbr = month_names.get(month, "sep")
    return f"{m_abbr}-{year}"


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
    Synthesizes concrete 5-stage progressive execution guidance tailored to task archetype,
    days remaining until deadline, and current subject standing.
    Includes explicit post-exam suppression on exam day (T-0).
    """
    classification = classify_obligation(obligation)
    ob_type = classification["type"]
    subject = obligation.get("subject", "School")
    title = obligation.get("title", "")
    scope = obligation.get("scope", obligation.get("description", ""))

    is_vuln = subject_gpa is not None and subject_gpa < 3.8
    vuln_tag = f" [Grade Risk: {subject_gpa:.1f} GPA]" if is_vuln else ""

    if ob_type in ("major_exam", "exam"):
        if days_left <= 0:
            stage = "Stage 5: Post-Exam Clearance & Roadmap Advance (T-0)"
            focus = f"Deep Work • Post-Exam Clearance: {subject}"
            activity = (
                f"[Exam Written // {stage}] Morning test completed in school. Academic defense cleared. "
                f"100% afternoon deep work capacity redirected to active TUM Roadmap deliverable."
            )
            is_school = False
        elif days_left == 1:
            stage = "Stage 4: Timed Mock Simulation & Rapid Blitz (T-1)"
            focus = f"Deep Work • {subject} Exam Prep: Final Mock & Blitz"
            activity = (
                f"[Exam Sprint // {stage}{vuln_tag}] 45m strict timed {subject} mock exam simulation + "
                f"30m rapid formula recall blitz on {scope or title[:35]} + 15m trap review."
            )
            is_school = True
        elif days_left in (2, 3):
            stage = "Stage 3: Hard & Past-Paper Drills (T-3 to T-2)"
            focus = f"Deep Work • {subject} Exam Prep: Advanced Past Papers"
            activity = (
                f"[Exam Sprint // {stage}{vuln_tag}] 60m {subject} unassisted CKE/operon past paper problems ({scope or title[:35]}) + "
                f"30m red-pen step-by-step scoring and proof verification."
            )
            is_school = True
        elif days_left in (4, 5):
            stage = "Stage 2: Foundational Problem Sets & Error Bank (T-5 to T-4)"
            focus = f"Deep Work • {subject} Exam Prep: Problem Drills"
            activity = (
                f"[Exam Prep // {stage}{vuln_tag}] 50m solve 6-8 foundational {subject} problem sets ({scope or title[:35]}) + "
                f"30m log all errors/hesitations into error bank + 10m review theorem justifications."
            )
            is_school = True
        else:  # T-6 or further (Stage 1)
            stage = "Stage 1: Scope & Theorem Mapping (T-7 to T-6)"
            focus = f"Deep Work • {subject} Exam Prep: Scope & Theorem Mapping"
            activity = (
                f"[Exam Prep // {stage}{vuln_tag}] 35m create condensed {subject} concept/theorem map ({scope or title[:35]}) + "
                f"35m catalog definition sheet & review past errors + 20m calibrate target problem archetypes."
            )
            is_school = True

    elif ob_type == "essay":
        if days_left <= 0:
            stage = "Stage 4: Submission Cleared (T-0)"
            focus = f"Deep Work • Essay Cleared: {subject}"
            activity = f"[Essay Submitted // {stage}] Written assignment submitted in morning class. SGH deep work pivoted to TUM Roadmap."
            is_school = False
        elif days_left == 1:
            stage = "Stage 3: Final Polish & Linguistic Flow (T-1)"
            focus = f"Deep Work • Polish Essay: Final Review ({subject})"
            activity = (
                f"[Essay Sprint // {stage}{vuln_tag}] 35m verify thesis alignment, textual quotes & bibliography + "
                f"35m polish syntax, vocabulary variety & transitions + 20m final formatting and word count check."
            )
            is_school = True
        elif days_left in (2, 3):
            stage = "Stage 2: Full Drafting Sprint (T-3 to T-2)"
            focus = f"Deep Work • Essay Drafting: {subject}"
            activity = (
                f"[Essay Sprint // {stage}{vuln_tag}] 45m draft core thesis & body paragraphs 1-2 + "
                f"35m integrate direct textual citations & analysis + 20m draft counter-argument and conclusion."
            )
            is_school = True
        else:
            stage = "Stage 1: Outline & Textual Research (T-4+)"
            focus = f"Deep Work • Essay Structure & Thesis: {subject}"
            activity = (
                f"[Essay Prep // {stage}{vuln_tag}] 35m analyze prompt, formulate central thesis & select 3 arguments + "
                f"45m extract literary quotes and supporting evidence from source texts."
            )
            is_school = True

    elif ob_type == "quiz":
        if days_left <= 0:
            stage = "Post-Quiz Clearance (T-0)"
            focus = f"Deep Work • Quiz Cleared: {subject}"
            activity = f"[Quiz Written // {stage}] Morning quiz finished. Capacity focused on TUM Roadmap."
            is_school = False
        elif days_left == 1:
            stage = "T-1 Rapid Active Recall & Flashcards"
            focus = f"Deep Work • {subject} Kartkówka Drill"
            activity = f"[Quiz Sprint // {stage}{vuln_tag}] 30m high-speed active recall flashcards/formulas ({title}) + 25m practice exercises under timer."
            is_school = True
        else:
            stage = "Early Concept & Terminology Review"
            focus = f"Deep Work • {subject} Concepts"
            activity = f"[Quiz Prep // {stage}{vuln_tag}] 30m active recall of definitions/formulas ({title}) + 20m review example problems."
            is_school = True

    else:  # homework / presentation
        if days_left <= 0:
            stage = "Submission Clearance (T-0)"
            focus = f"Deep Work • Homework Cleared: {subject}"
            activity = f"[Homework Cleared // {stage}] Assignment submitted. Session dedicated to TUM Roadmap."
            is_school = False
        elif days_left == 1:
            stage = "Final Review & Completion (T-1)"
            focus = f"Deep Work • Homework Clearance: {subject}"
            activity = (
                f"[Homework Sprint // {stage}{vuln_tag}] 45m complete {title} requirements + "
                f"30m answer verification and submission readiness."
            )
            is_school = True
        else:
            stage = "Early Problem Solving"
            focus = f"Deep Work • {subject} Assignment"
            activity = f"[Homework Prep // {stage}{vuln_tag}] 40m solve core assignment questions ({title[:35]}) + 20m verify steps."
            is_school = True

    return {
        "stage": stage,
        "focus": focus,
        "activity": activity,
        "is_school_dedicated": is_school,
        "obligation_type": ob_type,
    }


def get_workload_analysis(
    target_date_str: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, Any]:
    """
    Evaluates upcoming academic commitments over the active horizon (next 10 days for exams, next 7 days for homework).
    Incorporates subject grade vulnerability to calculate the composite academic pressure score.
    Automatically handles US Travel Protocol (Oct 4–18) and exam-day post-test suppression (T-0).
    """
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    target_dt = datetime.strptime(target_date_str, "%Y-%m-%d").date() if target_date_str else datetime.now().date()
    end_dt = target_dt + timedelta(days=10)
    hw_end_dt = target_dt + timedelta(days=7)

    is_travel = is_us_travel_date(target_dt)
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
            ex_date = target_dt
            days_left = 0

        e["days_left"] = days_left
        e["is_tier_1"] = _is_tier_1(e["subject"])
        subj_vuln = vulnerabilities.get(e["subject"], {})
        e["is_vulnerable"] = subj_vuln.get("is_vulnerable", False)
        e["subject_gpa"] = subj_vuln.get("gpa", 4.0)

        # US Travel protocol: exams occurring during trip are travel-excused post-trip defense
        if is_travel or is_us_travel_date(ex_date):
            e["is_travel_excused"] = True

        # Only future exams (days_left >= 1) require acute study preparation; exam day (days_left == 0) is already written
        if days_left >= 1 and not e.get("is_travel_excused"):
            if 1 <= days_left <= 2:
                immediate_exams.append(e)
            if 1 <= days_left <= 5:
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
            h_date = target_dt
            days_left = 0
        h["days_left"] = days_left
        classification = classify_obligation(h)
        h["is_essay"] = (classification["type"] == "essay")
        subj_vuln = vulnerabilities.get(h["subject"], {})
        h["is_vulnerable"] = subj_vuln.get("is_vulnerable", False)
        h["subject_gpa"] = subj_vuln.get("gpa", 4.0)

        if is_travel or is_us_travel_date(h_date):
            h["is_travel_excused"] = True

        if not h.get("is_travel_excused"):
            if days_left == 1:
                urgent_homework.append(h)
            elif 2 <= days_left <= 5:
                active_homework.append(h)

    # Composite Workload score calculation:
    score = (len(tier_1_exams) * 2.5) + (len(tier_2_exams) * 1.0)
    if immediate_exams:
        score += 2.0
    for e in exams:
        if e.get("is_vulnerable") and e.get("days_left", 0) >= 1 and not e.get("is_travel_excused"):
            score += 1.5
    if len(week_exams) > 1:
        score += (len(week_exams) - 1) * 1.5
    score += (len(urgent_homework) * 1.5)
    for h in homework:
        if h.get("is_essay") and 1 <= h.get("days_left", 99) <= 3 and not h.get("is_travel_excused"):
            score += 2.0
        elif h.get("is_vulnerable") and 1 <= h.get("days_left", 99) <= 3 and not h.get("is_travel_excused"):
            score += 1.0
    score += (len(active_homework) * 0.5)

    if is_travel:
        mode = "TRAVEL"
        mode_label = "US Travel Protocol • Hotel Deep Work"
        badge_class = "travel"
        desc = "US Trip Active (Oct 4–18). Warsaw Liceum timetable suspended. Academic surge mode frozen. 75m flexible hotel deep work scheduled for TUM roadmap."
        score = 1.0
    elif score <= 2.5:
        mode = "CRUISE"
        mode_label = "Cruise Mode • TUM Acceleration"
        badge_class = "optimal"
        desc = "Standard academic load. Maximum capacity allocated to raw LeetCode coding, Math R diagnostic mastery, and SIGG scanner."
    elif score <= 6.0:
        mode = "BALANCED"
        mode_label = "Balanced Mode • Dual Track Focus"
        badge_class = "lavender"
        hw_info = f", {len(urgent_homework)} urgent hw" if urgent_homework else ""
        desc = f"Moderate academic load ({len(tier_1_exams) + len(tier_2_exams)} exam(s){hw_info}). SGH library deep work calibrated between test prep and core TUM deliverables."
    else:
        mode = "SURGE"
        mode_label = "Surge Protocol • High Academic Density"
        badge_class = "amber"
        hw_info = f", {len(urgent_homework)} urgent homework" if urgent_homework else ""
        desc = f"High academic load ({len(tier_1_exams) + len(tier_2_exams)} upcoming test(s){hw_info}). SGH deep work blocks dynamically re-routed to phased exam defense and submission clearance."

    if close_conn:
        conn.close()

    future_exams = [e for e in exams if e.get("days_left", 0) >= 1 and not e.get("is_travel_excused")]
    today_exams = [e for e in exams if e.get("days_left", 0) == 0]

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
        "upcoming_exams": future_exams,
        "today_exams": today_exams,
        "all_exams": exams,
        "homework_count": len(homework),
        "urgent_homework_count": len(urgent_homework),
        "urgent_homework": urgent_homework,
        "active_homework": active_homework,
        "vulnerabilities": vulnerabilities,
        "is_us_travel_mode": is_travel,
    }


def synthesize_adaptive_schedule(
    base_schedule: Dict[str, Any],
    date_str: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, Any]:
    """
    Takes the static base routine and dynamically shapes the daily plan and study blocks
    depending on upcoming tests, essays, homework deadlines, live subject grades, and travel protocols.
    - US Travel Mode (Oct 4–18): Suspends Warsaw timetable and schedules hotel deep work.
    - Exam Day (T-0): Written test is excluded from afternoon study blocks.
    - Non-Defense Days: SGH Library block embeds active station TUM Roadmap deliverable.
    """
    schedule = dict(base_schedule)
    blocks = [dict(b) for b in schedule.get("blocks", [])]
    analysis = get_workload_analysis(date_str, conn=conn)

    schedule["workload"] = analysis

    target_dt = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else datetime.now().date()
    weekday = target_dt.weekday()  # Monday=0, ... Saturday=5, Sunday=6
    is_weekend = weekday in (5, 6)

    # --------------------------------------------------------------------------
    # 0. US TRAVEL PROTOCOL (Oct 4–18, 2026)
    # --------------------------------------------------------------------------
    if analysis.get("is_us_travel_mode"):
        station_id = get_active_station_id(target_dt)
        delivs = kill_list_controller.get_station_deliverables(station_id, conn=conn)
        chosen_deliv = next((d for d in delivs if not d.get("is_completed")), (delivs[0] if delivs else None))
        spec = (chosen_deliv.get("next_spec") if chosen_deliv else None) or {
            "title": "LeetCode Unassisted & Math R",
            "target_spec": "Solve 1 problem without AI & review Math R",
            "action_type": "url",
            "target_path": "https://leetcode.com/problemset/all/",
            "category": "Algorithms",
            "quantity": 1,
        }
        travel_blocks = [
            {
                "time": "08:30 – 09:30",
                "focus": "Morning Fuel & US Launch",
                "activity": "Wake up, hydration, high-protein breakfast, plan day exploration/program.",
                "type": "routine",
            },
            {
                "time": "10:00 – 11:30",
                "focus": f"US Hotel Deep Work • TUM Roadmap: {spec['title']}",
                "activity": f"[US Hotel Sprint // {station_id}] 60m {spec['target_spec']} + 30m self-correction & vocabulary review.",
                "type": "deep_work",
                "is_tum_roadmap": True,
                "is_school_dedicated": False,
                "is_us_travel": True,
                "deliverable": {
                    "deliverable_id": chosen_deliv["deliverable_id"] if chosen_deliv else "us_hotel_sprint",
                    "station_id": station_id,
                    "title": spec["title"],
                    "category": spec["category"],
                    "target_spec": spec["target_spec"],
                    "action_type": spec["action_type"],
                    "target_path": spec["target_path"],
                    "quantity": spec["quantity"],
                    "completed_count": chosen_deliv["completed_count"] if chosen_deliv else 0,
                    "total_required": chosen_deliv["total_required"] if chosen_deliv else 15,
                    "unit_label": chosen_deliv["unit_label"] if chosen_deliv else "exercises",
                } if chosen_deliv else None,
            },
            {
                "time": "11:30 – 18:30",
                "focus": "US Travel Program & Cultural Immersion",
                "activity": "Scheduled trip activities, city transit, cultural immersion, conferences, and exploration.",
                "type": "travel",
            },
            {
                "time": "18:30 – 19:15",
                "focus": "Hotel Fitness & Mobility Routine",
                "activity": "45 min hotel room / gym bodyweight workout (pushups, core circuit, mobility).",
                "type": "training",
            },
            {
                "time": "19:30 – 21:00",
                "focus": "Dinner & Travel Log",
                "activity": "High-protein dinner, hydration, quick day reflection log.",
                "type": "nutrition",
            },
            {
                "time": "21:00 – 22:30",
                "focus": "Evening Wind Down & Read",
                "activity": "Decompress, read, zero cognitive strain.",
                "type": "rest",
            },
            {
                "time": "22:30 – 07:30",
                "focus": "Restful Sleep (9 hrs)",
                "activity": "Deep physical recovery & circadian alignment.",
                "type": "sleep",
            },
        ]
        schedule["blocks"] = travel_blocks
        schedule["name"] = f"US Travel Protocol ({target_dt.strftime('%A')})"
        schedule["description"] = "Warsaw timetable suspended. 90m hotel deep work on active TUM Roadmap deliverable."
        return schedule

    exams = analysis.get("upcoming_exams", [])
    homework = analysis.get("urgent_homework", []) + analysis.get("active_homework", [])

    # Identify acute writing tasks (essays due in 1 to 2 days)
    acute_essays = [h for h in homework if h.get("is_essay") and 1 <= h.get("days_left", 99) <= 2]
    # Identify acute exams (exams due in 1 to 2 days - NEVER days_left == 0)
    acute_exams = [e for e in exams if 1 <= e.get("days_left", 99) <= 2]

    # Active station deliverable lookup for non-defense TUM embedding
    active_station_id = get_active_station_id(target_dt)
    station_delivs = kill_list_controller.get_station_deliverables(active_station_id, conn=conn)
    top_deliv = next((d for d in station_delivs if not d.get("is_completed")), (station_delivs[0] if station_delivs else None))
    deliv_spec = top_deliv.get("next_spec") if top_deliv else {
        "title": "LeetCode Unassisted & Math R",
        "target_spec": "Solve 1 problem without AI & review Math R",
        "action_type": "url",
        "target_path": "https://leetcode.com/problemset/all/",
        "category": "Algorithms",
        "quantity": 1,
    }

    # --------------------------------------------------------------------------
    # 1. WEEKEND ADAPTATION: Inject structured study blocks if heavy load looms
    # --------------------------------------------------------------------------
    if is_weekend:
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
    # Identify acute writing tasks (essays due in 1 to 2 days)
    acute_essays = [h for h in homework if h.get("is_essay") and 1 <= h.get("days_left", 99) <= 2]
    # Identify acute exams (exams due in 1 to 2 days - NEVER days_left == 0)
    acute_exams = [e for e in exams if 1 <= e.get("days_left", 99) <= 2]
    # Identify major vulnerable exams in 3 days
    impending_major = [
        e for e in exams
        if e.get("days_left", 99) == 3 and (e.get("is_vulnerable") or classify_obligation(e)["type"] == "major_exam")
    ]
    urgent_academic_exams = acute_exams + impending_major
    today_exams = analysis.get("today_exams", [])
    urgent_hw = analysis.get("urgent_homework", [])

    has_acute_defense = bool(acute_essays) or bool(urgent_academic_exams) or bool(urgent_hw)

    deliv_dict = {
        "deliverable_id": top_deliv["deliverable_id"] if top_deliv else "sgh_tum_roadmap",
        "station_id": active_station_id,
        "title": deliv_spec["title"],
        "category": deliv_spec["category"],
        "target_spec": deliv_spec["target_spec"],
        "action_type": deliv_spec["action_type"],
        "target_path": deliv_spec["target_path"],
        "quantity": deliv_spec["quantity"],
        "completed_count": top_deliv["completed_count"] if top_deliv else 0,
        "total_required": top_deliv["total_required"] if top_deliv else 15,
        "unit_label": top_deliv["unit_label"] if top_deliv else "exercises",
    } if top_deliv else None

    for b in blocks:
        is_deep_work = b.get("type") == "deep_work" or "SGH Library" in b.get("focus", "")
        if not is_deep_work:
            continue

        b["is_surge"] = (analysis["mode"] == "SURGE")

        # Scenario A: Acute Essay Due in <= 2 days
        if acute_essays:
            top_essay = acute_essays[0]
            phased = generate_phased_study_action(
                top_essay,
                days_left=top_essay.get("days_left", 1),
                subject_gpa=top_essay.get("subject_gpa"),
            )
            b["focus"] = phased["focus"]
            b["activity"] = phased["activity"]
            b["is_school_dedicated"] = True
            b["is_tum_roadmap"] = False
            b["deliverable"] = None

        # Scenario B: Multiple Urgent Exams in Acute Window (2+ due in <= 2 days)
        elif len(urgent_academic_exams) >= 2:
            e1, e2 = urgent_academic_exams[0], urgent_academic_exams[1]
            b["focus"] = f"Deep Work • Dual Defense: {e1['subject']} + {e2['subject']}"
            b["activity"] = (
                f"[{analysis['mode']} // Acute Dual Defense] 50m {e1['subject']} ({e1['title']}) problem drill + "
                f"45m {e2['subject']} ({e2['title']}) concept check + 25m TUM LeetCode anchor."
            )
            b["is_school_dedicated"] = True
            b["is_tum_roadmap"] = False
            b["deliverable"] = None

        # Scenario C: Single Urgent Exam Due in <= 2 days
        elif urgent_academic_exams:
            top_exam = urgent_academic_exams[0]
            phased = generate_phased_study_action(
                top_exam,
                days_left=top_exam.get("days_left", 1),
                subject_gpa=top_exam.get("subject_gpa"),
            )
            b["focus"] = phased["focus"]
            b["activity"] = phased["activity"]
            b["is_school_dedicated"] = True
            b["is_tum_roadmap"] = False
            b["deliverable"] = None

        # Scenario D: Urgent Homework Due Tomorrow
        elif urgent_hw:
            hw = urgent_hw[0]
            phased = generate_phased_study_action(hw, days_left=hw.get("days_left", 1), subject_gpa=hw.get("subject_gpa"))
            b["focus"] = phased["focus"]
            b["activity"] = phased["activity"]
            b["is_school_dedicated"] = True
            b["is_tum_roadmap"] = False
            b["deliverable"] = None

        # Scenario E: Exam Written Today (T-0) -> Test cleared in morning, afternoon dedicated to TUM Roadmap
        elif today_exams:
            b["focus"] = f"SGH Library • TUM Deep Work: {deliv_spec['title']}"
            b["activity"] = (
                f"[TUM Victory Sprint // {active_station_id}] Morning examination cleared. "
                f"70m {deliv_spec['target_spec']} + 35m algorithm problem solving + 15m German vocabulary buffer."
            )
            b["is_school_dedicated"] = False
            b["is_tum_roadmap"] = True
            b["deliverable"] = deliv_dict

        # Scenario F: Non-Defense Day with Medium-Horizon Exam (Exam in 3 to 5 days, e.g. Chemia in 4d)
        elif exams and exams[0].get("days_left", 99) <= 5:
            e = exams[0]
            scope_info = f" ({e['scope'][:40]})" if e.get("scope") else ""
            b["focus"] = f"SGH Library • TUM Deep Work: {deliv_spec['title']} & {e['subject']} Preview"
            b["activity"] = (
                f"[TUM Roadmap Sprint // {active_station_id}] 60m {deliv_spec['target_spec']} + "
                f"35m {e['subject']} ({e['title']}) foundation prep{scope_info}: formulas & definitions + "
                f"15m German vocabulary recall."
            )
            b["is_school_dedicated"] = False
            b["is_tum_roadmap"] = True
            b["deliverable"] = deliv_dict

        # Scenario G: Pure Cruise Mode / Clear Academic Horizon -> 100% TUM Acceleration
        else:
            b["focus"] = f"SGH Library • TUM Deep Work: {deliv_spec['title']}"
            b["activity"] = (
                f"[TUM Roadmap Sprint // {active_station_id}] 65m {deliv_spec['target_spec']} + "
                f"35m self-correction & formula recall + 15m German vocabulary buffer."
            )
            b["is_school_dedicated"] = False
            b["is_tum_roadmap"] = True
            b["deliverable"] = deliv_dict

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
    Dynamically resolves station ID for the next two years.
    Guarantees that both academic defense and TUM Metro deliverables are present.
    """
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    target_dt = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else datetime.now().date()
    analysis = get_workload_analysis(date_str, conn=conn)
    school_items = []
    metro_items = []

    # 1. Urgent essays or homework (due tomorrow, days_left == 1)
    urgent_hw = analysis.get("urgent_homework", []) + [h for h in analysis.get("active_homework", []) if h.get("is_essay")]
    if urgent_hw:
        for hw in urgent_hw[:1]:
            school_items.append({
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

    # 2. Impending exam prep (strictly future exams, days_left >= 1)
    if analysis["upcoming_exams"]:
        for ex in analysis["upcoming_exams"][:1]:
            scope_desc = f" ({ex.get('scope', '')[:35]}...)" if ex.get("scope") else ""
            school_items.append({
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

    # 3. Dynamic 2-Year Sequential Metro deliverable progression (LeetCode & Math R)
    active_station = get_active_station_id(target_dt)
    deliverables = kill_list_controller.get_station_deliverables(active_station, conn=conn)
    for d in deliverables:
        d_id = d["deliverable_id"]
        next_spec = d.get("next_spec")
        if not next_spec or d["is_completed"]:
            continue

        if "leetcode" in d_id or "code" in d_id:
            metro_items.append({
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
            metro_items.append({
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
        elif "german" in d_id:
            metro_items.append({
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

    # Determine if today is an active academic defense day (acute test in 1-2 days or urgent homework)
    is_defense_day = bool(urgent_hw) or any(1 <= ex.get("days_left", 99) <= 2 for ex in analysis.get("upcoming_exams", []))
    if is_defense_day:
        final_recs = school_items[:2] + metro_items[:2]
        if len(final_recs) < 4:
            for m in metro_items[2:]:
                if len(final_recs) >= 4:
                    break
                final_recs.append(m)
    else:
        # Non-defense day: TUM Roadmap deliverables take absolute priority
        final_recs = metro_items[:3] + school_items[:1]
        if len(final_recs) < 4:
            for m in metro_items[3:]:
                if len(final_recs) >= 4:
                    break
                final_recs.append(m)
            for s in school_items[1:]:
                if len(final_recs) >= 4:
                    break
                final_recs.append(s)

    return final_recs[:4]

