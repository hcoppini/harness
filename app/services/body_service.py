"""Service for Body / Life maintenance layer: weight progress, training log, and routine tracking."""

import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from app.db import get_connection

TARGET_WEIGHT_KG = 80.0
START_WEIGHT_KG = 68.0


def log_body_metric(
    weight_kg: float,
    calories_met: bool = False,
    protein_met: bool = False,
    notes: str = "",
    date_str: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, Any]:
    """Logs daily bodyweight and nutrition adherence."""
    target_date = date_str or datetime.now().strftime("%Y-%m-%d")
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO body_metrics (date, weight_kg, calories_met, protein_met, notes)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(date) DO UPDATE SET
            weight_kg = excluded.weight_kg,
            calories_met = excluded.calories_met,
            protein_met = excluded.protein_met,
            notes = excluded.notes
        """,
        (target_date, weight_kg, 1 if calories_met else 0, 1 if protein_met else 0, notes),
    )
    conn.commit()

    if close_conn:
        conn.close()

    return {
        "date": target_date,
        "weight_kg": weight_kg,
        "calories_met": calories_met,
        "protein_met": protein_met,
        "notes": notes,
    }


def get_body_metrics_history(limit: int = 30, conn: Optional[sqlite3.Connection] = None) -> List[Dict[str, Any]]:
    """Returns recent weigh-in logs ordered chronologically."""
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT * FROM body_metrics
        ORDER BY date DESC
        LIMIT ?
        """,
        (limit,),
    )
    rows = cursor.fetchall()
    history = [
        {
            "id": r["id"],
            "date": r["date"],
            "weight_kg": r["weight_kg"],
            "calories_met": bool(r["calories_met"]),
            "protein_met": bool(r["protein_met"]),
            "notes": r["notes"] or "",
        }
        for r in reversed(rows)
    ]

    if close_conn:
        conn.close()

    return history


def log_workout(
    workout_type: str,
    details: str,
    intensity: int = 7,
    date_str: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, Any]:
    """Logs a training session (boxing, gym, running)."""
    target_date = date_str or datetime.now().strftime("%Y-%m-%d")
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO workouts (date, workout_type, details, intensity)
        VALUES (?, ?, ?, ?)
        """,
        (target_date, workout_type.lower().strip(), details.strip(), intensity),
    )
    new_id = cursor.lastrowid
    conn.commit()

    if close_conn:
        conn.close()

    return {
        "id": new_id,
        "date": target_date,
        "workout_type": workout_type,
        "details": details,
        "intensity": intensity,
    }


def get_weekly_workout_summary(conn: Optional[sqlite3.Connection] = None) -> Dict[str, Any]:
    """Returns counts of workouts in the last 7 days vs weekly targets."""
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    today = datetime.now()
    seven_days_ago = (today - timedelta(days=7)).strftime("%Y-%m-%d")

    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT workout_type, COUNT(*) as count
        FROM workouts
        WHERE date >= ?
        GROUP BY workout_type
        """,
        (seven_days_ago,),
    )
    counts = {row["workout_type"]: row["count"] for row in cursor.fetchall()}

    cursor.execute("SELECT * FROM workouts ORDER BY date DESC, id DESC LIMIT 10")
    recent_workouts = [
        {
            "id": r["id"],
            "date": r["date"],
            "workout_type": r["workout_type"],
            "details": r["details"],
            "intensity": r["intensity"],
        }
        for r in cursor.fetchall()
    ]

    # Get latest weight
    cursor.execute("SELECT weight_kg FROM body_metrics ORDER BY date DESC LIMIT 1")
    latest_row = cursor.fetchone()
    current_weight = latest_row["weight_kg"] if latest_row else START_WEIGHT_KG

    weight_progress_pct = round(
        max(0.0, min(100.0, ((current_weight - START_WEIGHT_KG) / (TARGET_WEIGHT_KG - START_WEIGHT_KG)) * 100)),
        1,
    )

    if close_conn:
        conn.close()

    return {
        "current_weight": current_weight,
        "start_weight": START_WEIGHT_KG,
        "target_weight": TARGET_WEIGHT_KG,
        "progress_percentage": weight_progress_pct,
        "weekly_counts": {
            "boxing": counts.get("boxing", 0),
            "gym": counts.get("gym", 0),
            "running": counts.get("running", 0),
        },
        "weekly_targets": {
            "boxing": 3,
            "gym": 4,
            "running": 2,
        },
        "recent_workouts": recent_workouts,
    }
