"""Service for TUM Heilbronn roadmapping: 4-semester grades, Matura targets, German ladder."""

import sqlite3
from typing import List, Dict, Any, Optional
from app.db import get_connection

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

    # 1. Fetch grades grouped by semester
    cursor.execute("SELECT * FROM tum_grades ORDER BY semester ASC, id ASC")
    grade_rows = cursor.fetchall()
    semesters: Dict[int, List[Dict[str, Any]]] = {1: [], 2: [], 3: [], 4: []}
    total_grades = []
    grades_under_four = 0

    for row in grade_rows:
        sem = row["semester"]
        actual = row["actual_grade"]
        if actual is not None:
            total_grades.append(actual)
            if actual < 4.0:
                grades_under_four += 1

        semesters[sem].append(
            {
                "id": row["id"],
                "subject": row["subject"],
                "semester": sem,
                "target_grade": row["target_grade"],
                "actual_grade": actual,
                "percentage": row["percentage"],
                "notes": row["notes"] or "",
            }
        )

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

    return {
        "overall_gpa": overall_gpa,
        "grades_under_four": grades_under_four,
        "semesters": semesters,
        "matura": matura_list,
        "language": lang_list,
        "target_program": "TUM Campus Heilbronn - Management & Data Science (B.Sc.)",
        "key_requirements": [
            "Abitur-equivalent GPA >= 1.5 - 2.0 (Polish GPA ~ 5.0+)",
            "Rozszerzona Matematyka & Informatyka strong performance",
            "Bilingual English (C1 equivalent)",
            "German B2 recommended for living & internships in Baden-Württemberg",
            "Extracurricular impact: SIGG national finals & live software repos",
        ],
    }


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
