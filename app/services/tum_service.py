import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from app.db import get_connection, DATA_DIR
from engine.tum_calculator import calculate_bavarian_grade, calculate_tum_aptitude_score
from engine.grade_parser import parse_polish_grade, calculate_subject_average, get_grade_badge_color

DEFAULT_SUBJECTS = [
    ("Matematyka", 6.0),
    ("Informatyka", 6.0),
    ("Język Angielski", 5.5),
    ("Język Polski", 4.5),
    ("Fizyka", 4.5),
    ("Historia", 4.0),
    ("Geografia", 4.0),
    ("Biologia / Chemia", 4.0),
    ("Język Niemiecki", 5.0),
]

DEFAULT_MATURA = [
    ("Matematyka Rozszerzona", 90.0, 0.0, "Przedmiot kluczowy na TUM"),
    ("Informatyka Rozszerzona", 90.0, 0.0, "Algorytmika, Python/C++, CKE arkusze"),
    ("Język Angielski Dwujęzyczny / R", 95.0, 0.0, "Język wykładowy TUM Heilbronn"),
    ("Matematyka Podstawowa", 100.0, 0.0, "Fundament punktowy"),
    ("Język Polski Podstawowy", 75.0, 0.0, "Wymóg zdawalności"),
]

DEFAULT_GERMAN = [
    ("A1", "2025-06-01", "completed", "Podstawy gramatyki, czasowniki regularne/nieregularne"),
    ("A2", "2025-11-01", "in_progress", "Konwersacje codzienne, czas przeszły Perfekt/Präteritum"),
    ("B1", "2026-06-01", "pending", "Certyfikat Goethe B1: czytanie artykułów, pisanie maili"),
    ("B2", "2027-02-01", "pending", "Goethe B2 / TestDaF: niemiecki akademicki i biznesowy"),
]


def seed_tum_data_if_empty(conn: sqlite3.Connection) -> None:
    """Seeds initial TUM benchmarks if tables are empty."""
    cursor = conn.cursor()

    # Seed grades for Semesters 1 to 4 if empty
    cursor.execute("SELECT COUNT(*) as cnt FROM tum_grades")
    if cursor.fetchone()["cnt"] == 0:
        for sem in range(1, 5):
            for subj, target in DEFAULT_SUBJECTS:
                cursor.execute(
                    """
                    INSERT INTO tum_grades (subject, semester, target_grade, actual_grade, percentage)
                    VALUES (?, ?, ?, NULL, NULL)
                    """,
                    (subj, sem, target),
                )

    # Seed Matura subjects if empty
    cursor.execute("SELECT COUNT(*) as cnt FROM tum_matura")
    if cursor.fetchone()["cnt"] == 0:
        for subj, target, current, notes in DEFAULT_MATURA:
            cursor.execute(
                """
                INSERT INTO tum_matura (subject, target_percentage, current_mock_percentage, notes)
                VALUES (?, ?, ?, ?)
                """,
                (subj, target, current, notes),
            )

    # Seed German ladder if empty
    cursor.execute("SELECT COUNT(*) as cnt FROM tum_language")
    if cursor.fetchone()["cnt"] == 0:
        for level, target_date, status, desc in DEFAULT_GERMAN:
            cursor.execute(
                """
                INSERT INTO tum_language (level, target_date, status, milestone_description)
                VALUES (?, ?, ?, ?)
                """,
                (level, target_date, status, desc),
            )

    conn.commit()


def get_tum_overview(conn: Optional[sqlite3.Connection] = None) -> Dict[str, Any]:
    """Returns complete TUM roadmap dataset: grades, matura, language, and readiness indicators."""
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    seed_tum_data_if_empty(conn)
    cursor = conn.cursor()

    # 1. Fetch grade entries and group by (subject, semester)
    cursor.execute("SELECT * FROM tum_grade_entries ORDER BY date ASC, id ASC")
    all_entries = cursor.fetchall()
    entries_by_subj_sem: Dict[tuple, List[Dict[str, Any]]] = {}
    for er in all_entries:
        key = (er["subject"].strip().lower(), er["semester"])
        if key not in entries_by_subj_sem:
            entries_by_subj_sem[key] = []
        parsed = parse_polish_grade(er["raw_input"])
        entries_by_subj_sem[key].append({
            "id": er["id"],
            "subject": er["subject"],
            "semester": er["semester"],
            "raw_input": er["raw_input"],
            "numeric_value": er["numeric_value"],
            "weight": er["weight"],
            "category": er["category"],
            "description": er["description"] or "",
            "date": er["date"],
            "counts_in_average": bool(er["counts_in_average"]),
            "display_label": parsed["display_label"],
            "badge_color": parsed["badge_color"],
            "grade_type": parsed["grade_type"],
        })

    # Fetch subjects grouped by semester
    cursor.execute("SELECT * FROM tum_grades ORDER BY semester ASC, id ASC")
    grade_rows = cursor.fetchall()
    semesters: Dict[int, List[Dict[str, Any]]] = {1: [], 2: [], 3: [], 4: []}
    semester_gpas: Dict[int, float] = {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0}
    total_grades = []
    grades_under_four = 0

    for row in grade_rows:
        sem = row["semester"]
        subj = row["subject"]
        key = (subj.strip().lower(), sem)
        subj_entries = entries_by_subj_sem.get(key, [])
        running_avg = calculate_subject_average(subj_entries)

        if running_avg is not None:
            actual = running_avg
            if row["actual_grade"] != actual:
                cursor.execute("UPDATE tum_grades SET actual_grade = ? WHERE id = ?", (actual, row["id"]))
        else:
            actual = row["actual_grade"]

        if actual is not None:
            total_grades.append(actual)
            if actual < 4.0:
                grades_under_four += 1

        semesters[sem].append(
            {
                "id": row["id"],
                "subject": subj,
                "semester": sem,
                "target_grade": row["target_grade"],
                "actual_grade": actual,
                "running_average": running_avg,
                "entries": subj_entries,
                "percentage": row["percentage"],
                "notes": row["notes"] or "",
            }
        )

    # Calculate semester GPAs
    for s_idx in range(1, 5):
        sem_actuals = [g["actual_grade"] for g in semesters[s_idx] if g["actual_grade"] is not None]
        semester_gpas[s_idx] = round(sum(sem_actuals) / len(sem_actuals), 2) if sem_actuals else 0.0

    overall_gpa = round(sum(total_grades) / len(total_grades), 2) if total_grades else 0.0

    # 2. Fetch Matura
    cursor.execute("SELECT * FROM tum_matura ORDER BY target_percentage DESC")
    matura_rows = cursor.fetchall()
    matura_list = [
        {
            "id": r["id"],
            "subject": r["subject"],
            "target_percentage": r["target_percentage"],
            "current_mock_percentage": r["current_mock_percentage"] or 0.0,
            "notes": r["notes"] or "",
        }
        for r in matura_rows
    ]

    # 3. Fetch German
    cursor.execute("SELECT * FROM tum_language ORDER BY id ASC")
    lang_rows = cursor.fetchall()
    lang_list = [
        {
            "id": r["id"],
            "level": r["level"],
            "target_date": r["target_date"],
            "status": r["status"],
            "milestone_description": r["milestone_description"],
        }
        for r in lang_rows
    ]

    if close_conn:
        conn.close()

    # Calculate Subject Grades for TUM Aptitude (Math 2x, CS 2x, Lang 1x)
    def find_subj_grade(name_pattern: str, default_target: float = 5.5) -> float:
        actuals = []
        targets = []
        for sem_grades in semesters.values():
            for g in sem_grades:
                if name_pattern.lower() in g["subject"].lower():
                    if g["actual_grade"] is not None:
                        actuals.append(g["actual_grade"])
                    if g["target_grade"] is not None:
                        targets.append(g["target_grade"])
        if actuals:
            return round(sum(actuals) / len(actuals), 2)
        if targets:
            return round(sum(targets) / len(targets), 2)
        return default_target

    math_pl = find_subj_grade("matematyka", 5.5)
    cs_pl = find_subj_grade("informatyka", 5.5)
    lang_pl = find_subj_grade("angielski", 5.5)
    calc_gpa = overall_gpa if overall_gpa > 0 else round((math_pl + cs_pl + lang_pl) / 3.0, 2)

    bavarian_eval = calculate_tum_aptitude_score(calc_gpa, math_pl, cs_pl, lang_pl)

    return {
        "overall_gpa": overall_gpa,
        "grades_under_four": grades_under_four,
        "semesters": semesters,
        "semester_gpas": semester_gpas,
        "matura": matura_list,
        "language": lang_list,
        "bavarian_assessment": bavarian_eval,
        "target_program": "TUM Campus Heilbronn - Management & Data Science (B.Sc.)",
        "key_requirements": [
            "Abitur-equivalent GPA >= 1.5 - 2.0 (Polish GPA ~ 5.0+)",
            "Rozszerzona Matematyka & Informatyka strong performance",
            "Bilingual English (C1 equivalent)",
            "German B2 recommended for living & internships in Baden-Württemberg",
            "Extracurricular impact: SIGG national finals & live software repos",
        ],
    }


def add_grade_entry(
    subject: str,
    semester: int,
    raw_input: str,
    weight: float = 1.0,
    category: str = "Grade",
    description: str = "",
    date_str: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, Any]:
    """
    Parses and logs an individual grade entry, immediately recalculating the subject's running average.
    """
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    parsed = parse_polish_grade(raw_input)
    target_date = date_str or datetime.now().strftime("%Y-%m-%d")
    wt = float(weight or 1.0)
    num_val = parsed["numeric_value"]
    counts = 1 if parsed["counts_in_average"] else 0

    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO tum_grade_entries 
        (subject, semester, raw_input, numeric_value, weight, category, description, date, counts_in_average)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            subject.strip(),
            int(semester),
            raw_input.strip(),
            num_val,
            wt,
            category.strip(),
            description.strip(),
            target_date,
            counts,
        ),
    )
    entry_id = cursor.lastrowid

    # Ensure subject exists in tum_grades for this semester
    cursor.execute(
        "SELECT id FROM tum_grades WHERE LOWER(TRIM(subject)) = LOWER(TRIM(?)) AND semester = ?",
        (subject.strip(), int(semester)),
    )
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO tum_grades (subject, semester, target_grade, actual_grade) VALUES (?, ?, 5.0, NULL)",
            (subject.strip(), int(semester)),
        )

    # Recalculate subject running average
    cursor.execute(
        """
        SELECT * FROM tum_grade_entries 
        WHERE LOWER(TRIM(subject)) = LOWER(TRIM(?)) AND semester = ?
        """,
        (subject.strip(), int(semester)),
    )
    rows = cursor.fetchall()
    entries = [dict(r) for r in rows]
    running_avg = calculate_subject_average(entries)

    # Update tum_grades for this subject and semester
    cursor.execute(
        """
        UPDATE tum_grades 
        SET actual_grade = ?
        WHERE LOWER(TRIM(subject)) = LOWER(TRIM(?)) AND semester = ?
        """,
        (running_avg, subject.strip(), int(semester)),
    )
    conn.commit()

    if close_conn:
        conn.close()

    return {
        "success": True,
        "entry": {
            "id": entry_id,
            "subject": subject.strip(),
            "semester": int(semester),
            "raw_input": raw_input,
            "numeric_value": num_val,
            "weight": wt,
            "category": category,
            "description": description,
            "date": target_date,
            "counts_in_average": bool(counts),
            "display_label": parsed["display_label"],
            "badge_color": parsed["badge_color"],
        },
        "running_average": running_avg,
    }


def delete_grade_entry(entry_id: int, conn: Optional[sqlite3.Connection] = None) -> bool:
    """Deletes a grade entry and updates the running average."""
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    cursor = conn.cursor()
    cursor.execute("SELECT subject, semester FROM tum_grade_entries WHERE id = ?", (entry_id,))
    row = cursor.fetchone()
    if not row:
        if close_conn:
            conn.close()
        return False

    subject = row["subject"]
    semester = row["semester"]

    cursor.execute("DELETE FROM tum_grade_entries WHERE id = ?", (entry_id,))

    # Recalculate
    cursor.execute(
        """
        SELECT * FROM tum_grade_entries 
        WHERE LOWER(TRIM(subject)) = LOWER(TRIM(?)) AND semester = ?
        """,
        (subject, semester),
    )
    rows = cursor.fetchall()
    running_avg = calculate_subject_average([dict(r) for r in rows])

    cursor.execute(
        """
        UPDATE tum_grades 
        SET actual_grade = ?
        WHERE LOWER(TRIM(subject)) = LOWER(TRIM(?)) AND semester = ?
        """,
        (running_avg, subject, semester),
    )
    conn.commit()

    if close_conn:
        conn.close()

    return True


def get_grade_entries(
    subject: Optional[str] = None,
    semester: Optional[int] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> List[Dict[str, Any]]:
    """Returns list of all grade entries, optionally filtered by subject/semester."""
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    cursor = conn.cursor()
    query = "SELECT * FROM tum_grade_entries WHERE 1=1"
    params = []
    if subject:
        query += " AND LOWER(TRIM(subject)) = LOWER(TRIM(?))"
        params.append(subject.strip())
    if semester:
        query += " AND semester = ?"
        params.append(int(semester))
    query += " ORDER BY date DESC, id DESC"

    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()
    results = []
    for r in rows:
        parsed = parse_polish_grade(r["raw_input"])
        results.append({
            "id": r["id"],
            "subject": r["subject"],
            "semester": r["semester"],
            "raw_input": r["raw_input"],
            "numeric_value": r["numeric_value"],
            "weight": r["weight"],
            "category": r["category"],
            "description": r["description"] or "",
            "date": r["date"],
            "counts_in_average": bool(r["counts_in_average"]),
            "display_label": parsed["display_label"],
            "badge_color": parsed["badge_color"],
            "grade_type": parsed["grade_type"],
        })

    if close_conn:
        conn.close()

    return results


def calculate_custom_tum_aptitude(
    gpa_pl: float, math_pl: float, cs_pl: float, lang_pl: float
) -> Dict[str, Any]:
    """Calculates hypothetical TUM Stage 1 Aptitude Assessment points."""
    return calculate_tum_aptitude_score(gpa_pl, math_pl, cs_pl, lang_pl)


def update_grade(
    grade_id: int,
    actual_grade: Optional[float],
    percentage: Optional[float] = None,
    notes: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> bool:
    """Updates a subject grade."""
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE tum_grades
        SET actual_grade = ?, percentage = ?, notes = COALESCE(?, notes)
        WHERE id = ?
        """,
        (actual_grade, percentage, notes, grade_id),
    )
    conn.commit()
    updated = cursor.rowcount > 0

    if close_conn:
        conn.close()

    return updated


def update_matura(
    matura_id: int,
    current_mock_percentage: float,
    notes: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> bool:
    """Updates a mock score for a Matura subject."""
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE tum_matura
        SET current_mock_percentage = ?, notes = COALESCE(?, notes)
        WHERE id = ?
        """,
        (current_mock_percentage, notes, matura_id),
    )
    conn.commit()
    updated = cursor.rowcount > 0

    if close_conn:
        conn.close()

    return updated


def update_language_status(
    level: str, status: str, conn: Optional[sqlite3.Connection] = None
) -> bool:
    """Updates German language level status (pending, in_progress, completed)."""
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE tum_language
        SET status = ?
        WHERE level = ?
        """,
        (status, level),
    )
    conn.commit()
    updated = cursor.rowcount > 0

    if close_conn:
        conn.close()

    return updated


def get_metro_roadmap() -> Dict[str, Any]:
    """Returns the complete 2-year metro roadmap dataset from data/metro_roadmap.json."""
    roadmap_file = DATA_DIR / "metro_roadmap.json"
    if not roadmap_file.exists():
        return {"title": "TUM Roadmap", "stations": []}

    try:
        with open(roadmap_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        return {"title": "TUM Roadmap", "stations": [], "error": str(e)}


def update_station_status(station_id: str, status: str) -> bool:
    """Updates the status of a specific metro station in metro_roadmap.json."""
    roadmap_file = DATA_DIR / "metro_roadmap.json"
    if not roadmap_file.exists():
        return False

    try:
        with open(roadmap_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        found = False
        for s in data.get("stations", []):
            if s.get("id") == station_id:
                s["status"] = status
                found = True
                break

        if found:
            with open(roadmap_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        return False
    except Exception:
        return False


def toggle_station_deliverable(station_id: str, deliverable_key: str) -> Dict[str, Any]:
    """Toggles a deliverable checkbox for a station.
    When all deliverables for a station are checked, automatically marks the station as 'completed'.
    When any deliverable is unchecked, reverts status from 'completed' to 'active'.
    """
    roadmap_file = DATA_DIR / "metro_roadmap.json"
    if not roadmap_file.exists():
        return {"success": False, "error": "Roadmap file not found"}

    try:
        with open(roadmap_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        target_station = None
        for s in data.get("stations", []):
            if s.get("id") == station_id:
                target_station = s
                break

        if not target_station:
            return {"success": False, "error": f"Station {station_id} not found"}

        completed_list = target_station.get("completed_deliverables", [])
        if deliverable_key in completed_list:
            completed_list.remove(deliverable_key)
            is_checked = False
        else:
            completed_list.append(deliverable_key)
            is_checked = True

        target_station["completed_deliverables"] = completed_list

        all_keys = list(target_station.get("deliverables", {}).keys())
        total_count = len(all_keys)
        completed_count = len(completed_list)

        # Automatic station completion trigger
        if total_count > 0 and completed_count >= total_count:
            target_station["status"] = "completed"
        elif target_station.get("status") == "completed":
            target_station["status"] = "active"

        with open(roadmap_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return {
            "success": True,
            "station_id": station_id,
            "deliverable_key": deliverable_key,
            "is_checked": is_checked,
            "completed_deliverables": completed_list,
            "completed_count": completed_count,
            "total_count": total_count,
            "station_status": target_station["status"],
            "station_completed": target_station["status"] == "completed",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_all_configs() -> Dict[str, Any]:
    """Returns all structured JSON configs (schedules, gym routines, roadmap, sync config)."""
    res = {
        "schedules": {},
        "gym_routines": {},
        "metro_roadmap": {},
        "sync_config": {},
    }
    try:
        s_file = DATA_DIR / "schedules.json"
        if s_file.exists():
            with open(s_file, "r", encoding="utf-8") as f:
                res["schedules"] = json.load(f)

        g_file = DATA_DIR / "gym_routines.json"
        if g_file.exists():
            with open(g_file, "r", encoding="utf-8") as f:
                res["gym_routines"] = json.load(f)

        m_file = DATA_DIR / "metro_roadmap.json"
        if m_file.exists():
            with open(m_file, "r", encoding="utf-8") as f:
                res["metro_roadmap"] = json.load(f)

        c_file = DATA_DIR / "sync_config.json"
        if c_file.exists():
            with open(c_file, "r", encoding="utf-8") as f:
                res["sync_config"] = json.load(f)
    except Exception:
        pass
    return res


def import_config(config_type: str, json_content: str) -> bool:
    """Imports or updates a configuration file (schedules, gym_routines, metro_roadmap, or sync_config)."""
    filename_map = {
        "schedules": DATA_DIR / "schedules.json",
        "gym_routines": DATA_DIR / "gym_routines.json",
        "metro_roadmap": DATA_DIR / "metro_roadmap.json",
        "sync_config": DATA_DIR / "sync_config.json",
    }
    target = filename_map.get(config_type)
    if not target:
        return False

    try:
        parsed = json.loads(json_content)
        with open(target, "w", encoding="utf-8") as f:
            json.dump(parsed, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False

