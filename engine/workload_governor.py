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

    # 1. Fetch upcoming exams (normalize ISO date prefixes & deduplicate overlapping sync rows)
    cursor.execute(
        """
        SELECT * FROM school_exams
        WHERE completed = 0
          AND substr(trim(exam_date), 1, 10) >= ?
          AND substr(trim(exam_date), 1, 10) <= ?
        ORDER BY substr(trim(exam_date), 1, 10) ASC, id ASC
        """,
        (target_dt.strftime("%Y-%m-%d"), end_dt.strftime("%Y-%m-%d")),
    )
    raw_exams = [dict(r) for r in cursor.fetchall()]
    exams = []
    seen_exam_keys = set()
    for r in raw_exams:
        norm_date = str(r.get("exam_date") or "").strip()[:10]
        dedupe_key = (
            (r.get("subject") or "").strip().lower(),
            (r.get("title") or "").strip().lower(),
            norm_date,
        )
        if dedupe_key in seen_exam_keys:
            continue
        seen_exam_keys.add(dedupe_key)
        r["exam_date"] = norm_date or r.get("exam_date", "")
        exams.append(r)

    tier_1_exams = []
    tier_2_exams = []
    immediate_exams = []
    week_exams = []

    for e in exams:
        try:
            ex_date = datetime.strptime(str(e["exam_date"] or "").strip()[:10], "%Y-%m-%d").date()
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

        # Acute (1..3 days) triggers Defense readiness; rolling 7-day window captures weekly exam density
        if days_left >= 1 and not e.get("is_travel_excused"):
            if 1 <= days_left <= 3:
                immediate_exams.append(e)
            if 1 <= days_left <= 7:
                week_exams.append(e)

            if e["is_tier_1"]:
                tier_1_exams.append(e)
            else:
                tier_2_exams.append(e)

    # 2. Fetch pending homework (including overdue items that require triage)
    cursor.execute(
        """
        SELECT * FROM homework_items
        WHERE completed = 0 AND substr(trim(due_date), 1, 10) <= ?
        ORDER BY substr(trim(due_date), 1, 10) ASC, id ASC
        """,
        (hw_end_dt.strftime("%Y-%m-%d"),),
    )
    homework = [dict(r) for r in cursor.fetchall()]

    urgent_homework = []
    active_homework = []

    for h in homework:
        try:
            clean_due = str(h["due_date"] or "").strip()[:10]
            h["due_date"] = clean_due or h["due_date"]
            h_date = datetime.strptime(clean_due, "%Y-%m-%d").date()
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
    # REALITY-GROUNDED WORKLOAD STATE MACHINE:
    # School Defense locks ONLY on upcoming tests within the 3-day horizon
    # (1 <= days_left <= 3) or acute writing essays (<= 2 days).
    # Regular ~30m daily homework and historical nb/np/low marks remain tracked
    # as triage advisories without blocking daily TUM execution on Clean Horizons.
    # --------------------------------------------------------------------------
    has_active_hw_le_24h = len(urgent_homework) > 0
    has_open_nb = len(open_nb_marks) > 0
    has_pending_retakes_or_tripwires = (len(scheduled_poprawy) > 0 or len(failing_marks) > 0 or len(open_np_marks) > 0)
    acute_essays_list = [
        h for h in (urgent_homework + active_homework)
        if h.get("is_essay") and 1 <= h.get("days_left", 99) <= 2 and not h.get("is_travel_excused")
    ]
    has_acute_exams = len(immediate_exams) > 0
    has_acute_essays = len(acute_essays_list) > 0
    has_weekly_exam_surge = len(week_exams) >= 3

    cruise_unlocked = not has_acute_exams and not has_acute_essays and not has_weekly_exam_surge

    # Composite Workload score calculation:
    score = (len(tier_1_exams) * 2.5) + (len(tier_2_exams) * 1.0)
    if immediate_exams:
        score += 2.0
    for e in exams:
        if e.get("is_vulnerable") and e.get("days_left", 0) >= 1 and not e.get("is_travel_excused"):
            score += 1.5
    if len(week_exams) > 1:
        score += (len(week_exams) - 1) * 1.5
    score += (len(urgent_homework) * 0.75)
    for h in homework:
        if h.get("is_essay") and h.get("days_left", 99) <= 2 and not h.get("is_travel_excused"):
            score += 2.5
        elif h.get("is_vulnerable") and h.get("days_left", 99) <= 2 and not h.get("is_travel_excused"):
            score += 1.0
    score += (len(active_homework) * 0.25)

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
    elif score > 6.0 and has_acute_exams:
        mode = "SURGE"
        mode_label = "Surge Protocol • High Academic Density"
        badge_class = "amber"
        desc = f"High acute test density ({len(immediate_exams)} test(s) ≤3d, {len(tier_1_exams) + len(tier_2_exams)} total upcoming). Deep work prioritizes nearest test prep."
    elif has_acute_exams or has_acute_essays:
        mode = "DEFENSE"
        mode_label = "Defense Protocol • Test Within 3 Days"
        badge_class = "surge"
        triage_reasons = []
        if has_acute_exams:
            triage_reasons.append(f"{len(immediate_exams)} test(s) ≤3d")
        if has_acute_essays:
            triage_reasons.append(f"{len(acute_essays_list)} essay draft(s) ≤2d")
        reason_str = ", ".join(triage_reasons) if triage_reasons else "Acute 3-day test defense"
        desc = f"DEFENSE PROTOCOL ACTIVE: {reason_str}. Deep work shifted to acute test preparation."
    elif has_weekly_exam_surge:
        mode = "BALANCED"
        mode_label = f"Balanced Horizon • {len(week_exams)} Tests This Week"
        badge_class = "lavender"
        desc = f"CRUISE LOCKED: {len(week_exams)} tests scheduled within 7 days. Deep work pairs TUM Roadmap with early test preparation."
    elif score > 2.5:
        mode = "BALANCED"
        mode_label = "Balanced Horizon • Clean TUM + Early Test Prep"
        badge_class = "lavender"
        desc = "Clean 3-day horizon: no tests within 3 days. Deep work advances TUM Roadmap deliverables alongside light early review."
    else:
        mode = "CRUISE"
        mode_label = "Cruise Mode • TUM Acceleration"
        badge_class = "optimal"
        desc = "CRUISE PROTOCOL UNLOCKED: No tests within 3 days. 100% Deep Work & Training capacity advances TUM '28 Roadmap."

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


def _is_physical_deliverable(d: Dict[str, Any]) -> bool:
    """Returns True if a deliverable belongs to the Physical training stream."""
    did = str(d.get("deliverable_id") or "").lower()
    stream = str(d.get("stream") or d.get("category") or "").lower()
    return "_phys" in did or stream == "physical" or "physical" in stream


def _build_deliverable_payload(d: Dict[str, Any], active_station_id: str) -> Dict[str, Any]:
    """Builds standardized deliverable metadata attached to scheduled blocks."""
    spec = d.get("next_spec") or {}
    stream = str(d.get("stream") or spec.get("category") or "roadmap").lower()
    return {
        "deliverable_id": d["deliverable_id"],
        "station_id": active_station_id,
        "stream": stream,
        "title": spec.get("title") or d.get("title") or "TUM Deliverable",
        "category": spec.get("category") or d.get("category") or (stream.capitalize() if stream else "Roadmap"),
        "target_spec": spec.get("target_spec") or d.get("title") or "",
        "action_type": spec.get("action_type") or "url",
        "target_path": spec.get("target_path") or "",
        "quantity": spec.get("quantity") or 1,
        "completed_count": d.get("completed_count", 0),
        "total_required": d.get("total_required", 1),
        "unit_label": d.get("unit_label") or "units",
    }


def _select_station_deliverables_for_schedule(
    active_station_id: str, conn: Optional[sqlite3.Connection] = None
) -> tuple:
    """
    Separates intellectual deliverables (Academics, Code, SIGG, German) from Physical.
    Picks the intellectual deliverable with lowest completion ratio for Deep Work,
    and binds the active Physical deliverable to Training/Gym/Running blocks.
    """
    station_delivs = kill_list_controller.get_station_deliverables(active_station_id, conn=conn)
    intellectual = [d for d in station_delivs if not _is_physical_deliverable(d)]
    physical_list = [d for d in station_delivs if _is_physical_deliverable(d)]

    incomplete_intel = [d for d in intellectual if not d.get("is_completed")]
    pool = incomplete_intel if incomplete_intel else intellectual
    top_intel = None
    if pool:
        top_intel = min(
            pool,
            key=lambda d: (d.get("completed_count", 0) / max(d.get("total_required", 1), 1)),
        )

    phys_deliv = next((d for d in physical_list if not d.get("is_completed")), (physical_list[0] if physical_list else None))

    deliv_dict = _build_deliverable_payload(top_intel, active_station_id) if top_intel else None
    deliv_spec = (top_intel.get("next_spec") if top_intel else None) or {
        "title": "LeetCode Unassisted & Math R",
        "target_spec": "Solve 1 problem without AI & review Math R",
        "action_type": "url",
        "target_path": "https://leetcode.com/problemset/all/",
        "category": "Algorithms",
        "quantity": 1,
    }
    phys_dict = _build_deliverable_payload(phys_deliv, active_station_id) if phys_deliv else None
    candidates = [_build_deliverable_payload(d, active_station_id) for d in intellectual]
    return deliv_dict, deliv_spec, phys_dict, candidates


def _attach_physical_to_training_blocks(blocks: List[Dict[str, Any]], phys_dict: Optional[Dict[str, Any]]) -> None:
    """Attaches active Physical TUM deliverable metadata onto training/workout blocks."""
    if not phys_dict:
        return
    for b in blocks:
        if b.get("type") == "training":
            b["physical_deliverable"] = dict(phys_dict)


def synthesize_adaptive_schedule(
    base_schedule: Dict[str, Any],
    date_str: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, Any]:
    """
    Takes the static base routine and dynamically shapes the daily plan and study blocks
    depending on upcoming tests (3-day threshold), acute essays, and reality modes.
    - Clean Horizon (>3d until next exam): Deep work embeds TUM Roadmap deliverables.
    - Every training/gym/run block binds the active month's Physical deliverable.
    """
    schedule = dict(base_schedule)
    blocks = [dict(b) for b in schedule.get("blocks", [])]
    analysis = get_workload_analysis(date_str, conn=conn)

    schedule["workload"] = analysis

    target_dt = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else datetime.now().date()
    weekday = target_dt.weekday()  # Monday=0, ... Saturday=5, Sunday=6
    is_weekend = weekday in (5, 6)

    active_station_id = get_active_station_id(target_dt)
    deliv_dict, deliv_spec, phys_dict, candidate_deliverables = _select_station_deliverables_for_schedule(
        active_station_id, conn=conn
    )

    # --------------------------------------------------------------------------
    # 0A. SURGE RECOVERY PROTOCOL (Low Energy / Illness / Family Surge)
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
                "deliverable": deliv_dict,
                "candidate_deliverables": candidate_deliverables,
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
        _attach_physical_to_training_blocks(recovery_blocks, phys_dict)
        schedule["blocks"] = recovery_blocks
        schedule["name"] = f"Recovery Protocol ({target_dt.strftime('%A')})"
        schedule["description"] = "Life Recovery / Family Surge Mode Active. High-friction commitments paused. Biological floor and streak preserved."
        return schedule

    # --------------------------------------------------------------------------
    # 0B. FIELD / TRAVEL PROTOCOL (Away from Warsaw workstation)
    # --------------------------------------------------------------------------
    if analysis.get("is_us_travel_mode"):
        station_id = active_station_id
        chosen_payload = deliv_dict
        spec = deliv_spec
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
                "deliverable": chosen_payload,
                "candidate_deliverables": candidate_deliverables,
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
        _attach_physical_to_training_blocks(travel_blocks, phys_dict)
        schedule["blocks"] = travel_blocks
        schedule["name"] = f"US Travel Protocol ({target_dt.strftime('%A')})"
        schedule["description"] = "Travel Mode Active (Oct 4–18). Warsaw schedule suspended. 60m minimal maintenance anchor to keep pace with zero guilt. Enjoy your trip."
        return schedule

    exams = analysis.get("upcoming_exams", [])
    homework = analysis.get("urgent_homework", []) + analysis.get("active_homework", [])

    # 3-day test factor ONLY: exams due in 1 to 3 days + acute essays due in 1 to 2 days
    acute_essays = [h for h in homework if h.get("is_essay") and 1 <= h.get("days_left", 99) <= 2]
    acute_exams = [e for e in exams if 1 <= e.get("days_left", 99) <= 3]

    # --------------------------------------------------------------------------
    # 1. WEEKEND ADAPTATION: Inject extra study block ONLY when <=3d tests or acute essays loom
    #    Keep Clean Horizon weekends free to advance TUM Deep Work + Running/Physical!
    # --------------------------------------------------------------------------
    if is_weekend:
        impending_obligations = [e for e in exams if 1 <= e.get("days_left", 99) <= 3] + acute_essays

        if impending_obligations or analysis["mode"] in ("DEFENSE", "SURGE"):
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

    # --------------------------------------------------------------------------
    # 2. PHYSICAL BINDING & DEEP WORK SHAPING (BOTH WEEKDAYS AND WEEKENDS)
    # --------------------------------------------------------------------------
    _attach_physical_to_training_blocks(blocks, phys_dict)
    today_exams = analysis.get("today_exams", [])
    urgent_hw = analysis.get("urgent_homework", [])

    for b in blocks:
        is_deep_work = b.get("type") == "deep_work" or "SGH Library" in b.get("focus", "")
        if not is_deep_work:
            continue

        b["is_surge"] = (analysis["mode"] == "SURGE")
        b["candidate_deliverables"] = candidate_deliverables
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

        # Scenario B: Single Nearest Exam Dominance (1 to 3 days out)
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

        # Scenario C: Defense Protocol Active (only when 3-day test defense is unlocked/locked)
        elif analysis.get("mode") == "DEFENSE":
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
            focus_prefix = "TUM Deep Work" if is_weekend else "SGH Library • TUM Deep Work"
            b["focus"] = f"{focus_prefix}: {deliv_spec['title']}"
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

        # Scenario E: Clean Horizon with Upcoming Exam (<=5d out or 3+ weekly exams) -> Balanced TUM + Foundation
        elif exams and (exams[0].get("days_left", 99) <= 5 or analysis.get("week_exams_count", 0) >= 3):
            e = exams[0]
            p1, p2, p3 = compute_phase_durations(net_min, "medium_horizon")
            scope_info = f" ({e['scope'][:40]})" if e.get("scope") else ""
            focus_prefix = "TUM Deep Work" if is_weekend else "SGH Library • TUM Deep Work"
            b["focus"] = f"{focus_prefix}: {deliv_spec['title']} & {e['subject']} Foundation"
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
            focus_prefix = "TUM Deep Work" if is_weekend else "SGH Library • TUM Deep Work"
            b["focus"] = f"{focus_prefix}: {deliv_spec['title']}"
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
    resolved_date = (date_str or (target_dt.isoformat() if "target_dt" in locals() and target_dt else "")) or dt.date.today().isoformat()
    return optimize_schedule_with_calendar_events(schedule, date_str=resolved_date, conn=conn)


def _scale_plan_phases(
    phases: List[Dict[str, Any]],
    net_minutes: int,
    scenario_type: str,
) -> List[Dict[str, Any]]:
    """Recalculates phase durations so `sum(duration_min) == net_minutes` without mutating inputs."""
    if not phases:
        return []
    copied = [dict(p) for p in phases]
    if len(copied) == 3:
        d1, d2, d3 = compute_phase_durations(net_minutes, scenario_type or "medium_horizon")
        # Guarantee exact integer sum
        d3 = max(1, net_minutes - d1 - d2) if net_minutes >= 3 else max(0, net_minutes - d1 - d2)
        for p, dur in zip(copied, (d1, d2, d3)):
            p["duration_min"] = int(dur)
        return copied

    old_total = sum(max(1, int(p.get("duration_min", 0))) for p in copied) or len(copied)
    allocated = 0
    for idx, p in enumerate(copied):
        if idx == len(copied) - 1:
            p["duration_min"] = max(0, int(net_minutes) - allocated)
        else:
            part = max(1, round((max(1, int(p.get("duration_min", 0))) / old_total) * net_minutes))
            part = min(part, max(0, int(net_minutes) - allocated))
            p["duration_min"] = int(part)
            allocated += part
    return copied


def _free_intervals_from_busy(
    busy: List[Tuple[int, int]],
    day_start: int,
    day_end: int,
    buffer_min: int = 0,
) -> List[Tuple[int, int]]:
    """Computes sorted merged free windows inside [day_start, day_end] outside `busy` intervals."""
    expanded: List[Tuple[int, int]] = []
    for s, e in busy:
        if e <= day_start or s >= day_end:
            continue
        expanded.append((max(day_start, s - buffer_min), min(day_end, e + buffer_min)))
    expanded.sort()

    merged: List[Tuple[int, int]] = []
    for s, e in expanded:
        if not merged or s > merged[-1][1]:
            merged.append((s, e))
        else:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e))

    free: List[Tuple[int, int]] = []
    cursor = day_start
    for s, e in merged:
        if s > cursor:
            free.append((cursor, s))
        cursor = max(cursor, e)
    if cursor < day_end:
        free.append((cursor, day_end))
    return free


def _pick_best_reschedule_slot(
    orig_start: int,
    orig_dur: int,
    busy: List[Tuple[int, int]],
    min_slot_min: int = 45,
) -> Optional[Tuple[int, int]]:
    """Finds the best conflict-free slot for a shifted/compressed block."""
    day_start = 7 * 60
    day_end = 22 * 60 + 30

    for buf in (5, 0):
        free = _free_intervals_from_busy(busy, day_start, day_end, buffer_min=buf)
        if not free:
            continue

        # 1. Full duration before 21:30 preferred
        full_daytime: List[Tuple[int, int]] = []
        for fs, fe in free:
            if fe - fs < orig_dur:
                continue
            cand_s = max(fs, min(orig_start, fe - orig_dur))
            cand_e = cand_s + orig_dur
            if cand_e <= 21 * 60 + 30:
                full_daytime.append((cand_s, cand_e))
            elif fs + orig_dur <= 21 * 60 + 30:
                full_daytime.append((fs, fs + orig_dur))
        if full_daytime:
            return min(full_daytime, key=lambda win: (abs(win[0] - orig_start), win[0]))

        # 2. Ergonomic daytime compressed slot (>= 75 min before 21:00)
        daytime_substantial = [
            (fs, min(fe, fs + orig_dur))
            for fs, fe in free
            if min(fe, 21 * 60) - fs >= min(75, orig_dur)
        ]
        if daytime_substantial:
            best = max(daytime_substantial, key=lambda win: (win[1] - win[0], -abs(win[0] - orig_start)))
            return (best[0], min(best[1], best[0] + orig_dur))

        # 3. Full duration up to 22:30
        full_any = [(fs, fs + orig_dur) for fs, fe in free if fe - fs >= orig_dur]
        if full_any:
            return min(full_any, key=lambda win: (abs(win[0] - orig_start), win[0]))

        # 4. Largest available slot >= min_slot_min
        viable = [(fs, min(fe, fs + orig_dur)) for fs, fe in free if fe - fs >= min(min_slot_min, orig_dur)]
        if viable:
            return max(viable, key=lambda win: (win[1] - win[0], -abs(win[0] - orig_start)))

    return None


def optimize_schedule_with_calendar_events(
    schedule: Dict[str, Any],
    date_str: str,
    conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, Any]:
    """
    Applies Google Calendar user overrides (`gcal_sync_map`) and shifts/resizes conflicted
    movable blocks around external `gcal_events`, preserving array indices for completion parity.
    """
    from app.db import get_connection
    from app.services import gcalendar_service

    sched_copy = dict(schedule)
    blocks = [dict(b) for b in (schedule.get("blocks") or [])]

    own_conn = conn is None
    if own_conn:
        conn = get_connection()

    ext_events: List[Dict[str, Any]] = []
    override_by_idx: Dict[int, Dict[str, Any]] = {}
    try:
        rows = conn.execute(
            """
            SELECT event_id, calendar_id, summary, description, location,
                   date, start_time, end_time, start_iso, end_iso, is_all_day, status, source
            FROM gcal_events
            WHERE date = ? AND status != 'cancelled' AND is_harness_managed = 0
            ORDER BY is_all_day DESC, start_time ASC
            """,
            (date_str,),
        ).fetchall()
        ext_events = [dict(r) for r in rows]

        ov_rows = conn.execute(
            """
            SELECT harness_key, override_date, override_start, override_end, user_deleted
            FROM gcal_sync_map
            WHERE harness_kind = 'plan_block' AND harness_key LIKE ?
            """,
            (f"plan:{date_str}:%",),
        ).fetchall()
        for r in ov_rows:
            try:
                idx = int(str(r["harness_key"]).rsplit(":", 1)[-1])
                override_by_idx[idx] = dict(r)
            except Exception:
                continue
    except sqlite3.OperationalError:
        ext_events = []
        override_by_idx = {}
    finally:
        if own_conn and conn is not None:
            conn.close()

    # Step A: Apply explicit user edits / deletions from Google Calendar UI
    for idx, blk in enumerate(blocks):
        ov = override_by_idx.get(idx)
        if not ov:
            continue
        if ov.get("user_deleted"):
            blk["gcal_user_deleted"] = True
            blk["gcal_adjustment_reason"] = "Removed by user in Google Calendar"
            continue
        ov_date = ov.get("override_date") or date_str
        ov_start = (ov.get("override_start") or "").strip()
        ov_end = (ov.get("override_end") or "").strip()
        if ov_date == date_str and ov_start and ov_end:
            new_win = gcalendar_service.parse_time_window(f"{ov_start} – {ov_end}")
            if new_win:
                blk["original_time"] = blk.get("time", "")
                blk["time"] = gcalendar_service.format_time_window(new_win[0], new_win[1])
                blk["gcal_user_override"] = True
                blk["gcal_adjustment_reason"] = "Adjusted by user in Google Calendar"
                net_min, _ = parse_block_net_minutes(blk["time"], default_minutes=new_win[1] - new_win[0])
                blk["net_minutes"] = net_min
                if blk.get("plan_phases"):
                    blk["plan_phases"] = _scale_plan_phases(
                        blk["plan_phases"], net_min, blk.get("scenario_type") or "medium_horizon"
                    )

    # Step B: Conflict-aware optimization around external timed Google Calendar events
    cfg = gcalendar_service.get_gcalendar_config()
    auto_opt = bool(cfg.get("auto_optimize_schedule", True))
    ext_intervals: List[Tuple[int, int, str]] = []
    for ev in ext_events:
        if ev.get("is_all_day"):
            continue
        win = gcalendar_service.parse_time_window(f"{ev.get('start_time', '')} – {ev.get('end_time', '')}")
        if win:
            ext_intervals.append((win[0], win[1], ev.get("summary") or "Calendar Event"))

    conflicts_detected = 0
    blocks_optimized = 0
    opt_notes: List[str] = []

    if auto_opt and ext_intervals:
        def _is_movable(b: Dict[str, Any]) -> bool:
            if b.get("gcal_user_override") or b.get("gcal_user_deleted"):
                return False
            btype = b.get("type", "")
            if btype in ("deep_work", "study_block"):
                return True
            if btype == "training":
                lbl = (b.get("focus") or b.get("label") or "").lower()
                return "box" not in lbl
            return False

        # Soft 'rest' (Free Time) is absorbable by optimizer; 'chore'/'nutrition' preserved in Tier 1
        fixed_strict: List[Tuple[int, int]] = [(s, e) for s, e, _ in ext_intervals]
        fixed_relaxed: List[Tuple[int, int]] = [(s, e) for s, e, _ in ext_intervals]
        block_windows: Dict[int, Tuple[int, int]] = {}
        for idx, blk in enumerate(blocks):
            if blk.get("gcal_user_deleted"):
                continue
            btype = blk.get("type", "")
            win = gcalendar_service.parse_time_window(blk.get("time", ""))
            if not win:
                continue
            block_windows[idx] = win
            if btype == "rest":
                continue
            if not _is_movable(blk):
                fixed_strict.append(win)
                if btype not in ("chore",):
                    fixed_relaxed.append(win)

        # Keep track of each movable block's current slot so unmoved ones act as barriers
        placed_movable: Dict[int, Tuple[int, int]] = {
            idx: win for idx, win in block_windows.items() if _is_movable(blocks[idx])
        }

        for idx, blk in enumerate(blocks):
            if idx not in block_windows:
                continue
            b_start, b_end = block_windows[idx]
            overlapping_names = [
                name for es, ee, name in ext_intervals
                if b_start < ee and es < b_end
            ]
            if not overlapping_names:
                continue

            if not _is_movable(blk):
                conflicts_detected += 1
                opt_notes.append(
                    f"{blk.get('focus') or blk.get('label') or 'Block'} ({blk.get('time', '')}) overlaps GCal: {', '.join(overlapping_names)}"
                )
                continue

            conflicts_detected += 1
            other_movable = [w for j, w in placed_movable.items() if j != idx]
            orig_dur = max(15, b_end - b_start)
            new_slot = _pick_best_reschedule_slot(
                b_start, orig_dur, fixed_strict + other_movable, min_slot_min=45
            )
            if not new_slot:
                new_slot = _pick_best_reschedule_slot(
                    b_start, orig_dur, fixed_relaxed + other_movable, min_slot_min=45
                )

            if not new_slot:
                blk["gcal_conflict_warning"] = True
                opt_notes.append(
                    f"Could not relocate {blk.get('focus') or blk.get('label') or 'Block'} cleanly around {', '.join(overlapping_names)}"
                )
                continue

            ns, ne = new_slot
            orig_time = blk.get("time", "")
            blk["original_time"] = orig_time
            blk["time"] = gcalendar_service.format_time_window(ns, ne)
            blk["gcal_optimized"] = True
            blk["gcal_compressed"] = (ne - ns) < orig_dur
            blk["gcal_adjustment_reason"] = f"Shifted around GCal: {', '.join(overlapping_names)}"
            net_min, _ = parse_block_net_minutes(blk["time"], default_minutes=ne - ns)
            blk["net_minutes"] = net_min
            if blk.get("plan_phases"):
                blk["plan_phases"] = _scale_plan_phases(
                    blk["plan_phases"], net_min, blk.get("scenario_type") or "medium_horizon"
                )
            placed_movable[idx] = (ns, ne)
            blocks_optimized += 1
            opt_notes.append(
                f"{blk.get('focus') or blk.get('label') or 'Block'}: {orig_time} -> {blk['time']} (around {', '.join(overlapping_names)})"
            )

    sched_copy["blocks"] = blocks
    sched_copy["calendar_events"] = ext_events
    sched_copy["calendar_optimization"] = {
        "conflicts_detected": conflicts_detected,
        "blocks_optimized": blocks_optimized,
        "notes": opt_notes,
    }
    return sched_copy


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

