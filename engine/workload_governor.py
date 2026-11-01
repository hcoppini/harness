"""
Harness 3.0 Autonomous Academic Workload Governor.
Analyzes school exam pressure, subject grade vulnerabilities, task archetypes (e.g. essays, exams),
and dynamically shapes daily SGH Library deep work blocks and weekend schedules.
Unifies school-first defense with long-term Matura Rozszerzona & TUM Heilbronn mastery.
"""

import re
import sqlite3
import json
from pathlib import Path
from datetime import datetime, timedelta, date
from typing import Dict, Any, List, Optional, Tuple

from app.db import get_connection
from engine import kill_list_controller
from engine import grade_parser

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
OPERATING_MODE_FILE = DATA_DIR / "operating_mode.json"

TIER_1_KEYWORDS = ["matematyka", "informatyka", "angielski", "math", "cs", "algorithm"]
ESSAY_KEYWORDS = ["esej", "rozprawka", "wypracowanie", "tekst", "opowiadanie", "charakterystyka", "analiza literacka", "praca pisemna"]
EXAM_MAJOR_KEYWORDS = ["sprawdzian", "praca klasowa", "test diagnostyczny", "arkusz", "matura", "egzamin"]
QUIZ_KEYWORDS = ["kartkówka", "kartkowka", "odpowiedź", "odpowiedz ustna", "wejściówka"]


def get_operating_mode() -> str:
    """
    Returns the current active system operating mode:
    - 'FORTRESS' (Default): Standard Warsaw Liceum, SGH deep work, high problem quotas.
    - 'FIELD': Travel / Away from workstation / Holiday. Suspends Warsaw schedules, reduces to unbreakable floor anchor.
    - 'SURGE_RECOVERY': Life recovery / Illness / Family surge. Preserves biological baseline floor (protein, sleep, log).
    """
    if OPERATING_MODE_FILE.exists():
        try:
            with open(OPERATING_MODE_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                mode = (cfg.get("mode") or "").strip().upper()
                if mode in ("FORTRESS", "FIELD", "SURGE_RECOVERY"):
                    return mode
        except Exception:
            pass
    return "FORTRESS"


def set_operating_mode(mode: str) -> Dict[str, Any]:
    """
    Sets the active system operating mode ('FORTRESS', 'FIELD', or 'SURGE_RECOVERY').
    """
    clean_mode = (mode or "").strip().upper()
    if clean_mode not in ("FORTRESS", "FIELD", "SURGE_RECOVERY"):
        return {"success": False, "error": f"Invalid mode: {mode}. Must be FORTRESS, FIELD, or SURGE_RECOVERY."}

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(OPERATING_MODE_FILE, "w", encoding="utf-8") as f:
        json.dump({"mode": clean_mode, "updated_at": datetime.now().isoformat()}, f, indent=2)
    return {"success": True, "mode": clean_mode}


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

    op_mode = get_operating_mode()
    is_travel = is_us_travel_date(target_dt) or (op_mode == "FIELD")
    is_recovery = (op_mode == "SURGE_RECOVERY")
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

        # Travel or Recovery protocol: exams occurring during trip/recovery are excused post-event
        if is_travel or is_recovery or is_us_travel_date(ex_date):
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

    # 2. Fetch pending homework (including overdue items that require triage)
    cursor.execute(
        """
        SELECT * FROM homework_items
        WHERE completed = 0 AND due_date <= ?
        ORDER BY due_date ASC
        """,
        (hw_end_dt.strftime("%Y-%m-%d"),),
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

        if is_travel or is_recovery or is_us_travel_date(h_date):
            h["is_travel_excused"] = True

        if not h.get("is_travel_excused"):
            # Acute homework deliverables due <= 24h: includes overdue (days_left <= 0) and due tomorrow (days_left == 1)
            if days_left <= 1:
                urgent_homework.append(h)
            elif 2 <= days_left <= 5:
                active_homework.append(h)

    # Sort urgent homework so today's deliverables (days_left == 0) and essays are triaged first
    urgent_homework.sort(key=lambda x: (
        0 if x.get("days_left") == 0 and x.get("is_essay") else (
            1 if x.get("days_left") == 0 else (
                2 if x.get("is_essay") else (
                    3 if x.get("days_left") == 1 else 4
                )
            )
        ),
        x.get("due_date", "")
    ))

    # 3. Check Ledger Tripwires: unexcused 'nb' marks, open 'np' tripwires, and failing marks <= 2.5
    try:
        cursor.execute("SELECT * FROM tum_grade_entries ORDER BY date ASC")
        all_grades = [dict(r) for r in cursor.fetchall()]
    except Exception:
        all_grades = []

    open_nb_marks = [
        g for g in all_grades
        if "nb" in (g.get("raw_input") or "").lower()
        or "nb" in (g.get("category") or "").lower()
        or "nieobecno" in (g.get("description") or "").lower()
    ]

    open_np_marks = [
        g for g in all_grades
        if "np" in (g.get("raw_input") or "").lower()
        or "nieprzygotowanie" in (g.get("category") or "").lower()
    ]

    failing_marks = [
        g for g in all_grades
        if g.get("numeric_value") is not None and g["numeric_value"] <= 2.5
    ]

    # 4. Check Scheduled Retakes (poprawy)
    try:
        cursor.execute("SELECT * FROM school_exams WHERE completed = 0")
        all_uncompleted_exams = [dict(r) for r in cursor.fetchall()]
    except Exception:
        all_uncompleted_exams = []

    scheduled_poprawy = [
        e for e in all_uncompleted_exams
        if "popraw" in (e.get("title") or "").lower() or "popraw" in (e.get("scope") or "").lower()
    ]

    # --------------------------------------------------------------------------
    # STATE MACHINE INVERSION: DEFENSE PROTOCOL IS THE PERSISTENT DEFAULT STATE.
    # CRUISE PROTOCOL only unlocks if and only if ALL THREE conditions pass:
    # 1. Active Homework Deliverables with due date <= 24h == 0.
    # 2. Zero unexcused nb marks open on the current semester ledger.
    # 3. No pending retakes (poprawy) scheduled for marks <= 3 (and zero open np tripwires).
    # --------------------------------------------------------------------------
    has_active_hw_le_24h = len(urgent_homework) > 0
    has_open_nb = len(open_nb_marks) > 0
    has_pending_retakes_or_tripwires = (len(scheduled_poprawy) > 0 or len(failing_marks) > 0 or len(open_np_marks) > 0)
    has_acute_exams = len(immediate_exams) > 0

    cruise_unlocked = (
        not has_active_hw_le_24h
        and not has_open_nb
        and not has_pending_retakes_or_tripwires
        and not has_acute_exams
    )

    # Composite Workload score calculation:
    score = (len(tier_1_exams) * 2.5) + (len(tier_2_exams) * 1.0)
    if immediate_exams:
        score += 2.0
    for e in exams:
        if e.get("is_vulnerable") and e.get("days_left", 0) >= 1 and not e.get("is_travel_excused"):
            score += 1.5
    if len(week_exams) > 1:
        score += (len(week_exams) - 1) * 1.5
    score += (len(urgent_homework) * 2.0)
    for h in homework:
        if h.get("is_essay") and h.get("days_left", 99) <= 2 and not h.get("is_travel_excused"):
            score += 2.5
        elif h.get("is_vulnerable") and h.get("days_left", 99) <= 2 and not h.get("is_travel_excused"):
            score += 1.5
    score += (len(active_homework) * 0.5)

    if is_travel:
        mode = "TRAVEL"
        mode_label = "Field Mode • Minimal Maintenance Floor"
        badge_class = "travel"
        desc = "Field / Travel Mode Active. Warsaw Liceum timetable suspended. School surge frozen. 60m minimal maintenance study hour to keep pace with zero guilt. Enjoy your trip."
        score = 1.0
    elif is_recovery:
        mode = "SURGE_RECOVERY"
        mode_label = "Surge Recovery • Biological Baseline Floor"
        badge_class = "travel"
        desc = "Life Recovery / Family Surge Mode Active. High-friction deadlines excused. Priority on biological baseline, sleep, protein, and micro-habits."
        score = 1.0
    elif score > 6.0:
        mode = "SURGE"
        mode_label = "Surge Protocol • High Academic Density"
        badge_class = "amber"
        hw_info = f", {len(urgent_homework)} urgent homework" if urgent_homework else ""
        desc = f"High academic load ({len(tier_1_exams) + len(tier_2_exams)} upcoming test(s){hw_info}). SGH deep work blocks dynamically re-routed to phased exam defense and submission clearance."
    elif not cruise_unlocked:
        mode = "DEFENSE"
        mode_label = "Defense Protocol • School Triage"
        badge_class = "surge"
        triage_reasons = []
        if has_active_hw_le_24h:
            triage_reasons.append(f"{len(urgent_homework)} homework deliverable(s) due ≤24h")
        if has_open_nb:
            triage_reasons.append(f"{len(open_nb_marks)} unexcused nb mark(s)")
        if scheduled_poprawy:
            triage_reasons.append(f"{len(scheduled_poprawy)} scheduled retake(s)")
        if failing_marks:
            triage_reasons.append(f"{len(failing_marks)} failing mark(s) ≤2.5")
        if open_np_marks:
            triage_reasons.append(f"{len(open_np_marks)} open np tripwire(s)")
        if has_acute_exams:
            triage_reasons.append(f"{len(immediate_exams)} acute exam(s) in ≤2d")
        reason_str = ", ".join(triage_reasons) if triage_reasons else "Active school defense commitments"
        desc = f"DEFENSE PROTOCOL LOCKED: {reason_str}. Long-term aspirational work suspended until school triage is cleared."
    elif score > 2.5:
        mode = "BALANCED"
        mode_label = "Balanced Mode • Dual Track Focus"
        badge_class = "lavender"
        desc = "Moderate academic load. All acute defense conditions cleared; balanced SGH deep work."
    else:
        mode = "CRUISE"
        mode_label = "Cruise Mode • TUM Acceleration"
        badge_class = "optimal"
        desc = "CRUISE PROTOCOL UNLOCKED: 0 acute homework ≤24h, 0 open nb marks, 0 pending retakes. 100% capacity focused on TUM roadmap & Matura R."

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
        "open_nb_count": len(open_nb_marks),
        "open_nb_marks": open_nb_marks,
        "scheduled_poprawy_count": len(scheduled_poprawy),
        "scheduled_poprawy": scheduled_poprawy,
        "failing_marks_count": len(failing_marks),
        "open_np_count": len(open_np_marks),
        "cruise_unlocked": cruise_unlocked,
        "vulnerabilities": vulnerabilities,
        "is_us_travel_mode": is_travel,
        "is_recovery_mode": is_recovery,
        "operating_mode": op_mode,
    }


def parse_block_net_minutes(time_str: str, default_minutes: int = 110) -> Tuple[int, str]:
    """
    Parses a time window string (e.g. '14:30 – 16:30' or '14:30 - 16:00') into:
    (net_minutes, cutoff_time_str).
    Subtracts a 10-minute commute buffer when total duration >= 90 minutes.
    """
    try:
        parts = time_str.replace("–", "-").split("-")
        if len(parts) == 2:
            s_h, s_m = [int(p) for p in parts[0].strip().split(":")]
            e_h, e_m = [int(p) for p in parts[1].strip().split(":")]
            total_duration = (e_h * 60 + e_m) - (s_h * 60 + s_m)
            cutoff_str = parts[1].strip()
            buffer = 10 if total_duration >= 90 else (5 if total_duration >= 60 else 0)
            net = max(15, total_duration - buffer)
            return net, cutoff_str
    except Exception:
        pass
    return default_minutes, "16:30"


def compute_phase_durations(total_net_min: int, scenario_type: str) -> Tuple[int, int, int]:
    """
    Allocates exact minutes across 3 execution phases so that:
    phase_1 + phase_2 + phase_3 == total_net_min (100% exact parity).
    """
    if scenario_type in ("acute_school_defense", "urgent_hw"):
        p1 = int(round(total_net_min * 0.41))
        p2 = int(round(total_net_min * 0.41))
        p3 = max(10, total_net_min - p1 - p2)
        p1 = total_net_min - p2 - p3
        return p1, p2, p3
    elif scenario_type == "acute_essay":
        p1 = int(round(total_net_min * 0.36))
        p2 = int(round(total_net_min * 0.41))
        p3 = max(10, total_net_min - p1 - p2)
        p1 = total_net_min - p2 - p3
        return p1, p2, p3
    elif scenario_type == "medium_horizon":
        p3 = int(round(total_net_min * 0.55))
        rem = total_net_min - p3
        p1 = rem // 2
        p2 = rem - p1
        return p1, p2, p3
    elif scenario_type == "pure_tum":
        p1 = int(round(total_net_min * 0.45))
        p2 = int(round(total_net_min * 0.32))
        p3 = max(10, total_net_min - p1 - p2)
        p1 = total_net_min - p2 - p3
        return p1, p2, p3
    elif scenario_type == "us_travel":
        # 60m minimal maintenance hour: 30m anchor deliverable + 15m review/proofs + 15m German vocab
        p1 = int(round(total_net_min * 0.50))
        p2 = int(round(total_net_min * 0.25))
        p3 = total_net_min - p1 - p2
        return p1, p2, p3
    else:
        p1 = total_net_min // 3
        p2 = total_net_min // 3
        p3 = total_net_min - p1 - p2
        return p1, p2, p3


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
    # 0A. SURGE RECOVERY PROTOCOL (Illness / Jet lag / Family Emergency)
    # --------------------------------------------------------------------------
    if analysis.get("is_recovery_mode") or analysis.get("mode") == "SURGE_RECOVERY":
        recovery_blocks = [
            {
                "time": "08:30 – 09:30",
                "focus": "Morning Fuel & Launch",
                "activity": "Gentle wake up, hydration, high-protein breakfast. Nervous system recovery.",
                "type": "routine",
            },
            {
                "time": "10:00 – 10:45",
                "focus": "Biological Floor • Micro-Habits (45m)",
                "activity": "[Unbreakable Floor] 20m mobile German Anki vocabulary + 15m review/planning + 10m mental check-in. Momentum sustained; zero guilt.",
                "type": "deep_work",
                "is_tum_roadmap": True,
                "is_school_dedicated": False,
                "net_minutes": 45,
            },
            {
                "time": "12:00 – 18:30",
                "focus": "Rest, Family Duties & Life Recovery",
                "activity": "Family obligations, restorative downtime, low cognitive load. Zero academic guilt.",
                "type": "rest",
            },
            {
                "time": "18:30 – 19:15",
                "focus": "Light Mobility & Walk",
                "activity": "45 min outdoor walk, fresh air, light mobility/stretching.",
                "type": "training",
            },
            {
                "time": "19:30 – 21:00",
                "focus": "High-Protein Dinner & Daily Log",
                "activity": "Nutritious dinner, protein target met, 60-second status check-in on Harness.",
                "type": "nutrition",
            },
            {
                "time": "21:00 – 22:30",
                "focus": "Evening Wind Down & Read",
                "activity": "Decompress, read, zero screen glare before bed.",
                "type": "rest",
            },
            {
                "time": "22:30 – 07:30",
                "focus": "Restorative Sleep (9 hrs)",
                "activity": "Deep cellular and nervous system recovery.",
                "type": "sleep",
            },
        ]
        schedule["blocks"] = recovery_blocks
        schedule["name"] = f"Recovery Protocol ({target_dt.strftime('%A')})"
        schedule["description"] = "Life Recovery / Family Surge Mode Active. High-friction commitments paused. Biological floor and streak preserved."
        return schedule

    # --------------------------------------------------------------------------
    # 0B. FIELD / TRAVEL PROTOCOL (Away from Warsaw workstation)
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
        net_min, cutoff_str = parse_block_net_minutes("09:30 – 10:30", default_minutes=60)
        p1, p2, p3 = compute_phase_durations(net_min, "us_travel")
        travel_blocks = [
            {
                "time": "08:30 – 09:30",
                "focus": "Morning Fuel & Launch",
                "activity": "Wake up, hydration, high-protein breakfast, plan day exploration/activities.",
                "type": "routine",
            },
            {
                "time": "09:30 – 10:30",
                "focus": f"US Hotel Deep Work • 60m Maintenance Anchor: {spec['title']}",
                "activity": f"[US Travel Maintenance // {station_id}] 60m low-friction anchor: {p1}m {spec['target_spec']} + {p2}m self-correction + {p3}m German vocabulary. Momentum sustained; zero guilt.",
                "type": "deep_work",
                "is_tum_roadmap": True,
                "is_school_dedicated": False,
                "is_us_travel": True,
                "net_minutes": net_min,
                "commute_cutoff": cutoff_str,
                "plan_phases": [
                    {
                        "phase_num": 1,
                        "phase_key": "study_school",
                        "badge_label": "[1. TUM ROADMAP ANCHOR]",
                        "duration_min": p1,
                        "title": f"TUM Deliverable: {spec['title']}",
                        "description": f"{p1}m {spec['target_spec']}.\nMilestone: {spec['category']} • Station {station_id}.",
                        "type": "tum_deliverable",
                        "color": "var(--accent-lavender)",
                    },
                    {
                        "phase_num": 2,
                        "phase_key": "study_matura",
                        "badge_label": "[2. ACTIVE REVIEW]",
                        "duration_min": p2,
                        "title": "Unassisted Proofs & Error Analysis",
                        "description": f"{p2}m self-correction and mathematical proofs verification without external aids.",
                        "type": "matura_r",
                        "color": "#0284c7",
                    },
                    {
                        "phase_num": 3,
                        "phase_key": "study_code",
                        "badge_label": "[3. GERMAN VOCABULARY]",
                        "duration_min": p3,
                        "title": "German A2 Vocabulary Recall",
                        "description": f"{p3}m active recall of German A2 vocabulary and grammar structures.",
                        "type": "german_code",
                        "color": "#10b981",
                    },
                ],
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
                "time": "10:30 – 18:30",
                "focus": "Travel Program, Exploration & Free Time",
                "activity": "Scheduled trip activities, city transit, cultural immersion, boxing, and exploration. Zero guilt.",
                "type": "travel",
            },
            {
                "time": "18:30 – 19:15",
                "focus": "Fitness & Mobility Routine",
                "activity": "45 min hotel workout / gym / running session (pushups, mobility, or run).",
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
        schedule["description"] = "Travel Mode Active (Oct 4–18). Warsaw schedule suspended. 60m minimal maintenance anchor to keep pace with zero guilt. Enjoy your trip."
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
                net_min, cutoff_str = parse_block_net_minutes(time_slot, default_minutes=80)
                p1, p2, p3 = compute_phase_durations(net_min, "acute_school_defense")
                scope_str = primary_ob.get("scope") or primary_ob.get("title") or ""
                weekend_block = {
                    "time": time_slot,
                    "focus": f"Weekend Deep Work • {primary_ob['subject']} Defense",
                    "type": "study_block",
                    "activity": phased["activity"],
                    "is_school_dedicated": True,
                    "is_surge": analysis["mode"] == "SURGE",
                    "net_minutes": net_min,
                    "commute_cutoff": cutoff_str,
                    "plan_phases": [
                        {
                            "phase_num": 1,
                            "phase_key": "study_school",
                            "badge_label": "[1. SCOPE & THEORY BLITZ]",
                            "duration_min": p1,
                            "title": f"{primary_ob['subject']}: Core Theory, Definitions & Formulas",
                            "description": f"{p1}m active recall of {primary_ob['subject']} concepts ({scope_str[:40]}). Formulate flashcards.",
                            "type": "school_defense",
                            "color": "var(--accent-lavender)",
                        },
                        {
                            "phase_num": 2,
                            "phase_key": "study_matura",
                            "badge_label": "[2. PROBLEM DRILLS & PAST PAPERS]",
                            "duration_min": p2,
                            "title": f"{primary_ob['subject']}: Past Papers & Timed Drills",
                            "description": f"{p2}m unassisted problem solving on {primary_ob['subject']}. Red-pen verification.",
                            "type": "school_defense",
                            "color": "#0284c7",
                        },
                        {
                            "phase_num": 3,
                            "phase_key": "study_code",
                            "badge_label": "[3. ERROR BANK & MOCK BLITZ]",
                            "duration_min": p3,
                            "title": f"{primary_ob['subject']}: Error Bank & High-Yield Blitz",
                            "description": f"{p3}m rapid-fire drill of past mistakes and edge cases.",
                            "type": "school_defense",
                            "color": "#10b981",
                        },
                    ],
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
    acute_essays = [h for h in homework if h.get("is_essay") and 1 <= h.get("days_left", 99) <= 2]
    acute_exams = [e for e in exams if 1 <= e.get("days_left", 99) <= 2]
    today_exams = analysis.get("today_exams", [])
    urgent_hw = analysis.get("urgent_homework", [])

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
        time_slot = b.get("time", "14:30 – 16:30")
        net_min, cutoff_str = parse_block_net_minutes(time_slot, default_minutes=110)
        b["net_minutes"] = net_min
        b["commute_cutoff"] = cutoff_str

        # Scenario A: Acute Essay Due in <= 2 days
        if acute_essays:
            top_essay = acute_essays[0]
            p1, p2, p3 = compute_phase_durations(net_min, "acute_essay")
            b["focus"] = f"Deep Work • Essay Drafting: {top_essay['subject']}"
            b["activity"] = (
                f"[Essay Defense // T-{top_essay.get('days_left', 1)}] Thesis & Textual Evidence + "
                f"Full Drafting Sprint (400+ words) + Polish & Citation Check."
            )
            b["is_school_dedicated"] = True
            b["is_tum_roadmap"] = False
            b["deliverable"] = None
            b["plan_phases"] = [
                {
                    "phase_num": 1,
                    "phase_key": "study_school",
                    "badge_label": "[1. THESIS & EVIDENCE]",
                    "unit_target": "Outline + 3 Textual Citations",
                    "proof_type": "paper_ink",
                    "duration_min": p1,
                    "title": f"{top_essay['subject']}: Thesis & Source Text Quotes",
                    "description": f"Verify prompt criteria, structure central arguments, and extract exact quotes from source material ({top_essay['title']}).",
                    "type": "school_defense",
                    "color": "var(--accent-lavender)",
                },
                {
                    "phase_num": 2,
                    "phase_key": "study_matura",
                    "badge_label": "[2. DRAFTING SPRINT]",
                    "unit_target": "Complete 400+ Word Core Draft",
                    "proof_type": "paper_ink",
                    "duration_min": p2,
                    "title": f"{top_essay['subject']}: Rapid Drafting & Body Arguments",
                    "description": "Continuous writing sprint for core body paragraphs, counter-arguments, and synthesis. Finite ink/doc deliverable.",
                    "type": "school_defense",
                    "color": "#0284c7",
                },
                {
                    "phase_num": 3,
                    "phase_key": "study_code",
                    "badge_label": "[3. FINAL POLISH & FORMAT]",
                    "unit_target": "Final Submission Ready Document",
                    "proof_type": "completed_artifact",
                    "duration_min": p3,
                    "title": f"{top_essay['subject']}: Stylistic Polish & Citation Check",
                    "description": "Sentence flow, vocabulary richness, punctuation audit, word count verification, and final submission readiness.",
                    "type": "school_defense",
                    "color": "#10b981",
                },
            ]

        # Scenario B: Single Nearest Exam Dominance (1 to 2 days out)
        elif acute_exams:
            top_exam = acute_exams[0]
            p1, p2, p3 = compute_phase_durations(net_min, "acute_school_defense")
            scope_str = top_exam.get("scope") or top_exam.get("title") or ""
            b["focus"] = f"Deep Work • {top_exam['subject']} Prep: Acute Defense"
            b["activity"] = (
                f"[Acute Defense // T-{top_exam.get('days_left', 1)}] {top_exam['subject']} Scope & Core Theory + "
                f"6 Past Paper Problems + Error Bank Blitz."
            )
            b["is_school_dedicated"] = True
            b["is_tum_roadmap"] = False
            b["deliverable"] = None
            b["plan_phases"] = [
                {
                    "phase_num": 1,
                    "phase_key": "study_school",
                    "badge_label": "[1. SCOPE & THEORY BLITZ]",
                    "unit_target": "1 Condensed Formula/Concept Sheet",
                    "proof_type": "paper_ink",
                    "duration_min": p1,
                    "title": f"{top_exam['subject']}: Core Theory, Definitions & Formulas",
                    "description": f"{p1}m active recall of {top_exam['subject']} concepts ({scope_str[:40]}). Formulate flashcards and synthesize cheat sheet.",
                    "type": "school_defense",
                    "color": "var(--accent-lavender)",
                },
                {
                    "phase_num": 2,
                    "phase_key": "study_matura",
                    "badge_label": "[2. PROBLEM DRILLS & PAST PAPERS]",
                    "unit_target": "6 Unassisted Problems (Self-Corrected)",
                    "proof_type": "cke_tasks",
                    "duration_min": p2,
                    "title": f"{top_exam['subject']}: Past Papers & Timed Drills",
                    "description": f"{p2}m unassisted problem solving on {top_exam['subject']} ({top_exam.get('title')}). Red-pen verification and immediate mistake logging.",
                    "type": "school_defense",
                    "color": "#0284c7",
                },
                {
                    "phase_num": 3,
                    "phase_key": "study_code",
                    "badge_label": "[3. ERROR BANK & MOCK BLITZ]",
                    "unit_target": "5 Edge Cases / Trap Cards Logged",
                    "proof_type": "problem_count",
                    "duration_min": p3,
                    "title": f"{top_exam['subject']}: Error Bank & High-Yield Blitz",
                    "description": f"{p3}m rapid-fire drill of past mistakes, edge cases, and high-frequency exam traps before morning clearance.",
                    "type": "school_defense",
                    "color": "#10b981",
                },
            ]

        # Scenario C: Defense Protocol Active OR Urgent Homework Due <= 24h
        elif analysis.get("mode") == "DEFENSE" or urgent_hw:
            p1, p2, p3 = compute_phase_durations(net_min, "urgent_hw")
            primary_hw = urgent_hw[0] if urgent_hw else None
            second_hw = urgent_hw[1] if len(urgent_hw) > 1 else None
            open_nbs = analysis.get("open_nb_marks", [])
            retakes = analysis.get("scheduled_poprawy", [])

            b["focus"] = "Deep Work • School Defense Triage"
            b["activity"] = (
                "[DEFENSE TRIAGE] Forceful assignment to school clearance: "
                "acute homework due <= 24h, test retake problem sets, and open nb lab triage."
            )
            b["is_school_dedicated"] = True
            b["is_tum_roadmap"] = False
            b["deliverable"] = None

            # Phase 1: Primary Urgent Homework Deliverable
            if primary_hw:
                p1_title = f"{primary_hw['subject']}: Complete {primary_hw['title']}"
                p1_desc = f"Resolve all required exercises for {primary_hw['title']}. Step-by-step documentation in ink on paper."
                p1_unit = f"Complete {primary_hw['subject']} HW (Ink)"
            else:
                p1_title = "School Triage: Immediate Homework Clearance"
                p1_desc = "Audit classroom agenda and complete all outstanding homework deliverables on paper."
                p1_unit = "1 Complete HW Sheet (Ink)"

            # Phase 2: Secondary Homework OR Retake Problem Sets
            if second_hw:
                p2_title = f"{second_hw['subject']}: Complete {second_hw['title']}"
                p2_desc = f"Solve required problem set for {second_hw['title']}. Check answers against textbook/class notes."
                p2_unit = f"Complete {second_hw['subject']} HW (Paper)"
            elif retakes:
                top_retake = retakes[0]
                p2_title = f"Exam Retake Defense: {top_retake['subject']} ({top_retake['title']})"
                p2_desc = f"Solve and self-correct 4 practice problems targeting failed exam topics ({top_retake.get('scope', '')[:35]})."
                p2_unit = "4 Retake Problems (Self-Corrected)"
            else:
                p2_title = "Vulnerability Defense: Re-solving Failed Test Problems"
                p2_desc = "Re-solve 4 problems from past low kartkówka / sprawdzian marks (History / CS / Geography) with red-pen self-correction."
                p2_unit = "4 Past Problems (Self-Corrected)"

            # Phase 3: Open nb Absence Clearance OR Next-Day Prep
            if open_nbs:
                top_nb = open_nbs[0]
                p3_title = f"Clear Open Absence (nb): {top_nb.get('subject', 'School')} ({top_nb.get('description', '')[:30]})"
                p3_desc = "Complete missed class lab exercise or synthesize 1 page of lesson notes to clear open unexcused nb mark."
                p3_unit = "1 Lab Script / Class Notes Sheet"
            else:
                p3_title = "Next-Day Syllabus & Questioning Buffer"
                p3_desc = "Preview tomorrow's syllabus topics so you are never caught unprepared during active classroom questioning."
                p3_unit = "Tomorrow's Lesson Preview Notes"

            b["plan_phases"] = [
                {
                    "phase_num": 1,
                    "phase_key": "study_school",
                    "badge_label": "[1. HOMEWORK PROOF OF WORK]",
                    "unit_target": p1_unit,
                    "proof_type": "paper_ink",
                    "duration_min": p1,
                    "title": p1_title,
                    "description": p1_desc,
                    "type": "school_defense",
                    "color": "var(--accent-lavender)",
                },
                {
                    "phase_num": 2,
                    "phase_key": "study_matura",
                    "badge_label": "[2. RETAKE / DEFICIT DRILL]",
                    "unit_target": p2_unit,
                    "proof_type": "problem_count",
                    "duration_min": p2,
                    "title": p2_title,
                    "description": p2_desc,
                    "type": "school_defense",
                    "color": "#0284c7",
                },
                {
                    "phase_num": 3,
                    "phase_key": "study_code",
                    "badge_label": "[3. NB / CLASS PREP]",
                    "unit_target": p3_unit,
                    "proof_type": "completed_artifact",
                    "duration_min": p3,
                    "title": p3_title,
                    "description": p3_desc,
                    "type": "school_defense",
                    "color": "#10b981",
                },
            ]

        # Scenario D: Exam Written Today (T-0) -> Morning cleared, 100% TUM Metro Pipeline
        elif today_exams:
            p1, p2, p3 = compute_phase_durations(net_min, "pure_tum")
            b["focus"] = f"SGH Library • TUM Deep Work: {deliv_spec['title']}"
            b["activity"] = (
                f"[TUM Victory Sprint // {active_station_id}] Morning examination cleared. "
                f"1 TUM Milestone Rep + 4 CKE Matura R Tasks + 20 German A2 Vocab Units."
            )
            b["is_school_dedicated"] = False
            b["is_tum_roadmap"] = True
            b["deliverable"] = deliv_dict
            b["plan_phases"] = [
                {
                    "phase_num": 1,
                    "phase_key": "study_school",
                    "badge_label": "[1. TUM ROADMAP • REPS]",
                    "unit_target": "1 Milestone Rep (Unassisted)",
                    "proof_type": "code_or_math",
                    "duration_min": p1,
                    "title": f"TUM Roadmap: {deliv_spec['title']}",
                    "description": f"{deliv_spec['target_spec']}.\nMorning test cleared! Full momentum on TUM Heilbronn track.",
                    "type": "tum_deliverable",
                    "color": "var(--accent-lavender)",
                },
                {
                    "phase_num": 2,
                    "phase_key": "study_matura",
                    "badge_label": "[2. MATURA R • PROBLEM COUNT]",
                    "unit_target": "4 CKE Exam Tasks (Self-Corrected)",
                    "proof_type": "cke_tasks",
                    "duration_min": p2,
                    "title": "Matura R Mathematics: Analytical & Advanced Proofs",
                    "description": "Complete and self-correct 4 CKE tasks (2023 May exam). Traced on paper, red-pen self-correction.",
                    "type": "matura_r",
                    "color": "#0284c7",
                },
                {
                    "phase_num": 3,
                    "phase_key": "study_code",
                    "badge_label": "[3. GERMAN / LEETCODE • UNIT COUNT]",
                    "unit_target": "20 Vocab Cards or 1 LeetCode Commit",
                    "proof_type": "vocab_or_git",
                    "duration_min": p3,
                    "title": "German A2 (Nicos Weg) & Algorithmic Recall",
                    "description": "Master 20 German A2 vocabulary cards (Nicos Weg) or commit 1 clean algorithm solution to Git.",
                    "type": "german_code",
                    "color": "#10b981",
                },
            ]

        # Scenario E: Medium-Horizon Exam (3 to 5 days out) -> 50/50 Balanced Foundation
        elif exams and exams[0].get("days_left", 99) <= 5:
            e = exams[0]
            p1, p2, p3 = compute_phase_durations(net_min, "medium_horizon")
            scope_info = f" ({e['scope'][:40]})" if e.get("scope") else ""
            b["focus"] = f"SGH Library • TUM Deep Work: {deliv_spec['title']} & {e['subject']} Foundation"
            b["activity"] = (
                f"[TUM Roadmap & Foundation // {active_station_id}] 1 Formula Sheet + "
                f"4 Theorem Proofs + {deliv_spec['target_spec']}."
            )
            b["is_school_dedicated"] = False
            b["is_tum_roadmap"] = True
            b["deliverable"] = deliv_dict
            b["plan_phases"] = [
                {
                    "phase_num": 1,
                    "phase_key": "study_school",
                    "badge_label": "[1. EXAM SCOPE MAPPING]",
                    "unit_target": "1 Concept & Scope Map",
                    "proof_type": "paper_ink",
                    "duration_min": p1,
                    "title": f"{e['subject']} (in {e['days_left']}d): Scope & Core Definitions",
                    "description": f"Structured mapping of {e['subject']} exam material{scope_info}. Formulate flashcards.",
                    "type": "school_defense",
                    "color": "var(--accent-lavender)",
                },
                {
                    "phase_num": 2,
                    "phase_key": "study_matura",
                    "badge_label": "[2. THEOREM & FORMULA DRILL]",
                    "unit_target": "4 Foundational Proofs",
                    "proof_type": "problem_count",
                    "duration_min": p2,
                    "title": f"{e['subject']}: Key Formula Drills & Foundational Proofs",
                    "description": "Active recall of required formulas, reaction mechanisms, or physics laws with foundational exercises.",
                    "type": "school_defense",
                    "color": "#0284c7",
                },
                {
                    "phase_num": 3,
                    "phase_key": "study_code",
                    "badge_label": "[3. TUM ROADMAP SPRINT]",
                    "unit_target": "1 Station Rep",
                    "proof_type": "code_or_math",
                    "duration_min": p3,
                    "title": f"TUM Roadmap: {deliv_spec['title']}",
                    "description": f"{deliv_spec['target_spec']}.\nMilestone: {deliv_spec['category']} • Station {active_station_id}.",
                    "type": "tum_deliverable",
                    "color": "#10b981",
                },
            ]

        # Scenario F: Pure Cruise Mode / Clear Academic Horizon -> 100% TUM Metro Pipeline
        else:
            p1, p2, p3 = compute_phase_durations(net_min, "pure_tum")
            b["focus"] = f"SGH Library • TUM Deep Work: {deliv_spec['title']}"
            b["activity"] = (
                f"[TUM Metro Pipeline // {active_station_id}] 1 Milestone Rep + "
                f"4 CKE Tasks (2023 May) + 20 German A2 Vocab Units."
            )
            b["is_school_dedicated"] = False
            b["is_tum_roadmap"] = True
            b["deliverable"] = deliv_dict
            b["plan_phases"] = [
                {
                    "phase_num": 1,
                    "phase_key": "study_school",
                    "badge_label": "[1. TUM ROADMAP • REPS]",
                    "unit_target": "1 Milestone Rep (Unassisted)",
                    "proof_type": "code_or_math",
                    "duration_min": p1,
                    "title": f"TUM Roadmap: {deliv_spec['title']}",
                    "description": f"{deliv_spec['target_spec']}.\nCurrent Deliverable: {deliv_spec['category']} • Station {active_station_id}.",
                    "type": "tum_deliverable",
                    "color": "var(--accent-lavender)",
                },
                {
                    "phase_num": 2,
                    "phase_key": "study_matura",
                    "badge_label": "[2. MATURA R • PROBLEM COUNT]",
                    "unit_target": "4 CKE Exam Tasks (Self-Corrected)",
                    "proof_type": "cke_tasks",
                    "duration_min": p2,
                    "title": "Matura R Mathematics: Analytical & Advanced Proofs",
                    "description": "Complete and self-correct 4 CKE tasks (2023 May exam). Traced on paper, red-pen self-correction.",
                    "type": "matura_r",
                    "color": "#0284c7",
                },
                {
                    "phase_num": 3,
                    "phase_key": "study_code",
                    "badge_label": "[3. GERMAN / LEETCODE • UNIT COUNT]",
                    "unit_target": "20 Vocab Cards or 1 LeetCode Commit",
                    "proof_type": "vocab_or_git",
                    "duration_min": p3,
                    "title": "German A2 (Nicos Weg) & Algorithmic Recall",
                    "description": "Master 20 German A2 vocabulary cards (Nicos Weg) or commit 1 clean algorithm solution to Git.",
                    "type": "german_code",
                    "color": "#10b981",
                },
            ]

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

