"""Service for tracking Polish school homework, upcoming tests, and Vulcan/Librus bridges."""

import json
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from app.db import get_connection


def _calculate_days_left(target_date_str: str) -> int:
    """Calculates days remaining until target date (0 = Today, negative = overdue)."""
    try:
        target = datetime.strptime(target_date_str, "%Y-%m-%d").date()
        today = datetime.now().date()
        return (target - today).days
    except Exception:
        return 0


def get_upcoming_homework(conn: Optional[sqlite3.Connection] = None, limit: int = 30) -> List[Dict[str, Any]]:
    """Returns pending/uncompleted homework items ordered by due date."""
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT * FROM homework_items
        WHERE completed = 0
        ORDER BY due_date ASC, priority DESC
        LIMIT ?
        """,
        (limit,),
    )
    rows = cursor.fetchall()
    items = []
    for r in rows:
        days_left = _calculate_days_left(r["due_date"])
        items.append({
            "id": r["id"],
            "subject": r["subject"],
            "title": r["title"],
            "due_date": r["due_date"],
            "completed": bool(r["completed"]),
            "source": r["source"] or "manual",
            "priority": r["priority"],
            "notes": r["notes"] or "",
            "days_left": days_left,
        })

    if close_conn:
        conn.close()

    return items


def get_homework_for_date(date_str: Optional[str] = None, conn: Optional[sqlite3.Connection] = None) -> List[Dict[str, Any]]:
    """Returns all homework items due on or before a given date."""
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    target_date = date_str or datetime.now().strftime("%Y-%m-%d")
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT * FROM homework_items
        WHERE due_date = ?
        ORDER BY completed ASC, priority DESC
        """,
        (target_date,),
    )
    rows = cursor.fetchall()
    items = []
    for r in rows:
        items.append({
            "id": r["id"],
            "subject": r["subject"],
            "title": r["title"],
            "due_date": r["due_date"],
            "completed": bool(r["completed"]),
            "source": r["source"] or "manual",
            "priority": r["priority"],
            "notes": r["notes"] or "",
            "days_left": _calculate_days_left(r["due_date"]),
        })

    if close_conn:
        conn.close()

    return items


def add_homework(
    subject: str,
    title: str,
    due_date: str,
    priority: int = 1,
    notes: str = "",
    source: str = "manual",
    conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, Any]:
    """Adds a new homework item to the ledger."""
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO homework_items (subject, title, due_date, completed, source, priority, notes)
        VALUES (?, ?, ?, 0, ?, ?, ?)
        """,
        (subject.strip(), title.strip(), due_date.strip(), source, priority, notes.strip()),
    )
    new_id = cursor.lastrowid
    conn.commit()

    item = {
        "id": new_id,
        "subject": subject,
        "title": title,
        "due_date": due_date,
        "completed": False,
        "source": source,
        "priority": priority,
        "notes": notes,
        "days_left": _calculate_days_left(due_date),
    }

    if close_conn:
        conn.close()

    return item


def toggle_homework(hw_id: int, conn: Optional[sqlite3.Connection] = None) -> Dict[str, Any]:
    """Toggles completion status of a homework item."""
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    cursor = conn.cursor()
    cursor.execute("SELECT completed FROM homework_items WHERE id = ?", (hw_id,))
    row = cursor.fetchone()
    if not row:
        if close_conn:
            conn.close()
        return {"id": hw_id, "completed": False}

    new_val = 0 if row["completed"] else 1
    cursor.execute("UPDATE homework_items SET completed = ? WHERE id = ?", (new_val, hw_id))
    conn.commit()

    if close_conn:
        conn.close()

    return {"id": hw_id, "completed": bool(new_val)}


def delete_homework(hw_id: int, conn: Optional[sqlite3.Connection] = None) -> bool:
    """Deletes a homework item."""
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    cursor = conn.cursor()
    cursor.execute("DELETE FROM homework_items WHERE id = ?", (hw_id,))
    conn.commit()
    deleted = cursor.rowcount > 0

    if close_conn:
        conn.close()

    return deleted


def get_upcoming_exams(conn: Optional[sqlite3.Connection] = None, limit: int = 15) -> List[Dict[str, Any]]:
    """Returns upcoming school exams, tests, and mock maturas."""
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    today_str = datetime.now().strftime("%Y-%m-%d")
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT * FROM school_exams
        WHERE exam_date >= ? OR completed = 0
        ORDER BY exam_date ASC
        LIMIT ?
        """,
        (today_str, limit),
    )
    rows = cursor.fetchall()
    exams = []
    for r in rows:
        exams.append({
            "id": r["id"],
            "subject": r["subject"],
            "title": r["title"],
            "exam_date": r["exam_date"],
            "scope": r["scope"] or "",
            "completed": bool(r["completed"]),
            "result_percentage": r["result_percentage"],
            "days_left": _calculate_days_left(r["exam_date"]),
        })

    if close_conn:
        conn.close()

    return exams


def add_exam(
    subject: str,
    title: str,
    exam_date: str,
    scope: str = "",
    conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, Any]:
    """Adds a new upcoming exam or test."""
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO school_exams (subject, title, exam_date, scope, completed)
        VALUES (?, ?, ?, ?, 0)
        """,
        (subject.strip(), title.strip(), exam_date.strip(), scope.strip()),
    )
    new_id = cursor.lastrowid
    conn.commit()

    exam = {
        "id": new_id,
        "subject": subject,
        "title": title,
        "exam_date": exam_date,
        "scope": scope,
        "completed": False,
        "result_percentage": None,
        "days_left": _calculate_days_left(exam_date),
    }

    if close_conn:
        conn.close()

    return exam


def toggle_exam(
    exam_id: int,
    result_percentage: Optional[float] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> bool:
    """Toggles or completes an exam with an optional percentage."""
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    cursor = conn.cursor()
    cursor.execute("SELECT completed FROM school_exams WHERE id = ?", (exam_id,))
    row = cursor.fetchone()
    if not row:
        if close_conn:
            conn.close()
        return False

    new_val = 0 if row["completed"] else 1
    cursor.execute(
        "UPDATE school_exams SET completed = ?, result_percentage = ? WHERE id = ?",
        (new_val, result_percentage, exam_id),
    )
    conn.commit()
    updated = cursor.rowcount > 0

    if close_conn:
        conn.close()

    return updated


def delete_exam(exam_id: int, conn: Optional[sqlite3.Connection] = None) -> bool:
    """Deletes an exam entry."""
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    cursor = conn.cursor()
    cursor.execute("DELETE FROM school_exams WHERE id = ?", (exam_id,))
    conn.commit()
    deleted = cursor.rowcount > 0

    if close_conn:
        conn.close()

    return deleted


def import_school_data_json(json_str: str, conn: Optional[sqlite3.Connection] = None) -> bool:
    """Imports structured homework and exam entries from JSON payload."""
    try:
        data = json.loads(json_str)
    except Exception:
        return False

    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    cursor = conn.cursor()

    # Import homework
    if "homework" in data and isinstance(data["homework"], list):
        for h in data["homework"]:
            cursor.execute(
                """
                INSERT INTO homework_items (subject, title, due_date, completed, source, priority, notes)
                VALUES (?, ?, ?, 0, ?, ?, ?)
                """,
                (
                    h.get("subject", "General"),
                    h.get("title", "Homework"),
                    h.get("due_date", datetime.now().strftime("%Y-%m-%d")),
                    h.get("source", "import"),
                    h.get("priority", 1),
                    h.get("notes", ""),
                ),
            )

    # Import exams
    if "exams" in data and isinstance(data["exams"], list):
        for e in data["exams"]:
            cursor.execute(
                """
                INSERT INTO school_exams (subject, title, exam_date, scope, completed)
                VALUES (?, ?, ?, ?, 0)
                """,
                (
                    e.get("subject", "General"),
                    e.get("title", "Exam"),
                    e.get("exam_date", datetime.now().strftime("%Y-%m-%d")),
                    e.get("scope", ""),
                ),
            )

    conn.commit()

    if close_conn:
        conn.close()

    return True
