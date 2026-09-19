"""Kill List & Metro Auto-Increment Controller (Harness 2.1).

Eliminates decision friction by enforcing the 3-Item Rule for SGH Library TUM Deep Work blocks,
wires native OS/browser triggers (PDF, URL, VS Code), and executes atomic SQLite increments
linking completed kill-items to the active 24-month TUM Metro Line deliverables.
"""

import calendar
import json
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

    # Auto-carryover: Uncompleted kill items from prior days roll forward to today (up to 3-Item limit)
    today_str = datetime.now().strftime("%Y-%m-%d")
    if target_date == today_str:
        cursor.execute("SELECT COUNT(*) AS cnt FROM kill_list_items WHERE date = ?", (today_str,))
        existing_count = cursor.fetchone()["cnt"]
        if existing_count < 3:
            needed = 3 - existing_count
            cursor.execute(
                """
                SELECT id FROM kill_list_items
                WHERE date < ? AND completed = 0
                ORDER BY date ASC, created_at ASC
                LIMIT ?
                """,
                (today_str, needed),
            )
            rollover_rows = cursor.fetchall()
            for r in rollover_rows:
                cursor.execute(
                    "UPDATE kill_list_items SET date = ? WHERE id = ?",
                    (today_str, r["id"]),
                )
            if rollover_rows:
                conn.commit()

    cursor.execute(
        """
        SELECT 
            k.id, k.date, k.category, k.title, k.action_type, k.target_path, k.target_spec,
            k.station_deliverable_id, k.quantity, k.completed, k.created_at,
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
            "quantity": r["quantity"] if "quantity" in r.keys() else 1,
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
    quantity: int = 1,
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

    qty = max(1, int(quantity or 1))
    item_id = f"kill_{uuid.uuid4().hex[:8]}"
    d_id = station_deliverable_id or None
    if d_id == "sep26_hackerrank_15":
        d_id = "sep26_leetcode_15"

    cursor.execute(
        """
        INSERT INTO kill_list_items 
        (id, date, category, title, action_type, target_path, target_spec, station_deliverable_id, quantity, completed)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
        """,
        (
            item_id,
            target_date,
            category.strip(),
            title.strip(),
            action_type.strip().lower(),
            target_path.strip(),
            target_spec.strip(),
            d_id,
            qty,
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
        "quantity": qty,
        "completed": False,
    }


def compute_progressive_spec(deliverable_id: str, completed_count: int, total_required: int = 100) -> Dict[str, Any]:
    """
    Computes dynamic next progressive target specification, quantity, and resource path.
    Enables automatic sequential advancement (e.g. CKE Zadania 1–5 -> 6–10, LeetCode #4 -> #5).
    """
    d_id = (deliverable_id or "").lower()
    comp = max(0, int(completed_count or 0))
    total = max(1, int(total_required or 100))

    if "math" in d_id:
        step = 5
        start = comp + 1
        end = min(total, comp + step)
        return {
            "category": "Math R",
            "title": f"Math R Diagnostic: Zadania {start}–{end}",
            "target_spec": f"Zadania {start}–{end} (Zero-AI, pen & paper)",
            "quantity": step,
            "action_type": "pdf",
            "target_path": "https://cke.gov.pl",
        }
    elif "leetcode" in d_id or "hackerrank" in d_id or "code" in d_id:
        prob_num = comp + 1
        return {
            "category": "Algorithms",
            "title": f"LeetCode: Problem #{prob_num} (Unassisted)",
            "target_spec": f"Problem #{prob_num} (Zero-AI, trace by hand)",
            "quantity": 1,
            "action_type": "url",
            "target_path": "https://leetcode.com/problemset/all/",
        }
    elif "german" in d_id or "anki" in d_id:
        step = 20
        start = comp + 1
        end = min(total, comp + step)
        return {
            "category": "German",
            "title": f"German Vocabulary: Words {start}–{end}",
            "target_spec": f"Words {start}–{end} (Nicos Weg A2)",
            "quantity": step,
            "action_type": "url",
            "target_path": "https://learngerman.dw.com/en/nicos-weg/c-36519789",
        }
    elif "sigg" in d_id:
        return {
            "category": "SIGG",
            "title": "SIGG 2025/2026: Scanner Workspace",
            "target_spec": "Scan mWIG40 momentum & liquidity",
            "quantity": 1,
            "action_type": "workspace",
            "target_path": r"c:\Users\heito\Desktop\polish_stocks_day_trade-main",
        }
    elif "protein" in d_id or "phys" in d_id:
        return {
            "category": "Physical",
            "title": "Nutrition: 140g Daily Protein Floor",
            "target_spec": "Log 140g high-protein meals",
            "quantity": 1,
            "action_type": "url",
            "target_path": "https://www.myfitnesspal.com",
        }
    else:
        return {
            "category": "Deep Work",
            "title": f"Next Session Deliverable Rep",
            "target_spec": f"Sequential target #{comp + 1}",
            "quantity": 1,
            "action_type": "url",
            "target_path": "",
        }


def enqueue_progressive_deliverable(
    deliverable_id: str,
    date_str: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, Any]:
    """1-click enqueues the next progressive sequential deliverable into the Kill List."""
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    cursor = conn.cursor()
    cursor.execute("SELECT * FROM station_deliverable_progress WHERE deliverable_id = ?", (deliverable_id,))
    row = cursor.fetchone()
    if not row:
        if close_conn:
            conn.close()
        raise ValueError(f"Deliverable {deliverable_id} not found")

    prog = compute_progressive_spec(deliverable_id, row["completed_count"], row["total_required"])
    res = add_kill_item(
        category=prog["category"],
        title=prog["title"],
        action_type=prog["action_type"],
        target_path=prog["target_path"],
        target_spec=prog["target_spec"],
        station_deliverable_id=deliverable_id,
        quantity=prog["quantity"],
        date_str=date_str,
        conn=conn,
    )

    if close_conn:
        conn.close()
    return res


def enqueue_exam_prep(
    exam_id: int,
    date_str: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, Any]:
    """1-click enqueues an upcoming school exam preparation session into the Kill List."""
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    cursor = conn.cursor()
    cursor.execute("SELECT * FROM school_exams WHERE id = ?", (exam_id,))
    row = cursor.fetchone()
    if not row:
        if close_conn:
            conn.close()
        raise ValueError(f"Exam {exam_id} not found")

    title = f"Exam Prep: {row['subject']} ({row['title']})"
    scope_str = f" — Scope: {row['scope']}" if row['scope'] else ""
    target_spec = f"Core concept drill & problem sets{scope_str}"

    res = add_kill_item(
        category="Exam Prep",
        title=title,
        action_type="pdf",
        target_path="https://cke.gov.pl",
        target_spec=target_spec,
        station_deliverable_id=None,
        quantity=1,
        date_str=date_str,
        conn=conn,
    )

    if close_conn:
        conn.close()
    return res


def enqueue_homework_prep(
    hw_id: int,
    date_str: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, Any]:
    """1-click enqueues an urgent school homework assignment into the Kill List."""
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    cursor = conn.cursor()
    cursor.execute("SELECT * FROM homework_items WHERE id = ?", (hw_id,))
    row = cursor.fetchone()
    if not row:
        if close_conn:
            conn.close()
        raise ValueError(f"Homework {hw_id} not found")

    priority_val = row["priority"] if "priority" in row.keys() else 1
    target_spec = f"Due: {row['due_date']} (Priority {priority_val})"
    title = f"Homework: {row['subject']} - {row['title']}"

    res = add_kill_item(
        category="Homework",
        title=title,
        action_type="url",
        target_path="https://uonetplus.vulcan.net.pl",
        target_spec=target_spec,
        station_deliverable_id=None,
        quantity=1,
        date_str=date_str,
        conn=conn,
    )

    if close_conn:
        conn.close()
    return res


def complete_kill_item(item_id: str, conn: Optional[sqlite3.Connection] = None) -> Dict[str, Any]:
    """Marks daily item done and increments connected active station deliverable atomically."""
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    cursor = conn.cursor()
    cursor.execute(
        "SELECT station_deliverable_id, quantity, completed FROM kill_list_items WHERE id = ?",
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
    if deliverable_id == "sep26_hackerrank_15":
        deliverable_id = "sep26_leetcode_15"
    qty = row["quantity"] if "quantity" in row.keys() and row["quantity"] else 1

    cursor.execute("UPDATE kill_list_items SET completed = 1 WHERE id = ?", (item_id,))

    updated_deliverable = None
    if deliverable_id:
        cursor.execute(
            """
            UPDATE station_deliverable_progress 
            SET completed_count = completed_count + ?,
                is_completed = CASE WHEN completed_count + ? >= total_required THEN 1 ELSE 0 END
            WHERE deliverable_id = ?
            """,
            (qty, qty, deliverable_id),
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
        "SELECT station_deliverable_id, quantity, completed FROM kill_list_items WHERE id = ?",
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
    if deliverable_id == "sep26_hackerrank_15":
        deliverable_id = "sep26_leetcode_15"
    qty = row["quantity"] if "quantity" in row.keys() and row["quantity"] else 1

    cursor.execute("UPDATE kill_list_items SET completed = ? WHERE id = ?", (new_status, item_id))

    updated_deliverable = None
    if deliverable_id:
        delta = qty if new_status == 1 else -qty
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
            "next_spec": compute_progressive_spec(r["deliverable_id"], r["completed_count"], r["total_required"]),
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
        "deficit_item_title": deficit_item_title,
        "deficit_unit": deficit_unit,
        "status_text": status_text,
        "badge_variant": badge_variant,
        "deliverables": pace_items,
    }


def update_deliverable_progress(
    deliverable_id: str,
    new_count: Optional[int] = None,
    delta: Optional[int] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, Any]:
    """
    Sets or increments the completed count for a station deliverable,
    automatically syncing completion flag and metro_roadmap.json.
    """
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM station_deliverable_progress WHERE deliverable_id = ?",
        (deliverable_id,),
    )
    row = cursor.fetchone()
    if not row:
        if close_conn:
            conn.close()
        return {"success": False, "error": f"Deliverable {deliverable_id} not found"}

    total_required = row["total_required"]
    station_id = row["station_id"]
    curr_count = row["completed_count"]

    if new_count is not None:
        updated_count = max(0, int(new_count))
    elif delta is not None:
        updated_count = max(0, curr_count + int(delta))
    else:
        updated_count = curr_count

    is_done = 1 if updated_count >= total_required else 0

    cursor.execute(
        """
        UPDATE station_deliverable_progress 
        SET completed_count = ?, is_completed = ?
        WHERE deliverable_id = ?
        """,
        (updated_count, is_done, deliverable_id),
    )
    conn.commit()

    # Sync with metro_roadmap.json
    try:
        roadmap_file = DATA_DIR / "metro_roadmap.json"
        if roadmap_file.exists():
            with open(roadmap_file, "r", encoding="utf-8") as f:
                mdata = json.load(f)
            target_station = next(
                (s for s in mdata.get("stations", []) if s.get("id") == station_id or s.get("id") == station_id.replace("_", "-")),
                None
            )
            if target_station:
                comp_list = target_station.get("completed_deliverables", [])
                stream_key = row["stream"]
                deliv_dict = target_station.get("deliverables", {})
                matched_key = None
                for k in deliv_dict.keys():
                    if k.lower() == stream_key.lower() or stream_key.lower() in k.lower() or k.lower() in stream_key.lower():
                        matched_key = k
                        break

                if matched_key:
                    if is_done and matched_key not in comp_list:
                        comp_list.append(matched_key)
                    elif not is_done and matched_key in comp_list:
                        comp_list.remove(matched_key)

                    target_station["completed_deliverables"] = comp_list
                    if len(deliv_dict) > 0 and len(comp_list) >= len(deliv_dict) and all(k in comp_list for k in deliv_dict.keys()):
                        target_station["status"] = "completed"
                    elif target_station.get("status") == "completed" and not is_done:
                        target_station["status"] = "active"

                    with open(roadmap_file, "w", encoding="utf-8") as f:
                        json.dump(mdata, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

    if close_conn:
        conn.close()

    return {
        "success": True,
        "deliverable_id": deliverable_id,
        "station_id": station_id,
        "completed_count": updated_count,
        "total_required": total_required,
        "is_completed": bool(is_done),
        "unit_label": row["unit_label"],
    }


def log_study_reps(
    deliverable_id: str,
    count: int,
    notes: str = "",
    conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, Any]:
    """Logs positive study reps (words, problems, exercises) directly into deliverable progress."""
    return update_deliverable_progress(deliverable_id, delta=count, conn=conn)


def auto_populate_kill_list(
    date_str: Optional[str] = None,
    station_id: str = "sep-2026",
    conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, Any]:
    """
    Zero-Decision Auto-Populator for the daily Kill List.
    Eliminates decision friction by automatically filling up to 3 optimal deep work targets:
      Slot 1: Acute School Exam defense (if exam in <= 5 days) OR Core Math R deliverable.
      Slot 2: Unassisted Coding / Algorithmic deliverable (LeetCode #N).
      Slot 3: German vocabulary (Anki / Nicos Weg A2) or secondary focus.
    """
    target_date = date_str or datetime.now().strftime("%Y-%m-%d")
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) AS cnt FROM kill_list_items WHERE date = ?", (target_date,))
    count = cursor.fetchone()["cnt"]
    if count >= 3:
        res = get_kill_list(target_date, conn=conn)
        if close_conn:
            conn.close()
        return res

    # Fetch existing items to prevent duplicate categories/deliverables
    cursor.execute(
        "SELECT station_deliverable_id, title, category FROM kill_list_items WHERE date = ?",
        (target_date,),
    )
    existing_rows = cursor.fetchall()
    existing_deliv_ids = {r["station_deliverable_id"] for r in existing_rows if r["station_deliverable_id"]}
    existing_titles = {r["title"].lower() for r in existing_rows}
    existing_cats = {r["category"].lower() for r in existing_rows}

    # 1. Dynamically adapt school defense slots to weekly test volume and homework deadlines
    from app.services import homework_service
    upcoming_exams = homework_service.get_upcoming_exams(conn=conn, limit=5, today_str=target_date)
    acute_exams = [
        e for e in upcoming_exams
        if not e["completed"] and 0 <= e.get("days_left", 99) <= 5
        and not any(e["subject"].lower() in t for t in existing_titles)
        and "exam prep" not in existing_cats
    ]

    all_hw = homework_service.get_upcoming_homework(conn=conn, today_str=target_date)
    urgent_hw = [
        h for h in all_hw
        if not h["completed"] and 0 <= h.get("days_left", 99) <= 2
        and not any(h["title"].lower() in t for t in existing_titles)
        and "homework" not in existing_cats
    ]

    # Academic density determination:
    # If 2+ acute school commitments (multiple tests or test + urgent homework), allocate up to 2 slots
    # to academic defense while preserving at least 1 slot for TUM anchor (Math R or LeetCode).
    school_slots_max = 2 if (len(acute_exams) >= 2 or (acute_exams and urgent_hw) or len(urgent_hw) >= 2) else (1 if (acute_exams or urgent_hw) else 0)
    school_slots_used = 0

    # Urgent homework due today/tomorrow gets immediate defense
    if urgent_hw and (not acute_exams or urgent_hw[0].get("days_left", 99) <= acute_exams[0].get("days_left", 99)):
        hw_item = urgent_hw[0]
        if count < 3 and school_slots_used < school_slots_max:
            try:
                enqueue_homework_prep(hw_item["id"], date_str=target_date, conn=conn)
                count += 1
                school_slots_used += 1
                existing_cats.add("homework")
                existing_titles.add(hw_item["title"].lower())
            except Exception:
                pass

    # Acute upcoming exams
    for ex in acute_exams:
        if count >= 3 or school_slots_used >= school_slots_max:
            break
        try:
            enqueue_exam_prep(ex["id"], date_str=target_date, conn=conn)
            count += 1
            school_slots_used += 1
            existing_cats.add("exam prep")
            existing_titles.add(ex["subject"].lower())
        except Exception:
            pass

    # Remaining urgent homework if school defense capacity remains
    if count < 3 and school_slots_used < school_slots_max:
        for hw_item in urgent_hw:
            if count >= 3 or school_slots_used >= school_slots_max:
                break
            if hw_item["title"].lower() in existing_titles:
                continue
            try:
                enqueue_homework_prep(hw_item["id"], date_str=target_date, conn=conn)
                count += 1
                school_slots_used += 1
                existing_cats.add("homework")
                existing_titles.add(hw_item["title"].lower())
            except Exception:
                pass

    # 2. Fetch station deliverables for active station
    station_delivs = get_station_deliverables(station_id, conn=conn)

    # Slot: Math R
    if count < 3:
        math_delivs = [
            d for d in station_delivs
            if "math" in d["deliverable_id"].lower()
            and not d["is_completed"]
            and d["deliverable_id"] not in existing_deliv_ids
            and "math r" not in existing_cats
        ]
        if math_delivs:
            try:
                enqueue_progressive_deliverable(math_delivs[0]["deliverable_id"], date_str=target_date, conn=conn)
                count += 1
                existing_deliv_ids.add(math_delivs[0]["deliverable_id"])
                existing_cats.add("math r")
            except Exception:
                pass

    # Slot: LeetCode / Unassisted Algorithms
    if count < 3:
        code_delivs = [
            d for d in station_delivs
            if any(k in d["deliverable_id"].lower() for k in ["leetcode", "code", "algo"])
            and not d["is_completed"]
            and d["deliverable_id"] not in existing_deliv_ids
            and "algorithms" not in existing_cats
        ]
        if code_delivs:
            try:
                enqueue_progressive_deliverable(code_delivs[0]["deliverable_id"], date_str=target_date, conn=conn)
                count += 1
                existing_deliv_ids.add(code_delivs[0]["deliverable_id"])
                existing_cats.add("algorithms")
            except Exception:
                pass

    # Slot: German / Language
    if count < 3:
        lang_delivs = [
            d for d in station_delivs
            if any(k in d["deliverable_id"].lower() for k in ["german", "anki", "lang"])
            and not d["is_completed"]
            and d["deliverable_id"] not in existing_deliv_ids
            and "german" not in existing_cats
        ]
        if lang_delivs:
            try:
                enqueue_progressive_deliverable(lang_delivs[0]["deliverable_id"], date_str=target_date, conn=conn)
                count += 1
                existing_deliv_ids.add(lang_delivs[0]["deliverable_id"])
                existing_cats.add("german")
            except Exception:
                pass

    # Fallback: Any other incomplete station deliverable
    if count < 3:
        other_delivs = [
            d for d in station_delivs
            if not d["is_completed"] and d["deliverable_id"] not in existing_deliv_ids
        ]
        for d in other_delivs:
            if count >= 3:
                break
            try:
                enqueue_progressive_deliverable(d["deliverable_id"], date_str=target_date, conn=conn)
                count += 1
                existing_deliv_ids.add(d["deliverable_id"])
            except Exception:
                pass

    res = get_kill_list(target_date, conn=conn)
    if close_conn:
        conn.close()
    return res

