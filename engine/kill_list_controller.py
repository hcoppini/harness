"""Kill List & Metro Auto-Increment Controller (Harness 2.1).

Eliminates decision friction by enforcing the 3-Item Rule for SGH Library TUM Deep Work blocks,
wires native OS/browser triggers (PDF, URL, VS Code), and executes atomic SQLite increments
linking completed kill-items to the active 24-month TUM Metro Line deliverables.
"""

import calendar
import os
import sqlite3
import subprocess
import uuid
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from app.db import get_connection, get_db_path, DATA_DIR


def launch_kill_item(action_type: str, target_path: str) -> Dict[str, Any]:
    """Directly triggers the tool/resource for the study session."""
    target_path = (target_path or "").strip()
    if not target_path:
        return {"success": False, "error": "Empty target path"}

    try:
        if action_type == "url":
            webbrowser.open(target_path)
            return {"success": True, "action": "url", "target": target_path}

        elif action_type == "pdf":
            # If target_path is a web URL, open in browser
            if target_path.startswith("http://") or target_path.startswith("https://"):
                webbrowser.open(target_path)
                return {"success": True, "action": "pdf_url", "target": target_path}

            # Check if file exists locally (or relative to harness root)
            local_candidate = Path(target_path)
            if not local_candidate.is_absolute():
                local_candidate = (DATA_DIR.parent / target_path).resolve()

            if local_candidate.exists():
                try:
                    os.startfile(str(local_candidate))
                except Exception:
                    subprocess.Popen(["cmd", "/c", "start", "", str(local_candidate)], shell=True)
                return {"success": True, "action": "pdf_local", "target": str(local_candidate)}
            else:
                # Still attempt system open via start
                subprocess.Popen(["cmd", "/c", "start", "", target_path], shell=True)
                return {"success": True, "action": "pdf_cmd", "target": target_path}

        elif action_type == "workspace":
            # Normalize path
            ws_path = os.path.normpath(target_path)
            try:
                subprocess.Popen(["code", ws_path], shell=True)
                return {"success": True, "action": "code", "target": ws_path}
            except Exception:
                # Fallback to explorer if VS Code fails
                subprocess.Popen(["explorer", ws_path], shell=True)
                return {"success": True, "action": "explorer", "target": ws_path}

        else:
            # Generic fallback
            webbrowser.open(target_path)
            return {"success": True, "action": "generic_fallback", "target": target_path}

    except Exception as e:
        return {"success": False, "error": str(e)}


def is_evening_locked(target_date_str: str) -> bool:
    """
    Returns True if target_date is in the future and today has passed 18:00 (evening review lock),
    or if target_date is in the past.
    """
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    if target_date_str < today_str:
        return True
    if target_date_str > today_str and now.hour >= 18:
        return True
    return False


def get_kill_list(
    date_str: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, Any]:
    """Retrieves all Kill List items for the specified date, joining deliverable progress."""
    target_date = date_str or datetime.now().strftime("%Y-%m-%d")
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT 
            k.id, k.date, k.category, k.title, k.action_type, k.target_path, k.target_spec,
            k.station_deliverable_id, k.completed, k.created_at,
            s.stream, s.title AS deliverable_title, s.total_required, s.completed_count,
            s.unit_label, s.is_completed AS deliverable_is_completed
        FROM kill_list_items k
        LEFT JOIN station_deliverable_progress s ON k.station_deliverable_id = s.deliverable_id
        WHERE k.date = ?
        ORDER BY k.completed ASC, k.created_at ASC
        """,
        (target_date,),
    )
    rows = cursor.fetchall()
    items = []
    for r in rows:
        items.append({
            "id": r["id"],
            "date": r["date"],
            "category": r["category"],
            "title": r["title"],
            "action_type": r["action_type"],
            "target_path": r["target_path"],
            "target_spec": r["target_spec"],
            "station_deliverable_id": r["station_deliverable_id"],
            "completed": bool(r["completed"]),
            "created_at": r["created_at"],
            "deliverable": {
                "id": r["station_deliverable_id"],
                "stream": r["stream"] or "",
                "title": r["deliverable_title"] or "",
                "total_required": r["total_required"] or 0,
                "completed_count": r["completed_count"] or 0,
                "unit_label": r["unit_label"] or "",
                "is_completed": bool(r["deliverable_is_completed"] or 0),
            } if r["station_deliverable_id"] else None,
        })

    locked = is_evening_locked(target_date)

    if close_conn:
        conn.close()

    return {
        "date": target_date,
        "items": items,
        "count": len(items),
        "is_evening_locked": locked,
        "max_allowed": 3,
    }


def add_kill_item(
    category: str,
    title: str,
    action_type: str,
    target_path: str,
    target_spec: str = "",
    station_deliverable_id: Optional[str] = None,
    date_str: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, Any]:
    """
    Adds a new item to the daily Kill List.
    Strictly enforces the 3-Item Rule per library session.
    """
    target_date = date_str or datetime.now().strftime("%Y-%m-%d")
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    cursor = conn.cursor()

    # Enforce 3-Item Rule
    cursor.execute("SELECT COUNT(*) AS cnt FROM kill_list_items WHERE date = ?", (target_date,))
    count = cursor.fetchone()["cnt"]
    if count >= 3:
        if close_conn:
            conn.close()
        raise ValueError("3-Item Rule Enforced: Maximum of 3 active kill-items allowed per library session.")

    item_id = f"kill_{uuid.uuid4().hex[:8]}"
    cursor.execute(
        """
        INSERT INTO kill_list_items 
        (id, date, category, title, action_type, target_path, target_spec, station_deliverable_id, completed)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
        """,
        (
            item_id,
            target_date,
            category.strip(),
            title.strip(),
            action_type.strip().lower(),
            target_path.strip(),
            target_spec.strip(),
            station_deliverable_id or None,
        ),
    )
    conn.commit()

    if close_conn:
        conn.close()

    return {
        "id": item_id,
        "date": target_date,
        "category": category,
        "title": title,
        "action_type": action_type,
        "target_path": target_path,
        "target_spec": target_spec,
        "station_deliverable_id": station_deliverable_id,
        "completed": False,
    }


def complete_kill_item(item_id: str, conn: Optional[sqlite3.Connection] = None) -> Dict[str, Any]:
    """Marks daily item done and increments connected active station deliverable atomically."""
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    cursor = conn.cursor()
    cursor.execute(
        "SELECT station_deliverable_id, completed FROM kill_list_items WHERE id = ?",
        (item_id,),
    )
    row = cursor.fetchone()
    if not row:
        if close_conn:
            conn.close()
        return {"success": False, "error": f"Item {item_id} not found"}

    if row["completed"] == 1:
        if close_conn:
            conn.close()
        return {"success": True, "already_completed": True}

    deliverable_id = row["station_deliverable_id"]

    cursor.execute("UPDATE kill_list_items SET completed = 1 WHERE id = ?", (item_id,))

    updated_deliverable = None
    if deliverable_id:
        cursor.execute(
            """
            UPDATE station_deliverable_progress 
            SET completed_count = completed_count + 1,
                is_completed = CASE WHEN completed_count + 1 >= total_required THEN 1 ELSE 0 END
            WHERE deliverable_id = ?
            """,
            (deliverable_id,),
        )
        cursor.execute("SELECT * FROM station_deliverable_progress WHERE deliverable_id = ?", (deliverable_id,))
        d_row = cursor.fetchone()
        if d_row:
            updated_deliverable = {
                "deliverable_id": d_row["deliverable_id"],
                "completed_count": d_row["completed_count"],
                "total_required": d_row["total_required"],
                "is_completed": bool(d_row["is_completed"]),
            }

    conn.commit()

    if close_conn:
        conn.close()

    return {
        "success": True,
        "item_id": item_id,
        "completed": True,
        "deliverable": updated_deliverable,
    }


def toggle_kill_item(item_id: str, conn: Optional[sqlite3.Connection] = None) -> Dict[str, Any]:
    """Toggles completion of a Kill List item and bi-directionally syncs station deliverable."""
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    cursor = conn.cursor()
    cursor.execute(
        "SELECT station_deliverable_id, completed FROM kill_list_items WHERE id = ?",
        (item_id,),
    )
    row = cursor.fetchone()
    if not row:
        if close_conn:
            conn.close()
        return {"success": False, "error": f"Item {item_id} not found"}

    current_status = row["completed"]
    new_status = 0 if current_status == 1 else 1
    deliverable_id = row["station_deliverable_id"]

    cursor.execute("UPDATE kill_list_items SET completed = ? WHERE id = ?", (new_status, item_id))

    updated_deliverable = None
    if deliverable_id:
        delta = 1 if new_status == 1 else -1
        cursor.execute(
            """
            UPDATE station_deliverable_progress 
            SET completed_count = MAX(0, completed_count + ?),
                is_completed = CASE WHEN MAX(0, completed_count + ?) >= total_required THEN 1 ELSE 0 END
            WHERE deliverable_id = ?
            """,
            (delta, delta, deliverable_id),
        )
        cursor.execute("SELECT * FROM station_deliverable_progress WHERE deliverable_id = ?", (deliverable_id,))
        d_row = cursor.fetchone()
        if d_row:
            updated_deliverable = {
                "deliverable_id": d_row["deliverable_id"],
                "completed_count": d_row["completed_count"],
                "total_required": d_row["total_required"],
                "is_completed": bool(d_row["is_completed"]),
            }

    conn.commit()

    if close_conn:
        conn.close()

    return {
        "success": True,
        "item_id": item_id,
        "completed": bool(new_status),
        "deliverable": updated_deliverable,
    }


def delete_kill_item(item_id: str, conn: Optional[sqlite3.Connection] = None) -> bool:
    """Deletes a Kill List item."""
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    cursor = conn.cursor()
    cursor.execute("DELETE FROM kill_list_items WHERE id = ?", (item_id,))
    conn.commit()
    deleted = cursor.rowcount > 0

    if close_conn:
        conn.close()

    return deleted


def get_station_deliverables(
    station_id: str = "sep-2026",
    conn: Optional[sqlite3.Connection] = None,
) -> List[Dict[str, Any]]:
    """Returns all deliverable progress records for a given station ID."""
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    alt_id = station_id.replace("_", "-") if "_" in station_id else station_id.replace("-", "_")

    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT * FROM station_deliverable_progress 
        WHERE station_id = ? OR station_id = ?
        ORDER BY deliverable_id ASC
        """,
        (station_id, alt_id),
    )
    rows = cursor.fetchall()
    results = [
        {
            "deliverable_id": r["deliverable_id"],
            "station_id": r["station_id"],
            "stream": r["stream"],
            "title": r["title"],
            "total_required": r["total_required"],
            "completed_count": r["completed_count"],
            "unit_label": r["unit_label"],
            "is_completed": bool(r["is_completed"]),
        }
        for r in rows
    ]

    if close_conn:
        conn.close()

    return results


def get_station_pace_velocity(
    station_id: str = "sep-2026",
    date_str: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, Any]:
    """
    Station Velocity Indicator (Ghost Beacon):
    Calculates: Target Pace = (Day of Month / Total Days in Month) * Total Required.
    Displays:
      - If completed_count < Target Pace: Pace Deficit: -X units behind schedule
      - On pace / ahead: Pace Velocity: Optimal (+Y)
    """
    target_dt = datetime.strptime(date_str, "%Y-%m-%d") if date_str else datetime.now()
    day_of_month = target_dt.day
    _, total_days_in_month = calendar.monthrange(target_dt.year, target_dt.month)

    deliverables = get_station_deliverables(station_id, conn=conn)

    pace_items = []
    max_deficit = 0.0
    deficit_item_title = ""
    deficit_unit = ""
    overall_behind = False

    for d in deliverables:
        total = d["total_required"]
        comp = d["completed_count"]
        target_pace = (day_of_month / total_days_in_month) * total
        delta = comp - target_pace

        is_behind = comp < target_pace
        deficit = round(target_pace - comp, 1) if is_behind else 0.0

        if deficit > max_deficit:
            max_deficit = deficit
            deficit_item_title = d["title"]
            deficit_unit = d["unit_label"]
            overall_behind = True

        pace_items.append({
            "deliverable_id": d["deliverable_id"],
            "title": d["title"],
            "stream": d["stream"],
            "total_required": total,
            "completed_count": comp,
            "unit_label": d["unit_label"],
            "target_pace": round(target_pace, 1),
            "pace_delta": round(delta, 1),
            "is_behind": is_behind,
            "deficit": deficit,
            "is_completed": d["is_completed"],
        })

    if overall_behind and max_deficit > 0:
        status_text = f"Pace Deficit: -{max_deficit} {deficit_unit}"
        badge_variant = "amber"
    else:
        # Calculate net positive pace delta
        avg_delta = sum(p["pace_delta"] for p in pace_items) / max(1, len(pace_items))
        status_text = f"Pace Velocity: Optimal (+{abs(round(avg_delta, 1))})"
        badge_variant = "optimal"

    return {
        "station_id": station_id,
        "date": target_dt.strftime("%Y-%m-%d"),
        "day_of_month": day_of_month,
        "total_days": total_days_in_month,
        "is_behind": overall_behind,
        "max_deficit": max_deficit,
        "deficit_unit": deficit_unit,
        "status_text": status_text,
        "badge_variant": badge_variant,
        "deliverables": pace_items,
    }
