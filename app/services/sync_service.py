"""
Harness Executive OS - Cross-Device Cloud Sync Engine (Version 3.5)
Provides two-way synchronization between Laptop, Desktop PC, Vercel Web, and Supabase REST API.
100% offline-first: runs locally in SQLite and seamlessly replicates deltas when online.
"""

import json
import os
import sqlite3
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

from app.db import get_connection, DATA_DIR

CONFIG_FILE = DATA_DIR / "sync_config.json"

DEFAULT_CONFIG = {
    "supabase_url": "https://xfslkbcopnugiubkboux.supabase.co",
    "supabase_key": "",
    "auto_sync": True,
    "last_synced_at": None,
}


def get_sync_config() -> Dict[str, Any]:
    """Loads sync configuration (URL, API Key, timestamps) from env or disk."""
    cfg = DEFAULT_CONFIG.copy()
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg.update(json.load(f))
        except Exception:
            pass

    # Environment variables take precedence (for Vercel / Cloud deployments)
    env_url = os.environ.get("SUPABASE_URL") or os.environ.get("NEXT_PUBLIC_SUPABASE_URL") or os.environ.get("EXPO_PUBLIC_SUPABASE_URL")
    env_key = (
        os.environ.get("SUPABASE_KEY")
        or os.environ.get("SUPABASE_ANON_KEY")
        or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        or os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY")
        or os.environ.get("EXPO_PUBLIC_SUPABASE_ANON_KEY")
    )
    if env_url:
        cfg["supabase_url"] = env_url.strip()
    if env_key:
        cfg["supabase_key"] = env_key.strip()

    return cfg


def save_sync_config(config: Dict[str, Any]) -> None:
    """Saves sync configuration to disk."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def _make_supabase_request(
    endpoint: str,
    method: str = "GET",
    payload: Optional[Any] = None,
    headers_extra: Optional[Dict[str, str]] = None,
) -> Optional[Any]:
    """Sends authenticated REST request to Supabase PostgREST API."""
    cfg = get_sync_config()
    url_base = cfg.get("supabase_url", "").rstrip("/")
    key = cfg.get("supabase_key", "").strip()

    if not url_base or not key:
        return None

    full_url = f"{url_base}/rest/v1/{endpoint}"
    req_headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if headers_extra:
        req_headers.update(headers_extra)

    data_bytes = None
    if payload is not None:
        data_bytes = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(full_url, data=data_bytes, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=6) as response:
            res_body = response.read().decode("utf-8")
            if res_body:
                return json.loads(res_body)
            return {}
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, Exception) as e:
        return None


# =========================================================================
# 1. Tasks Sync
# =========================================================================
def sync_tasks(conn: sqlite3.Connection) -> int:
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, category, is_tum, completed, date FROM tasks")
        local_tasks = {row["id"]: dict(row) for row in cursor.fetchall()}
    except (sqlite3.OperationalError, Exception):
        return 0

    remote_tasks = _make_supabase_request("tasks?select=*")
    if remote_tasks is None:
        return 0

    synced_count = 0
    for rt in remote_tasks:
        r_id = rt.get("id")
        if r_id not in local_tasks:
            cursor.execute(
                """
                INSERT OR REPLACE INTO tasks (id, title, category, is_tum, completed, date)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    r_id,
                    rt.get("title", ""),
                    rt.get("category", "General"),
                    1 if rt.get("is_tum") else 0,
                    1 if rt.get("completed") else 0,
                    rt.get("date", datetime.now().strftime("%Y-%m-%d")),
                ),
            )
            synced_count += 1
        else:
            loc = local_tasks[r_id]
            r_comp = 1 if rt.get("completed") else 0
            if loc["completed"] != r_comp:
                cursor.execute("UPDATE tasks SET completed = ? WHERE id = ?", (r_comp, r_id))
                synced_count += 1

    remote_ids = {rt.get("id") for rt in remote_tasks if rt.get("id")}
    for l_id, loc in local_tasks.items():
        if l_id not in remote_ids:
            _make_supabase_request(
                "tasks",
                method="POST",
                payload={
                    "id": l_id,
                    "title": loc["title"],
                    "category": loc["category"],
                    "is_tum": bool(loc["is_tum"]),
                    "completed": bool(loc["completed"]),
                    "date": loc["date"],
                },
                headers_extra={"Prefer": "resolution=merge-duplicates"},
            )
            synced_count += 1

    conn.commit()
    return synced_count


# =========================================================================
# 2. Daily Logs & Routine Sync
# =========================================================================
def sync_daily_logs(conn: sqlite3.Connection) -> int:
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT date, scratchpad, completed_blocks, completed_exercises FROM daily_logs")
        local_logs = {row["date"]: dict(row) for row in cursor.fetchall()}
    except (sqlite3.OperationalError, Exception):
        return 0

    remote_logs = _make_supabase_request("daily_logs?select=*")
    if remote_logs is None:
        return 0

    synced_count = 0
    for rl in remote_logs:
        dt = rl.get("date")
        if not dt:
            continue
        if dt not in local_logs:
            cursor.execute(
                """
                INSERT OR REPLACE INTO daily_logs (date, scratchpad, completed_blocks, completed_exercises)
                VALUES (?, ?, ?, ?)
                """,
                (
                    dt,
                    rl.get("scratchpad", ""),
                    rl.get("completed_blocks", ""),
                    rl.get("completed_exercises", ""),
                ),
            )
            synced_count += 1
        else:
            loc = local_logs[dt]
            loc_blocks = set(filter(None, (loc.get("completed_blocks") or "").split(",")))
            rem_blocks = set(filter(None, (rl.get("completed_blocks") or "").split(",")))
            merged_blocks = ",".join(sorted(loc_blocks.union(rem_blocks)))

            loc_ex = set(filter(None, (loc.get("completed_exercises") or "").split(",")))
            rem_ex = set(filter(None, (rl.get("completed_exercises") or "").split(",")))
            merged_ex = ",".join(sorted(loc_ex.union(rem_ex)))

            scratchpad = rl.get("scratchpad") if len(rl.get("scratchpad", "")) >= len(loc.get("scratchpad", "")) else loc.get("scratchpad", "")

            if merged_blocks != loc["completed_blocks"] or merged_ex != loc["completed_exercises"] or scratchpad != loc["scratchpad"]:
                cursor.execute(
                    """
                    UPDATE daily_logs 
                    SET completed_blocks = ?, completed_exercises = ?, scratchpad = ?
                    WHERE date = ?
                    """,
                    (merged_blocks, merged_ex, scratchpad, dt),
                )
                synced_count += 1

    cursor.execute("SELECT date, scratchpad, completed_blocks, completed_exercises FROM daily_logs")
    for row in cursor.fetchall():
        _make_supabase_request(
            "daily_logs",
            method="POST",
            payload={
                "date": row["date"],
                "scratchpad": row["scratchpad"] or "",
                "completed_blocks": row["completed_blocks"] or "",
                "completed_exercises": row["completed_exercises"] or "",
            },
            headers_extra={"Prefer": "resolution=merge-duplicates"},
        )

    conn.commit()
    return synced_count


# =========================================================================
# 3. Metro Roadmap & Deliverables Sync
# =========================================================================
def sync_metro_roadmap() -> int:
    metro_file = DATA_DIR / "metro_roadmap.json"
    if not metro_file.exists():
        return 0

    try:
        with open(metro_file, "r", encoding="utf-8") as f:
            metro_data = json.load(f)
    except Exception:
        return 0

    stations = metro_data.get("stations", [])
    remote_stations = _make_supabase_request("metro_stations?select=*")
    if remote_stations is None:
        return 0

    remote_map = {rs.get("id"): rs for rs in remote_stations if rs.get("id")}
    synced_count = 0

    for st in stations:
        st_id = st.get("id")
        if not st_id:
            continue

        if st_id in remote_map:
            rem = remote_map[st_id]
            loc_delivs = set(st.get("completed_deliverables", []))
            rem_delivs = set(rem.get("completed_deliverables", []))
            merged = list(loc_delivs.union(rem_delivs))

            total_delivs = len(st.get("deliverables", {}))
            if total_delivs > 0 and len(merged) >= total_delivs:
                st["status"] = "completed"
            st["completed_deliverables"] = merged
            synced_count += 1
        else:
            _make_supabase_request(
                "metro_stations",
                method="POST",
                payload={
                    "id": st_id,
                    "name": st.get("name", ""),
                    "phase": st.get("phase", ""),
                    "month_label": st.get("month_label", ""),
                    "year_month": st.get("date", ""),
                    "is_major": bool(st.get("is_major")),
                    "status": st.get("status", "upcoming"),
                    "objective": st.get("objective", ""),
                    "deliverables": st.get("deliverables", {}),
                    "completed_deliverables": st.get("completed_deliverables", []),
                    "order_idx": stations.index(st),
                },
                headers_extra={"Prefer": "resolution=merge-duplicates"},
            )

    with open(metro_file, "w", encoding="utf-8") as f:
        json.dump(metro_data, f, indent=2)

    return synced_count


# =========================================================================
# 4. Kill List Items Sync (SGH Library 3-Item Engine)
# =========================================================================
def sync_kill_list_items(conn: sqlite3.Connection) -> int:
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, date, category, title, action_type, target_path, target_spec, station_deliverable_id, completed FROM kill_list_items")
        local_items = {row["id"]: dict(row) for row in cursor.fetchall()}
    except (sqlite3.OperationalError, Exception):
        return 0

    remote_items = _make_supabase_request("kill_list_items?select=*")
    if remote_items is None:
        return 0

    synced_count = 0
    for ri in remote_items:
        r_id = ri.get("id")
        if not r_id:
            continue
        r_comp = 1 if ri.get("completed") else 0
        if r_id not in local_items:
            cursor.execute(
                """
                INSERT OR REPLACE INTO kill_list_items
                (id, date, category, title, action_type, target_path, target_spec, station_deliverable_id, completed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    r_id,
                    ri.get("date", ""),
                    ri.get("category", "General"),
                    ri.get("title", ""),
                    ri.get("action_type", "url"),
                    ri.get("target_path", ""),
                    ri.get("target_spec", ""),
                    ri.get("station_deliverable_id"),
                    r_comp,
                ),
            )
            synced_count += 1
        else:
            if local_items[r_id]["completed"] != r_comp:
                cursor.execute("UPDATE kill_list_items SET completed = ? WHERE id = ?", (r_comp, r_id))
                synced_count += 1

    remote_ids = {ri.get("id") for ri in remote_items if ri.get("id")}
    for l_id, loc in local_items.items():
        if l_id not in remote_ids:
            _make_supabase_request(
                "kill_list_items",
                method="POST",
                payload={
                    "id": l_id,
                    "date": loc["date"],
                    "category": loc["category"],
                    "title": loc["title"],
                    "action_type": loc["action_type"],
                    "target_path": loc["target_path"],
                    "target_spec": loc["target_spec"],
                    "station_deliverable_id": loc["station_deliverable_id"],
                    "completed": bool(loc["completed"]),
                },
                headers_extra={"Prefer": "resolution=merge-duplicates"},
            )
            synced_count += 1

    conn.commit()
    return synced_count


# =========================================================================
# 5. Station Deliverable Progress Sync
# =========================================================================
def sync_station_deliverable_progress(conn: sqlite3.Connection) -> int:
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT deliverable_id, station_id, stream, title, total_required, completed_count, unit_label, is_completed FROM station_deliverable_progress")
        local_map = {row["deliverable_id"]: dict(row) for row in cursor.fetchall()}
    except (sqlite3.OperationalError, Exception):
        return 0

    remote_delivs = _make_supabase_request("station_deliverable_progress?select=*")
    if remote_delivs is None:
        return 0

    synced_count = 0
    for rd in remote_delivs:
        d_id = rd.get("deliverable_id")
        if not d_id:
            continue
        rem_count = rd.get("completed_count", 0)
        rem_done = 1 if rd.get("is_completed") else 0
        if d_id in local_map:
            loc = local_map[d_id]
            max_count = max(loc["completed_count"], rem_count)
            is_done = 1 if (max_count >= loc["total_required"] or loc["is_completed"] or rem_done) else 0
            if max_count != loc["completed_count"] or is_done != loc["is_completed"]:
                cursor.execute("UPDATE station_deliverable_progress SET completed_count = ?, is_completed = ? WHERE deliverable_id = ?", (max_count, is_done, d_id))
                synced_count += 1
        else:
            cursor.execute(
                """
                INSERT OR REPLACE INTO station_deliverable_progress
                (deliverable_id, station_id, stream, title, total_required, completed_count, unit_label, is_completed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    d_id,
                    rd.get("station_id", "sep-2026"),
                    rd.get("stream", "code"),
                    rd.get("title", ""),
                    rd.get("total_required", 1),
                    rem_count,
                    rd.get("unit_label", "reps"),
                    rem_done,
                ),
            )
            synced_count += 1

    cursor.execute("SELECT deliverable_id, station_id, stream, title, total_required, completed_count, unit_label, is_completed FROM station_deliverable_progress")
    for row in cursor.fetchall():
        _make_supabase_request(
            "station_deliverable_progress",
            method="POST",
            payload={
                "deliverable_id": row["deliverable_id"],
                "station_id": row["station_id"],
                "stream": row["stream"],
                "title": row["title"],
                "total_required": row["total_required"],
                "completed_count": row["completed_count"],
                "unit_label": row["unit_label"],
                "is_completed": bool(row["is_completed"]),
            },
            headers_extra={"Prefer": "resolution=merge-duplicates"},
        )

    conn.commit()
    return synced_count


# =========================================================================
# Master Multi-Entity Synchronizer
# =========================================================================
def sync_all() -> Dict[str, Any]:
    """Executes full bi-directional synchronization across all tables."""
    cfg = get_sync_config()
    if not cfg.get("supabase_key"):
        return {
            "status": "unconfigured",
            "message": "Supabase key not configured in JSON Hub",
            "synced_count": 0,
            "timestamp": datetime.now().isoformat(),
        }

    conn = get_connection()
    try:
        tasks_count = sync_tasks(conn)
        logs_count = sync_daily_logs(conn)
        metro_count = sync_metro_roadmap()
        kill_count = sync_kill_list_items(conn)
        deliv_count = sync_station_deliverable_progress(conn)

        total_synced = tasks_count + logs_count + metro_count + kill_count + deliv_count
        now_iso = datetime.now().isoformat()

        cfg["last_synced_at"] = now_iso
        save_sync_config(cfg)

        return {
            "status": "synced",
            "message": f"Successfully synced {total_synced} updates",
            "synced_count": total_synced,
            "timestamp": now_iso,
        }
    except Exception as e:
        return {
            "status": "offline",
            "message": str(e),
            "synced_count": 0,
            "timestamp": datetime.now().isoformat(),
        }
    finally:
        conn.close()
