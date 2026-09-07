"""
Harness Executive OS - Cross-Device Cloud Sync Engine
Provides two-way synchronization between Laptop, Desktop PC, and Cloud Database (Supabase / REST).
100% offline-first: runs locally in SQLite and seamlessly replicates deltas when online.
"""

import json
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
    """Loads sync configuration (URL, API Key, timestamps)."""
    if not CONFIG_FILE.exists():
        save_sync_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return {**DEFAULT_CONFIG, **json.load(f)}
    except Exception:
        return DEFAULT_CONFIG.copy()


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
        with urllib.request.urlopen(req, timeout=5) as response:
            res_body = response.read().decode("utf-8")
            if res_body:
                return json.loads(res_body)
            return {}
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, Exception) as e:
        print(f"[Sync Engine] Request error on {endpoint}: {e}")
        return None


def sync_tasks(conn: sqlite3.Connection) -> int:
    """Two-way sync for daily tasks."""
    remote_tasks = _make_supabase_request("tasks?select=*")
    if remote_tasks is None:
        return 0

    cursor = conn.cursor()
    cursor.execute("SELECT id, title, category, is_tum, completed, date FROM tasks")
    local_tasks = {row["id"]: dict(row) for row in cursor.fetchall()}

    synced_count = 0

    # 1. Pull remote tasks into local SQLite
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
            # If remote completed status is different, update local
            loc = local_tasks[r_id]
            r_comp = 1 if rt.get("completed") else 0
            if loc["completed"] != r_comp:
                cursor.execute("UPDATE tasks SET completed = ? WHERE id = ?", (r_comp, r_id))
                synced_count += 1

    # 2. Push local tasks not present on remote
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


def sync_daily_logs(conn: sqlite3.Connection) -> int:
    """Two-way sync for daily routine blocks and scratchpad."""
    remote_logs = _make_supabase_request("daily_logs?select=*")
    if remote_logs is None:
        return 0

    cursor = conn.cursor()
    cursor.execute("SELECT date, scratchpad, completed_blocks, completed_exercises FROM daily_logs")
    local_logs = {row["date"]: dict(row) for row in cursor.fetchall()}

    synced_count = 0

    # 1. Merge remote logs into local SQLite
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
            # Merge completed blocks
            loc = local_logs[dt]
            loc_blocks = set(filter(None, loc["completed_blocks"].split(",")))
            rem_blocks = set(filter(None, (rl.get("completed_blocks") or "").split(",")))
            merged_blocks = ",".join(sorted(loc_blocks.union(rem_blocks)))

            loc_ex = set(filter(None, loc["completed_exercises"].split(",")))
            rem_ex = set(filter(None, (rl.get("completed_exercises") or "").split(",")))
            merged_ex = ",".join(sorted(loc_ex.union(rem_ex)))

            scratchpad = rl.get("scratchpad") if len(rl.get("scratchpad", "")) >= len(loc["scratchpad"]) else loc["scratchpad"]

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

    # 2. Push local logs to remote
    cursor.execute("SELECT date, scratchpad, completed_blocks, completed_exercises FROM daily_logs")
    for row in cursor.fetchall():
        _make_supabase_request(
            "daily_logs",
            method="POST",
            payload={
                "date": row["date"],
                "scratchpad": row["scratchpad"],
                "completed_blocks": row["completed_blocks"],
                "completed_exercises": row["completed_exercises"],
            },
            headers_extra={"Prefer": "resolution=merge-duplicates"},
        )

    conn.commit()
    return synced_count


def sync_metro_roadmap() -> int:
    """Syncs TUM Metro Station deliverable checkmarks."""
    metro_file = DATA_DIR / "metro_roadmap.json"
    if not metro_file.exists():
        return 0

    with open(metro_file, "r", encoding="utf-8") as f:
        metro_data = json.load(f)

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
            # Merge completed deliverables
            loc_delivs = set(st.get("completed_deliverables", []))
            rem_delivs = set(rem.get("completed_deliverables", []))
            merged = list(loc_delivs.union(rem_delivs))

            total_delivs = len(st.get("deliverables", {}))
            if total_delivs > 0 and len(merged) >= total_delivs:
                st["status"] = "completed"
            st["completed_deliverables"] = merged
            synced_count += 1
        else:
            # Push local station state to remote
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


def sync_all() -> Dict[str, Any]:
    """
    Executes full bi-directional synchronization.
    Returns status payload for UI feedback.
    """
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

        total_synced = tasks_count + logs_count + metro_count
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
        print(f"[Sync Engine] Sync failed: {e}")
        return {
            "status": "offline",
            "message": str(e),
            "synced_count": 0,
            "timestamp": datetime.now().isoformat(),
        }
    finally:
        conn.close()
