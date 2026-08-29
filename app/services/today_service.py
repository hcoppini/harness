"""Service for managing daily execution tasks, rollover logic, and scratchpad."""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from app.db import get_connection, DATA_DIR


def get_schedule_for_date(date_str: Optional[str] = None) -> Dict[str, Any]:
    """Determines Schedule A, B, or C based on the day of the week."""
    target_dt = datetime.strptime(date_str, "%Y-%m-%d") if date_str else datetime.now()
    weekday = target_dt.strftime("%A")  # Monday, Tuesday, etc.

    schedules_file = DATA_DIR / "schedules.json"
    if not schedules_file.exists():
        return {"name": "Standard Day", "blocks": [], "weekday": weekday}

    try:
        with open(schedules_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        schedules = data.get("schedules", {})

        for key, sched in schedules.items():
            if weekday in sched.get("days", []):
                result = dict(sched)
                result["key"] = key
                result["weekday"] = weekday
                return result

        return {"name": f"{weekday} Routine", "blocks": [], "weekday": weekday}
    except Exception as e:
        return {"name": f"{weekday} Routine", "blocks": [], "weekday": weekday, "error": str(e)}


def get_gym_routine_for_date(date_str: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Returns today's gym routine if Tuesday or Thursday."""
    target_dt = datetime.strptime(date_str, "%Y-%m-%d") if date_str else datetime.now()
    weekday = target_dt.strftime("%A").lower()

    if weekday not in ["tuesday", "thursday"]:
        return None

    gym_file = DATA_DIR / "gym_routines.json"
    if not gym_file.exists():
        return None

    try:
        with open(gym_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("routines", {}).get(weekday)
    except Exception:
        return None


def get_today_tasks(date_str: Optional[str] = None, conn: Optional[sqlite3.Connection] = None) -> List[Dict[str, Any]]:
    """Returns all tasks for the given date (defaults to today)."""
    target_date = date_str or datetime.now().strftime("%Y-%m-%d")
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, title, category, is_tum, completed, date, rollover_count, created_at, completed_at
        FROM tasks
        WHERE date = ?
        ORDER BY is_tum DESC, completed ASC, id ASC
        """,
        (target_date,),
    )
    rows = cursor.fetchall()
    tasks = [
        {
            "id": row["id"],
            "title": row["title"],
            "category": row["category"],
            "is_tum": bool(row["is_tum"]),
            "completed": bool(row["completed"]),
            "date": row["date"],
            "rollover_count": row["rollover_count"],
            "created_at": row["created_at"],
            "completed_at": row["completed_at"],
        }
        for row in rows
    ]

    if close_conn:
        conn.close()

    return tasks


def add_task(
    title: str,
    category: str = "personal",
    is_tum: bool = False,
    date_str: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, Any]:
    """Adds a new task for the given date."""
    target_date = date_str or datetime.now().strftime("%Y-%m-%d")
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO tasks (title, category, is_tum, completed, date, rollover_count)
        VALUES (?, ?, ?, 0, ?, 0)
        """,
        (title.strip(), category, 1 if is_tum else 0, target_date),
    )
    new_id = cursor.lastrowid
    conn.commit()

    if close_conn:
        conn.close()

    return {
        "id": new_id,
        "title": title.strip(),
        "category": category,
        "is_tum": is_tum,
        "completed": False,
        "date": target_date,
        "rollover_count": 0,
    }


def toggle_task(task_id: int, conn: Optional[sqlite3.Connection] = None) -> Dict[str, Any]:
    """Toggles task completed status and updates completed_at."""
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    cursor = conn.cursor()
    cursor.execute("SELECT completed FROM tasks WHERE id = ?", (task_id,))
    row = cursor.fetchone()
    if not row:
        if close_conn:
            conn.close()
        raise ValueError(f"Task {task_id} not found")

    new_status = 0 if row["completed"] else 1
    completed_at = datetime.now().isoformat() if new_status == 1 else None

    cursor.execute(
        """
        UPDATE tasks
        SET completed = ?, completed_at = ?
        WHERE id = ?
        """,
        (new_status, completed_at, task_id),
    )
    conn.commit()

    if close_conn:
        conn.close()

    return {"id": task_id, "completed": bool(new_status), "completed_at": completed_at}


def delete_task(task_id: int, conn: Optional[sqlite3.Connection] = None) -> bool:
    """Deletes a task by ID."""
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    deleted = cursor.rowcount > 0

    if close_conn:
        conn.close()

    return deleted


def rollover_tasks(target_date_str: Optional[str] = None, conn: Optional[sqlite3.Connection] = None) -> int:
    """
    Carries forward all uncompleted tasks from prior dates to target_date.
    Increments rollover_count so the user knows how many days it lingered,
    without any guilt score or failure penalty.
    """
    target_date = target_date_str or datetime.now().strftime("%Y-%m-%d")
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE tasks
        SET date = ?,
            rollover_count = rollover_count + 1
        WHERE date < ? AND completed = 0
        """,
        (target_date, target_date),
    )
    rolled_count = cursor.rowcount
    conn.commit()

    if close_conn:
        conn.close()

    return rolled_count


def get_daily_log(date_str: Optional[str] = None, conn: Optional[sqlite3.Connection] = None) -> Dict[str, Any]:
    """Retrieves or creates daily log metadata (scratchpad, wake/sleep, reflections)."""
    target_date = date_str or datetime.now().strftime("%Y-%m-%d")
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    cursor = conn.cursor()
    cursor.execute("SELECT * FROM daily_logs WHERE date = ?", (target_date,))
    row = cursor.fetchone()

    if not row:
        cursor.execute(
            """
            INSERT INTO daily_logs (date, scratchpad, wake_time, sleep_time, reflection_worked, reflection_slipped, reflection_tomorrow, completed_blocks, completed_exercises)
            VALUES (?, '', '', '', '', '', '', '', '')
            """,
            (target_date,),
        )
        conn.commit()
        log_data = {
            "date": target_date,
            "scratchpad": "",
            "wake_time": "",
            "sleep_time": "",
            "reflection_worked": "",
            "reflection_slipped": "",
            "reflection_tomorrow": "",
            "completed_blocks": "",
            "completed_exercises": "",
        }
    else:
        log_data = {
            "date": row["date"],
            "scratchpad": row["scratchpad"] or "",
            "wake_time": row["wake_time"] or "",
            "sleep_time": row["sleep_time"] or "",
            "reflection_worked": row["reflection_worked"] or "",
            "reflection_slipped": row["reflection_slipped"] or "",
            "reflection_tomorrow": row["reflection_tomorrow"] or "",
            "completed_blocks": row["completed_blocks"] or "" if "completed_blocks" in row.keys() else "",
            "completed_exercises": row["completed_exercises"] or "" if "completed_exercises" in row.keys() else "",
        }

    if close_conn:
        conn.close()

    return log_data


def update_daily_log(
    date_str: Optional[str] = None,
    scratchpad: Optional[str] = None,
    wake_time: Optional[str] = None,
    sleep_time: Optional[str] = None,
    reflection_worked: Optional[str] = None,
    reflection_slipped: Optional[str] = None,
    reflection_tomorrow: Optional[str] = None,
    completed_blocks: Optional[str] = None,
    completed_exercises: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, Any]:
    """Updates daily log fields."""
    target_date = date_str or datetime.now().strftime("%Y-%m-%d")
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    # Ensure row exists
    get_daily_log(target_date, conn=conn)

    updates = []
    values = []
    if scratchpad is not None:
        updates.append("scratchpad = ?")
        values.append(scratchpad)
    if wake_time is not None:
        updates.append("wake_time = ?")
        values.append(wake_time)
    if sleep_time is not None:
        updates.append("sleep_time = ?")
        values.append(sleep_time)
    if reflection_worked is not None:
        updates.append("reflection_worked = ?")
        values.append(reflection_worked)
    if reflection_slipped is not None:
        updates.append("reflection_slipped = ?")
        values.append(reflection_slipped)
    if reflection_tomorrow is not None:
        updates.append("reflection_tomorrow = ?")
        values.append(reflection_tomorrow)
    if completed_blocks is not None:
        updates.append("completed_blocks = ?")
        values.append(completed_blocks)
    if completed_exercises is not None:
        updates.append("completed_exercises = ?")
        values.append(completed_exercises)

    if updates:
        values.append(target_date)
        query = f"UPDATE daily_logs SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP WHERE date = ?"
        conn.execute(query, values)
        conn.commit()

    res = get_daily_log(target_date, conn=conn)
    if close_conn:
        conn.close()

    return res
