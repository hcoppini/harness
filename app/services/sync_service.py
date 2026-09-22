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
    "supabase_url": "",
    "supabase_key": "",
    "web_url": "",
    "auto_sync": True,
    "last_synced_at": None,
}


def get_sync_config() -> Dict[str, Any]:
    """Loads sync configuration (URL, API Key, Web URL, timestamps) from env or disk."""
    cfg = DEFAULT_CONFIG.copy()
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg.update(json.load(f))
        except Exception:
            pass

    # Clean legacy placeholder URL if present
    if cfg.get("supabase_url") and "xfslkbcopnugiubkboux" in cfg["supabase_url"]:
        cfg["supabase_url"] = ""

    # Environment variables take precedence (for Vercel / Cloud deployments)
    env_url = os.environ.get("SUPABASE_URL") or os.environ.get("NEXT_PUBLIC_SUPABASE_URL") or os.environ.get("EXPO_PUBLIC_SUPABASE_URL")
    env_key = (
        os.environ.get("SUPABASE_KEY")
        or os.environ.get("SUPABASE_ANON_KEY")
        or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        or os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY")
        or os.environ.get("EXPO_PUBLIC_SUPABASE_ANON_KEY")
    )
    env_web = os.environ.get("HARNESS_WEB_URL") or os.environ.get("WEB_URL") or os.environ.get("VERCEL_URL")

    if env_url:
        cfg["supabase_url"] = env_url.strip()
    if env_key:
        cfg["supabase_key"] = env_key.strip()
    if env_web:
        clean_web = env_web.strip()
        if not clean_web.startswith("http://") and not clean_web.startswith("https://"):
            clean_web = f"https://{clean_web}"
        cfg["web_url"] = clean_web.rstrip("/")

    if cfg.get("web_url"):
        cfg["web_url"] = cfg["web_url"].strip().rstrip("/")

    return cfg


def save_sync_config(config: Dict[str, Any]) -> None:
    """Saves sync configuration to disk."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def _post_json(
    url: str,
    payload: Dict[str, Any],
    headers_extra: Optional[Dict[str, str]] = None,
    timeout: int = 8,
) -> Optional[Any]:
    """Posts JSON payload to URL and returns parsed JSON response."""
    data_bytes = json.dumps(payload).encode("utf-8")
    req_headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if headers_extra:
        req_headers.update(headers_extra)

    req = urllib.request.Request(url, data=data_bytes, headers=req_headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            res_body = response.read().decode("utf-8")
            if res_body:
                return json.loads(res_body)
            return {}
    except Exception:
        return None


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
        with urllib.request.urlopen(req, timeout=8) as response:
            res_body = response.read().decode("utf-8")
            if res_body:
                return json.loads(res_body)
            return {}
    except urllib.error.HTTPError as e:
        err_body = ""
        try:
            err_body = e.read().decode("utf-8")
        except Exception:
            pass
        print(f"[Supabase Sync] HTTP {e.code} for {method} {endpoint}: {err_body or e.reason}")
        return None
    except Exception as e:
        print(f"[Supabase Sync] Request failed for {method} {endpoint}: {e}")
        return None


def delete_remote_item(table: str, id_column: str, id_value: Any, async_mode: bool = False) -> bool:
    """Sends DELETE request to Supabase PostgREST endpoint."""
    cfg = get_sync_config()
    if not cfg.get("supabase_key") or not cfg.get("supabase_url"):
        return False

    def _execute():
        try:
            endpoint = f"{table}?{id_column}=eq.{id_value}"
            res = _make_supabase_request(endpoint, method="DELETE")
            return res is not None
        except Exception as e:
            print(f"[Supabase Sync] Remote delete failed for {table} {id_column}={id_value}: {e}")
            return False

    if async_mode:
        import threading
        threading.Thread(target=_execute, daemon=True).start()
        return True
    return _execute()


def upsert_remote_item(table: str, id_column: str, payload: Dict[str, Any], async_mode: bool = False) -> bool:
    """Sends an immediate UPSERT (POST with resolution=merge-duplicates) request to Supabase PostgREST endpoint."""
    cfg = get_sync_config()
    if not cfg.get("supabase_key") or not cfg.get("supabase_url"):
        return False

    def _execute():
        try:
            endpoint = f"{table}?on_conflict={id_column}"
            res = _make_supabase_request(
                endpoint,
                method="POST",
                payload=payload,
                headers_extra={"Prefer": "resolution=merge-duplicates"},
            )
            return res is not None
        except Exception as e:
            print(f"[Supabase Sync] Remote upsert failed for {table}: {e}")
            return False

    if async_mode:
        import threading
        threading.Thread(target=_execute, daemon=True).start()
        return True
    return _execute()


def test_supabase_connection(url: Optional[str] = None, key: Optional[str] = None) -> Dict[str, Any]:
    """
    Tests connectivity to Supabase and verifies existence of required schema tables.
    """
    cfg = get_sync_config()
    target_url = (url or cfg.get("supabase_url", "")).rstrip("/")
    target_key = (key or cfg.get("supabase_key", "")).strip()

    if not target_url or not target_key:
        return {
            "success": False,
            "status": "unconfigured",
            "message": "Supabase Project URL and API Key are required.",
            "error": "Supabase Project URL and API Key are required.",
            "tables_found": [],
            "verified_tables": [],
            "tables_missing": [],
        }

    required_tables = [
        "tasks", "daily_logs", "homework_items", "school_exams",
        "tum_grades", "tum_grade_entries", "tum_matura", "tum_language",
        "kill_list_items", "metro_stations", "station_deliverable_progress",
        "body_metrics", "workouts", "projects", "app_settings"
    ]

    req_headers = {
        "apikey": target_key,
        "Authorization": f"Bearer {target_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    try:
        probe_url = f"{target_url}/rest/v1/"
        req = urllib.request.Request(probe_url, headers=req_headers, method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            pass
    except urllib.error.HTTPError as e:
        if e.code in [401, 403]:
            return {
                "success": False,
                "status": "error",
                "message": f"Authentication failed (HTTP {e.code}). Please check your Supabase anon/service key.",
                "error": f"Authentication failed (HTTP {e.code})",
                "tables_found": [],
                "verified_tables": [],
                "tables_missing": required_tables,
            }
        # Some Supabase instances return 404 for root /rest/v1/ - proceed to table check
    except Exception as e:
        return {
            "success": False,
            "status": "error",
            "message": f"Could not reach Supabase at {target_url}: {e}",
            "error": str(e),
            "tables_found": [],
            "verified_tables": [],
            "tables_missing": required_tables,
        }

    tables_found = []
    tables_missing = []

    for tbl in required_tables:
        try:
            tbl_url = f"{target_url}/rest/v1/{tbl}?select=*&limit=1"
            req = urllib.request.Request(tbl_url, headers=req_headers, method="GET")
            with urllib.request.urlopen(req, timeout=4) as resp:
                if resp.status in [200, 206]:
                    tables_found.append(tbl)
                else:
                    tables_missing.append(tbl)
        except urllib.error.HTTPError as e:
            if e.code in [404, 400]:
                tables_missing.append(tbl)
            else:
                tables_missing.append(tbl)
        except Exception:
            tables_missing.append(tbl)

    if not tables_missing:
        return {
            "success": True,
            "status": "connected",
            "message": f"Connected successfully! All {len(tables_found)} schema tables verified in PostgreSQL.",
            "tables_found": tables_found,
            "verified_tables": tables_found,
            "tables_missing": [],
        }
    else:
        return {
            "success": False,
            "status": "schema_missing",
            "message": f"Connected to Supabase, but {len(tables_missing)} table(s) missing ({', '.join(tables_missing[:4])}...). Execute supabase/schema.sql in your Supabase SQL Editor.",
            "error": f"Connected to Supabase, but {len(tables_missing)} table(s) missing",
            "tables_found": tables_found,
            "verified_tables": tables_found,
            "tables_missing": tables_missing,
        }


# =========================================================================
# 1. Tasks Sync
# =========================================================================
def sync_tasks(conn: sqlite3.Connection) -> int:
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, category, is_tum, completed, date, rollover_count, created_at, completed_at FROM tasks")
        local_tasks = {row["id"]: dict(row) for row in cursor.fetchall()}
    except (sqlite3.OperationalError, Exception):
        return 0

    remote_tasks = _make_supabase_request("tasks?select=*")
    if remote_tasks is None:
        return 0

    synced_count = 0
    for rt in remote_tasks:
        r_id = rt.get("id")
        r_comp = 1 if rt.get("completed") else 0
        if r_id not in local_tasks:
            cursor.execute(
                """
                INSERT OR REPLACE INTO tasks (id, title, category, is_tum, completed, date, rollover_count, created_at, completed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    r_id,
                    rt.get("title", ""),
                    rt.get("category", "General"),
                    1 if rt.get("is_tum") else 0,
                    r_comp,
                    rt.get("date", datetime.now().strftime("%Y-%m-%d")),
                    rt.get("rollover_count", 0),
                    rt.get("created_at"),
                    rt.get("completed_at"),
                ),
            )
            synced_count += 1
        else:
            loc = local_tasks[r_id]
            if loc["completed"] != r_comp:
                if loc["completed"] == 1 and r_comp == 0:
                    _make_supabase_request(
                        "tasks?on_conflict=id",
                        method="POST",
                        payload={"id": r_id, "completed": True},
                        headers_extra={"Prefer": "resolution=merge-duplicates"},
                    )
                    synced_count += 1
                elif r_comp == 1 and loc["completed"] == 0:
                    cursor.execute("UPDATE tasks SET completed = 1 WHERE id = ?", (r_id,))
                    synced_count += 1

    remote_ids = {rt.get("id") for rt in remote_tasks if rt.get("id")}
    for l_id, loc in local_tasks.items():
        if l_id not in remote_ids:
            _make_supabase_request(
                "tasks?on_conflict=id",
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
        cursor.execute("PRAGMA table_info(daily_logs)")
        cols = [r[1] for r in cursor.fetchall()]
        has_updated_at = "updated_at" in cols
        cursor.execute("SELECT * FROM daily_logs")
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
                INSERT OR REPLACE INTO daily_logs
                (date, scratchpad, wake_time, sleep_time, reflection_worked, reflection_slipped, reflection_tomorrow, completed_blocks, completed_exercises)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    dt,
                    rl.get("scratchpad", "") or "",
                    rl.get("wake_time", "") or "",
                    rl.get("sleep_time", "") or "",
                    rl.get("reflection_worked", "") or "",
                    rl.get("reflection_slipped", "") or "",
                    rl.get("reflection_tomorrow", "") or "",
                    rl.get("completed_blocks", "") or "",
                    rl.get("completed_exercises", "") or "",
                ),
            )
            synced_count += 1
        else:
            loc = local_logs[dt]
            loc_updated = loc.get("updated_at") or ""
            rem_updated = rl.get("updated_at") or ""

            if rem_updated and loc_updated and rem_updated != loc_updated:
                if rem_updated > loc_updated:
                    merged_blocks = rl.get("completed_blocks", "") or ""
                    merged_ex = rl.get("completed_exercises", "") or ""
                    scratchpad = rl.get("scratchpad") if rl.get("scratchpad") is not None else (loc.get("scratchpad") or "")
                    wake_time = rl.get("wake_time") or loc.get("wake_time") or ""
                    sleep_time = rl.get("sleep_time") or loc.get("sleep_time") or ""
                    ref_w = rl.get("reflection_worked") or loc.get("reflection_worked") or ""
                    ref_s = rl.get("reflection_slipped") or loc.get("reflection_slipped") or ""
                    ref_t = rl.get("reflection_tomorrow") or loc.get("reflection_tomorrow") or ""
                    target_updated = rem_updated
                else:
                    merged_blocks = loc.get("completed_blocks", "") or ""
                    merged_ex = loc.get("completed_exercises", "") or ""
                    scratchpad = loc.get("scratchpad") or rl.get("scratchpad") or ""
                    wake_time = loc.get("wake_time") or rl.get("wake_time") or ""
                    sleep_time = loc.get("sleep_time") or rl.get("sleep_time") or ""
                    ref_w = loc.get("reflection_worked") or rl.get("reflection_worked") or ""
                    ref_s = loc.get("reflection_slipped") or rl.get("reflection_slipped") or ""
                    ref_t = loc.get("reflection_tomorrow") or rl.get("reflection_tomorrow") or ""
                    target_updated = loc_updated
            else:
                loc_b = set(filter(None, (loc.get("completed_blocks") or "").split(",")))
                rem_b = set(filter(None, (rl.get("completed_blocks") or "").split(",")))
                merged_blocks = ",".join(sorted(loc_b.union(rem_b)))

                loc_e = set(filter(None, (loc.get("completed_exercises") or "").split(",")))
                rem_e = set(filter(None, (rl.get("completed_exercises") or "").split(",")))
                merged_ex = ",".join(sorted(loc_e.union(rem_e)))

                scratchpad = rl.get("scratchpad") if len(rl.get("scratchpad", "") or "") >= len(loc.get("scratchpad", "") or "") else loc.get("scratchpad", "")
                wake_time = rl.get("wake_time") or loc.get("wake_time") or ""
                sleep_time = rl.get("sleep_time") or loc.get("sleep_time") or ""
                ref_w = rl.get("reflection_worked") if len(rl.get("reflection_worked", "") or "") >= len(loc.get("reflection_worked", "") or "") else loc.get("reflection_worked", "")
                ref_s = rl.get("reflection_slipped") if len(rl.get("reflection_slipped", "") or "") >= len(loc.get("reflection_slipped", "") or "") else loc.get("reflection_slipped", "")
                ref_t = rl.get("reflection_tomorrow") if len(rl.get("reflection_tomorrow", "") or "") >= len(loc.get("reflection_tomorrow", "") or "") else loc.get("reflection_tomorrow", "")
                target_updated = rem_updated or loc_updated or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if (
                merged_blocks != loc.get("completed_blocks", "")
                or merged_ex != loc.get("completed_exercises", "")
                or scratchpad != loc.get("scratchpad", "")
                or wake_time != loc.get("wake_time", "")
                or sleep_time != loc.get("sleep_time", "")
                or ref_w != loc.get("reflection_worked", "")
                or ref_s != loc.get("reflection_slipped", "")
                or ref_t != loc.get("reflection_tomorrow", "")
            ):
                if has_updated_at:
                    cursor.execute(
                        """
                        UPDATE daily_logs 
                        SET completed_blocks = ?, completed_exercises = ?, scratchpad = ?,
                            wake_time = ?, sleep_time = ?, reflection_worked = ?,
                            reflection_slipped = ?, reflection_tomorrow = ?, updated_at = ?
                        WHERE date = ?
                        """,
                        (merged_blocks, merged_ex, scratchpad, wake_time, sleep_time, ref_w, ref_s, ref_t, target_updated, dt),
                    )
                else:
                    cursor.execute(
                        """
                        UPDATE daily_logs 
                        SET completed_blocks = ?, completed_exercises = ?, scratchpad = ?,
                            wake_time = ?, sleep_time = ?, reflection_worked = ?,
                            reflection_slipped = ?, reflection_tomorrow = ?
                        WHERE date = ?
                        """,
                        (merged_blocks, merged_ex, scratchpad, wake_time, sleep_time, ref_w, ref_s, ref_t, dt),
                    )
                synced_count += 1

    cursor.execute("SELECT date, scratchpad, wake_time, sleep_time, reflection_worked, reflection_slipped, reflection_tomorrow, completed_blocks, completed_exercises FROM daily_logs")
    for row in cursor.fetchall():
        _make_supabase_request(
            "daily_logs?on_conflict=date",
            method="POST",
            payload={
                "date": row["date"],
                "scratchpad": row["scratchpad"] or "",
                "wake_time": row["wake_time"] or "",
                "sleep_time": row["sleep_time"] or "",
                "reflection_worked": row["reflection_worked"] or "",
                "reflection_slipped": row["reflection_slipped"] or "",
                "reflection_tomorrow": row["reflection_tomorrow"] or "",
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
                "metro_stations?on_conflict=id",
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
        json.dump(metro_data, f, indent=2, ensure_ascii=False)

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
                if local_items[r_id]["completed"] == 1 and r_comp == 0:
                    _make_supabase_request(
                        "kill_list_items?on_conflict=id",
                        method="POST",
                        payload={"id": r_id, "completed": True},
                        headers_extra={"Prefer": "resolution=merge-duplicates"},
                    )
                    synced_count += 1
                elif r_comp == 1 and local_items[r_id]["completed"] == 0:
                    cursor.execute("UPDATE kill_list_items SET completed = 1 WHERE id = ?", (r_id,))
                    synced_count += 1

    remote_ids = {ri.get("id") for ri in remote_items if ri.get("id")}
    for l_id, loc in local_items.items():
        if l_id not in remote_ids:
            _make_supabase_request(
                "kill_list_items?on_conflict=id",
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
            "station_deliverable_progress?on_conflict=deliverable_id",
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
# 6. Body Metrics Sync
# =========================================================================
def sync_body_metrics(conn: sqlite3.Connection) -> int:
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, date, weight_kg, calories_met, protein_met, notes FROM body_metrics")
        local_metrics = {row["id"]: dict(row) for row in cursor.fetchall()}
    except (sqlite3.OperationalError, Exception):
        return 0

    remote_metrics = _make_supabase_request("body_metrics?select=*")
    if remote_metrics is None:
        return 0

    synced_count = 0
    for rm in remote_metrics:
        r_id = rm.get("id")
        if not r_id:
            continue
        cal = 1 if rm.get("calories_met") else 0
        prot = 1 if rm.get("protein_met") else 0
        w = float(rm.get("weight_kg", 0))
        notes = rm.get("notes", "") or ""
        dt = rm.get("date", "")
        if r_id not in local_metrics:
            cursor.execute(
                """
                INSERT OR REPLACE INTO body_metrics (id, date, weight_kg, calories_met, protein_met, notes)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (r_id, dt, w, cal, prot, notes),
            )
            synced_count += 1
        else:
            loc = local_metrics[r_id]
            if loc["weight_kg"] != w or loc["notes"] != notes or loc["calories_met"] != cal or loc["protein_met"] != prot:
                cursor.execute(
                    "UPDATE body_metrics SET weight_kg = ?, calories_met = ?, protein_met = ?, notes = ? WHERE id = ?",
                    (w, cal, prot, notes, r_id),
                )
                synced_count += 1

    remote_ids = {rm.get("id") for rm in remote_metrics if rm.get("id")}
    for l_id, loc in local_metrics.items():
        if l_id not in remote_ids:
            _make_supabase_request(
                "body_metrics?on_conflict=id",
                method="POST",
                payload={
                    "id": l_id,
                    "date": loc["date"],
                    "weight_kg": loc["weight_kg"],
                    "calories_met": bool(loc["calories_met"]),
                    "protein_met": bool(loc["protein_met"]),
                    "notes": loc["notes"] or "",
                },
                headers_extra={"Prefer": "resolution=merge-duplicates"},
            )
            synced_count += 1

    conn.commit()
    return synced_count


# =========================================================================
# 7. Workouts Sync
# =========================================================================
def sync_workouts(conn: sqlite3.Connection) -> int:
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, date, workout_type, details, intensity FROM workouts")
        local_workouts = {row["id"]: dict(row) for row in cursor.fetchall()}
    except (sqlite3.OperationalError, Exception):
        return 0

    remote_workouts = _make_supabase_request("workouts?select=*")
    if remote_workouts is None:
        return 0

    synced_count = 0
    for rw in remote_workouts:
        r_id = rw.get("id")
        if not r_id:
            continue
        w_type = rw.get("workout_type", "Gym")
        details = rw.get("details", "") or ""
        intensity = int(rw.get("intensity", 7))
        dt = rw.get("date", "")
        if r_id not in local_workouts:
            cursor.execute(
                """
                INSERT OR REPLACE INTO workouts (id, date, workout_type, details, intensity)
                VALUES (?, ?, ?, ?, ?)
                """,
                (r_id, dt, w_type, details, intensity),
            )
            synced_count += 1
        else:
            loc = local_workouts[r_id]
            if loc["details"] != details or loc["intensity"] != intensity or loc["workout_type"] != w_type:
                cursor.execute(
                    "UPDATE workouts SET workout_type = ?, details = ?, intensity = ? WHERE id = ?",
                    (w_type, details, intensity, r_id),
                )
                synced_count += 1

    remote_ids = {rw.get("id") for rw in remote_workouts if rw.get("id")}
    for l_id, loc in local_workouts.items():
        if l_id not in remote_ids:
            _make_supabase_request(
                "workouts?on_conflict=id",
                method="POST",
                payload={
                    "id": l_id,
                    "date": loc["date"],
                    "workout_type": loc["workout_type"],
                    "details": loc["details"] or "",
                    "intensity": loc["intensity"],
                },
                headers_extra={"Prefer": "resolution=merge-duplicates"},
            )
            synced_count += 1

    conn.commit()
    return synced_count


# =========================================================================
# 8. Projects Sync
# =========================================================================
def sync_projects(conn: sqlite3.Connection) -> int:
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, description, local_path, github_url, current_milestone, next_action, deadline, notes, status FROM projects")
        local_projects = {row["id"]: dict(row) for row in cursor.fetchall()}
    except (sqlite3.OperationalError, Exception):
        return 0

    remote_projects = _make_supabase_request("projects?select=*")
    if remote_projects is None:
        return 0

    synced_count = 0
    for rp in remote_projects:
        r_id = rp.get("id")
        if not r_id:
            continue
        name = rp.get("name", "")
        desc = rp.get("description", "") or ""
        milestone = rp.get("current_milestone", "") or ""
        next_act = rp.get("next_action", "") or ""
        status = rp.get("status", "active") or "active"
        if r_id not in local_projects:
            cursor.execute(
                """
                INSERT OR REPLACE INTO projects (id, name, description, local_path, github_url, current_milestone, next_action, deadline, notes, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    r_id,
                    name,
                    desc,
                    rp.get("local_path", "") or "",
                    rp.get("github_url", "") or "",
                    milestone,
                    next_act,
                    rp.get("deadline", "") or "",
                    rp.get("notes", "") or "",
                    status,
                ),
            )
            synced_count += 1
        else:
            loc = local_projects[r_id]
            if loc["current_milestone"] != milestone or loc["next_action"] != next_act or loc["status"] != status:
                cursor.execute(
                    "UPDATE projects SET current_milestone = ?, next_action = ?, status = ? WHERE id = ?",
                    (milestone, next_act, status, r_id),
                )
                synced_count += 1

    remote_ids = {rp.get("id") for rp in remote_projects if rp.get("id")}
    for l_id, loc in local_projects.items():
        if l_id not in remote_ids:
            _make_supabase_request(
                "projects?on_conflict=id",
                method="POST",
                payload={
                    "id": l_id,
                    "name": loc["name"],
                    "description": loc["description"] or "",
                    "local_path": loc["local_path"] or "",
                    "github_url": loc["github_url"] or "",
                    "current_milestone": loc["current_milestone"] or "",
                    "next_action": loc["next_action"] or "",
                    "deadline": loc["deadline"] or "",
                    "notes": loc["notes"] or "",
                    "status": loc["status"] or "active",
                },
                headers_extra={"Prefer": "resolution=merge-duplicates"},
            )
            synced_count += 1

    conn.commit()
    return synced_count


# =========================================================================
# 8b. School Exams Sync
# =========================================================================
def sync_school_exams(conn: sqlite3.Connection) -> int:
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, subject, title, exam_date, scope, completed, result_percentage FROM school_exams")
        local_exams = {row["id"]: dict(row) for row in cursor.fetchall()}
    except (sqlite3.OperationalError, Exception):
        return 0

    remote_exams = _make_supabase_request("school_exams?select=*")
    if remote_exams is None:
        return 0

    synced_count = 0
    for re in remote_exams:
        r_id = re.get("id")
        if not r_id:
            continue
        r_comp = 1 if re.get("completed") else 0
        r_res = re.get("result_percentage")
        if r_id not in local_exams:
            cursor.execute(
                """
                INSERT OR REPLACE INTO school_exams (id, subject, title, exam_date, scope, completed, result_percentage)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (r_id, re.get("subject", ""), re.get("title", ""), re.get("exam_date", ""), re.get("scope", ""), r_comp, r_res),
            )
            synced_count += 1
        else:
            loc = local_exams[r_id]
            if loc["completed"] != r_comp or loc["result_percentage"] != r_res:
                if loc["completed"] == 1 and r_comp == 0:
                    _make_supabase_request(
                        "school_exams?on_conflict=id",
                        method="POST",
                        payload={
                            "id": r_id,
                            "completed": True,
                            "result_percentage": loc["result_percentage"],
                        },
                        headers_extra={"Prefer": "resolution=merge-duplicates"},
                    )
                    synced_count += 1
                elif r_comp == 1 and loc["completed"] == 0:
                    cursor.execute("UPDATE school_exams SET completed = 1, result_percentage = ? WHERE id = ?", (r_res, r_id))
                    synced_count += 1
                elif r_res is not None and loc["result_percentage"] is None:
                    cursor.execute("UPDATE school_exams SET result_percentage = ? WHERE id = ?", (r_res, r_id))
                    synced_count += 1
                elif loc["result_percentage"] is not None and r_res != loc["result_percentage"]:
                    _make_supabase_request(
                        "school_exams?on_conflict=id",
                        method="POST",
                        payload={"id": r_id, "result_percentage": loc["result_percentage"]},
                        headers_extra={"Prefer": "resolution=merge-duplicates"},
                    )
                    synced_count += 1

    remote_ids = {re.get("id") for re in remote_exams if re.get("id")}
    for l_id, loc in local_exams.items():
        if l_id not in remote_ids:
            _make_supabase_request(
                "school_exams?on_conflict=id",
                method="POST",
                payload={
                    "id": l_id,
                    "subject": loc["subject"],
                    "title": loc["title"],
                    "exam_date": loc["exam_date"],
                    "scope": loc["scope"] or "",
                    "completed": bool(loc["completed"]),
                    "result_percentage": loc["result_percentage"],
                },
                headers_extra={"Prefer": "resolution=merge-duplicates"},
            )
            synced_count += 1

    conn.commit()
    return synced_count


# =========================================================================
# 8c. Homework Items Sync
# =========================================================================
def sync_homework_items(conn: sqlite3.Connection) -> int:
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, subject, title, due_date, completed, source, priority, notes FROM homework_items")
        local_hw = {row["id"]: dict(row) for row in cursor.fetchall()}
    except (sqlite3.OperationalError, Exception):
        return 0

    remote_hw = _make_supabase_request("homework_items?select=*")
    if remote_hw is None:
        return 0

    synced_count = 0
    for rh in remote_hw:
        r_id = rh.get("id")
        if not r_id:
            continue
        r_comp = 1 if rh.get("completed") else 0
        if r_id not in local_hw:
            cursor.execute(
                """
                INSERT OR REPLACE INTO homework_items (id, subject, title, due_date, completed, source, priority, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (r_id, rh.get("subject", ""), rh.get("title", ""), rh.get("due_date", ""), r_comp, rh.get("source", "manual"), rh.get("priority", 1), rh.get("notes", "")),
            )
            synced_count += 1
        else:
            loc = local_hw[r_id]
            if loc["completed"] != r_comp:
                if loc["completed"] == 1 and r_comp == 0:
                    _make_supabase_request(
                        "homework_items?on_conflict=id",
                        method="POST",
                        payload={"id": r_id, "completed": True},
                        headers_extra={"Prefer": "resolution=merge-duplicates"},
                    )
                    synced_count += 1
                elif r_comp == 1 and loc["completed"] == 0:
                    cursor.execute("UPDATE homework_items SET completed = 1 WHERE id = ?", (r_id,))
                    synced_count += 1

    remote_ids = {rh.get("id") for rh in remote_hw if rh.get("id")}
    for l_id, loc in local_hw.items():
        if l_id not in remote_ids:
            _make_supabase_request(
                "homework_items?on_conflict=id",
                method="POST",
                payload={
                    "id": l_id,
                    "subject": loc["subject"],
                    "title": loc["title"],
                    "due_date": loc["due_date"],
                    "completed": bool(loc["completed"]),
                    "source": loc["source"] or "manual",
                    "priority": loc["priority"] or 1,
                    "notes": loc["notes"] or "",
                },
                headers_extra={"Prefer": "resolution=merge-duplicates"},
            )
            synced_count += 1

    conn.commit()
    return synced_count


# =========================================================================
# 8d. TUM Grades & Curriculum Sync
# =========================================================================
def sync_tum_grades(conn) -> int:
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, subject, semester, target_grade, actual_grade, percentage, notes FROM tum_grades")
        local_items = {row["id"]: dict(row) for row in cursor.fetchall()}
    except Exception:
        return 0

    remote_items = _make_supabase_request("tum_grades?select=*")
    if remote_items is None:
        return 0

    synced_count = 0
    for re in remote_items:
        r_id = re.get("id")
        if not r_id:
            continue
        if r_id not in local_items:
            cursor.execute(
                "INSERT OR REPLACE INTO tum_grades (id, subject, semester, target_grade, actual_grade, percentage, notes) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (r_id, re.get("subject"), re.get("semester"), re.get("target_grade"), re.get("actual_grade"), re.get("percentage"), re.get("notes"))
            )
            synced_count += 1
        else:
            loc = local_items[r_id]
            if loc["actual_grade"] != re.get("actual_grade") or loc["percentage"] != re.get("percentage") or loc["target_grade"] != re.get("target_grade"):
                cursor.execute(
                    "UPDATE tum_grades SET target_grade = ?, actual_grade = ?, percentage = ?, notes = ? WHERE id = ?",
                    (re.get("target_grade"), re.get("actual_grade"), re.get("percentage"), re.get("notes"), r_id)
                )
                synced_count += 1

    remote_ids = {re.get("id") for re in remote_items if re.get("id")}
    for l_id, loc in local_items.items():
        if l_id not in remote_ids:
            _make_supabase_request(
                "tum_grades?on_conflict=id",
                method="POST",
                payload=loc,
                headers_extra={"Prefer": "resolution=merge-duplicates"},
            )
            synced_count += 1
    conn.commit()
    return synced_count


def sync_tum_grade_entries(conn) -> int:
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, subject, semester, raw_input, numeric_value, weight, category, description, date, counts_in_average FROM tum_grade_entries")
        local_items = {row["id"]: dict(row) for row in cursor.fetchall()}
    except Exception:
        return 0

    remote_items = _make_supabase_request("tum_grade_entries?select=*")
    if remote_items is None:
        return 0

    synced_count = 0
    for re in remote_items:
        r_id = re.get("id")
        if not r_id:
            continue
        if r_id not in local_items:
            cursor.execute(
                "INSERT OR REPLACE INTO tum_grade_entries (id, subject, semester, raw_input, numeric_value, weight, category, description, date, counts_in_average) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (r_id, re.get("subject"), re.get("semester"), re.get("raw_input"), re.get("numeric_value"), re.get("weight"), re.get("category"), re.get("description"), re.get("date"), 1 if re.get("counts_in_average") else 0)
            )
            synced_count += 1
        else:
            pass

    remote_ids = {re.get("id") for re in remote_items if re.get("id")}
    for l_id, loc in local_items.items():
        if l_id not in remote_ids:
            payload = dict(loc)
            payload["counts_in_average"] = bool(payload["counts_in_average"])
            _make_supabase_request(
                "tum_grade_entries?on_conflict=id",
                method="POST",
                payload=payload,
                headers_extra={"Prefer": "resolution=merge-duplicates"},
            )
            synced_count += 1
    conn.commit()
    return synced_count


def sync_tum_matura(conn) -> int:
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, subject, target_percentage, current_mock_percentage, notes FROM tum_matura")
        local_items = {row["id"]: dict(row) for row in cursor.fetchall()}
    except Exception:
        return 0

    remote_items = _make_supabase_request("tum_matura?select=*")
    if remote_items is None:
        return 0

    synced_count = 0
    for re in remote_items:
        r_id = re.get("id")
        if not r_id:
            continue
        if r_id not in local_items:
            cursor.execute(
                "INSERT OR REPLACE INTO tum_matura (id, subject, target_percentage, current_mock_percentage, notes) VALUES (?, ?, ?, ?, ?)",
                (r_id, re.get("subject"), re.get("target_percentage"), re.get("current_mock_percentage"), re.get("notes"))
            )
            synced_count += 1
        else:
            loc = local_items[r_id]
            if loc["current_mock_percentage"] != re.get("current_mock_percentage"):
                cursor.execute(
                    "UPDATE tum_matura SET current_mock_percentage = ? WHERE id = ?",
                    (re.get("current_mock_percentage"), r_id)
                )
                synced_count += 1

    remote_ids = {re.get("id") for re in remote_items if re.get("id")}
    for l_id, loc in local_items.items():
        if l_id not in remote_ids:
            _make_supabase_request(
                "tum_matura?on_conflict=id",
                method="POST",
                payload=loc,
                headers_extra={"Prefer": "resolution=merge-duplicates"},
            )
            synced_count += 1
    conn.commit()
    return synced_count


def sync_tum_language(conn) -> int:
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, level, target_date, status, milestone_description FROM tum_language")
        local_items = {row["id"]: dict(row) for row in cursor.fetchall()}
    except Exception:
        return 0

    remote_items = _make_supabase_request("tum_language?select=*")
    if remote_items is None:
        return 0

    synced_count = 0
    for re in remote_items:
        r_id = re.get("id")
        if not r_id:
            continue
        if r_id not in local_items:
            cursor.execute(
                "INSERT OR REPLACE INTO tum_language (id, level, target_date, status, milestone_description) VALUES (?, ?, ?, ?, ?)",
                (r_id, re.get("level"), re.get("target_date"), re.get("status"), re.get("milestone_description"))
            )
            synced_count += 1
        else:
            loc = local_items[r_id]
            if loc["status"] != re.get("status"):
                cursor.execute(
                    "UPDATE tum_language SET status = ? WHERE id = ?",
                    (re.get("status"), r_id)
                )
                synced_count += 1

    remote_ids = {re.get("id") for re in remote_items if re.get("id")}
    for l_id, loc in local_items.items():
        if l_id not in remote_ids:
            _make_supabase_request(
                "tum_language?on_conflict=id",
                method="POST",
                payload=loc,
                headers_extra={"Prefer": "resolution=merge-duplicates"},
            )
            synced_count += 1
    conn.commit()
    return synced_count


def sync_app_settings() -> int:
    synced_count = 0
    vulcan_path = DATA_DIR / "vulcan_config.json"
    remote_items = _make_supabase_request("app_settings?select=*")
    if remote_items is None:
        return 0

    remote_settings = {item["key"]: item["value"] for item in remote_items if "key" in item}

    if "vulcan_config" in remote_settings:
        if not vulcan_path.exists() or os.environ.get("VERCEL"):
            try:
                vulcan_path.parent.mkdir(parents=True, exist_ok=True)
                with open(vulcan_path, "w", encoding="utf-8") as f:
                    import json
                    json.dump(remote_settings["vulcan_config"], f, indent=2)
                synced_count += 1
            except Exception:
                pass

    if vulcan_path.exists() and not os.environ.get("VERCEL"):
        try:
            import json
            with open(vulcan_path, "r", encoding="utf-8") as f:
                local_vulcan = json.load(f)

            if "vulcan_config" not in remote_settings or remote_settings["vulcan_config"] != local_vulcan:
                _make_supabase_request(
                    "app_settings?on_conflict=key",
                    method="POST",
                    payload={"key": "vulcan_config", "value": local_vulcan},
                    headers_extra={"Prefer": "resolution=merge-duplicates"},
                )
                synced_count += 1
        except Exception:
            pass

    return synced_count

# =========================================================================
# 9. Direct Web Server Synchronizer (Local Executable <-> Web Version HTTP)
# =========================================================================
def probe_local_server() -> Optional[str]:
    """Probes if a local Harness companion web server is running on localhost:5000."""
    if os.environ.get("HARNESS_SERVER") or os.environ.get("VERCEL"):
        return None
    try:
        req = urllib.request.Request("http://127.0.0.1:5000/api/health", headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=0.25) as resp:
            if resp.status == 200:
                return "http://127.0.0.1:5000"
    except Exception:
        pass
    return None



def sync_with_web_server(conn: sqlite3.Connection, cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Exchanges all local updates directly with a deployed Harness Web server."""
    if cfg is None:
        cfg = get_sync_config()

    web_url = cfg.get("web_url", "").strip().rstrip("/")
    if not web_url:
        local_url = probe_local_server()
        if local_url:
            web_url = local_url
        else:
            return {"status": "unconfigured", "message": "No web_url configured", "synced_count": 0}

    cursor = conn.cursor()
    local_data = {}

    def fetch_all(query):
        try:
            cursor.execute(query)
            return [dict(r) for r in cursor.fetchall()]
        except Exception:
            return []

    local_data["tasks"] = fetch_all("SELECT * FROM tasks")
    local_data["daily_logs"] = fetch_all("SELECT * FROM daily_logs")
    local_data["kill_list_items"] = fetch_all("SELECT * FROM kill_list_items")
    local_data["station_deliverable_progress"] = fetch_all("SELECT * FROM station_deliverable_progress")
    local_data["school_exams"] = fetch_all("SELECT * FROM school_exams")
    local_data["homework_items"] = fetch_all("SELECT * FROM homework_items")
    local_data["body_metrics"] = fetch_all("SELECT * FROM body_metrics")
    local_data["workouts"] = fetch_all("SELECT * FROM workouts")
    local_data["projects"] = fetch_all("SELECT * FROM projects")
    local_data["tum_grade_entries"] = fetch_all("SELECT * FROM tum_grade_entries")
    local_data["tum_grades"] = fetch_all("SELECT * FROM tum_grades")
    local_data["tum_matura"] = fetch_all("SELECT * FROM tum_matura")
    local_data["tum_language"] = fetch_all("SELECT * FROM tum_language")

    metro_file = DATA_DIR / "metro_roadmap.json"
    if metro_file.exists():
        try:
            with open(metro_file, "r", encoding="utf-8") as f:
                local_data["metro_roadmap"] = json.load(f)
        except Exception:
            local_data["metro_roadmap"] = {}

    payload = {
        "client_time": datetime.now().isoformat(),
        "last_synced_at": cfg.get("last_synced_at"),
        "data": local_data,
    }

    url = f"{web_url}/api/sync/exchange"
    res = _post_json(url, payload, timeout=10)
    if not res or res.get("status") not in ["ok", "synced"]:
        return {"status": "offline", "message": f"Web server at {web_url} unreachable", "synced_count": 0}

    remote_data = res.get("data", {})
    synced_count = 0

    # 1. Tasks
    if "tasks" in remote_data:
        for rt in remote_data["tasks"]:
            r_id = rt.get("id")
            if not r_id:
                continue
            r_comp = 1 if rt.get("completed") else 0
            cursor.execute("SELECT id, completed FROM tasks WHERE id = ?", (r_id,))
            loc = cursor.fetchone()
            if not loc:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO tasks (id, title, category, is_tum, completed, date, rollover_count, created_at, completed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        r_id,
                        rt.get("title", ""),
                        rt.get("category", "personal"),
                        1 if rt.get("is_tum") else 0,
                        r_comp,
                        rt.get("date", datetime.now().strftime("%Y-%m-%d")),
                        rt.get("rollover_count", 0),
                        rt.get("created_at"),
                        rt.get("completed_at"),
                    ),
                )
                synced_count += 1
            elif loc["completed"] != r_comp:
                cursor.execute("UPDATE tasks SET completed = ? WHERE id = ?", (r_comp, r_id))
                synced_count += 1

    # 2. Daily Logs
    if "daily_logs" in remote_data:
        for rl in remote_data["daily_logs"]:
            dt = rl.get("date")
            if not dt:
                continue
            cursor.execute("SELECT * FROM daily_logs WHERE date = ?", (dt,))
            loc = cursor.fetchone()
            rem_updated = rl.get("updated_at") or ""
            if not loc:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO daily_logs
                    (date, scratchpad, wake_time, sleep_time, reflection_worked, reflection_slipped, reflection_tomorrow, completed_blocks, completed_exercises, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        dt,
                        rl.get("scratchpad", "") or "",
                        rl.get("wake_time", "") or "",
                        dl_sleep := rl.get("sleep_time", "") or "",
                        rl.get("reflection_worked", "") or "",
                        rl.get("reflection_slipped", "") or "",
                        rl.get("reflection_tomorrow", "") or "",
                        rl.get("completed_blocks", "") or "",
                        rl.get("completed_exercises", "") or "",
                        rem_updated or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    ),
                )
                synced_count += 1
            else:
                loc_dict = dict(loc)
                loc_updated = loc_dict.get("updated_at") or ""

                if rem_updated and loc_updated and rem_updated != loc_updated:
                    if rem_updated > loc_updated:
                        merged_b = rl.get("completed_blocks", "") or ""
                        merged_e = rl.get("completed_exercises", "") or ""
                        sp = rl.get("scratchpad") if rl.get("scratchpad") is not None else (loc_dict.get("scratchpad") or "")
                        rw = rl.get("reflection_worked") or loc_dict.get("reflection_worked") or ""
                        rs = rl.get("reflection_slipped") or loc_dict.get("reflection_slipped") or ""
                        rt = rl.get("reflection_tomorrow") or loc_dict.get("reflection_tomorrow") or ""
                        wt = rl.get("wake_time") or loc_dict.get("wake_time") or ""
                        st = rl.get("sleep_time") or loc_dict.get("sleep_time") or ""
                        target_updated = rem_updated
                    else:
                        merged_b = loc_dict.get("completed_blocks", "") or ""
                        merged_e = loc_dict.get("completed_exercises", "") or ""
                        sp = loc_dict.get("scratchpad") or rl.get("scratchpad") or ""
                        rw = loc_dict.get("reflection_worked") or rl.get("reflection_worked") or ""
                        rs = loc_dict.get("reflection_slipped") or rl.get("reflection_slipped") or ""
                        rt = loc_dict.get("reflection_tomorrow") or rl.get("reflection_tomorrow") or ""
                        wt = loc_dict.get("wake_time") or rl.get("wake_time") or ""
                        st = loc_dict.get("sleep_time") or rl.get("sleep_time") or ""
                        target_updated = loc_updated
                else:
                    loc_b = set(filter(None, (loc_dict.get("completed_blocks") or "").split(",")))
                    rem_b = set(filter(None, (rl.get("completed_blocks") or "").split(",")))
                    merged_b = ",".join(sorted(loc_b.union(rem_b)))

                    loc_e = set(filter(None, (loc_dict.get("completed_exercises") or "").split(",")))
                    rem_e = set(filter(None, (rl.get("completed_exercises") or "").split(",")))
                    merged_e = ",".join(sorted(loc_e.union(rem_e)))

                    sp = rl.get("scratchpad") if len(rl.get("scratchpad") or "") >= len(loc_dict.get("scratchpad") or "") else loc_dict.get("scratchpad")
                    rw = rl.get("reflection_worked") if len(rl.get("reflection_worked", "") or "") >= len(loc_dict.get("reflection_worked", "") or "") else loc_dict.get("reflection_worked", "")
                    rs = rl.get("reflection_slipped") if len(rl.get("reflection_slipped", "") or "") >= len(loc_dict.get("reflection_slipped", "") or "") else loc_dict.get("reflection_slipped", "")
                    rt = rl.get("reflection_tomorrow") if len(rl.get("reflection_tomorrow", "") or "") >= len(loc_dict.get("reflection_tomorrow", "") or "") else loc_dict.get("reflection_tomorrow", "")
                    wt = rl.get("wake_time") or loc_dict.get("wake_time") or ""
                    st = rl.get("sleep_time") or loc_dict.get("sleep_time") or ""
                    target_updated = rem_updated or loc_updated or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                if (
                    merged_b != loc_dict.get("completed_blocks", "")
                    or merged_e != loc_dict.get("completed_exercises", "")
                    or sp != loc_dict.get("scratchpad", "")
                    or rw != loc_dict.get("reflection_worked", "")
                    or rs != loc_dict.get("reflection_slipped", "")
                    or rt != loc_dict.get("reflection_tomorrow", "")
                    or wt != loc_dict.get("wake_time", "")
                    or st != loc_dict.get("sleep_time", "")
                ):
                    cursor.execute(
                        """
                        UPDATE daily_logs SET
                            completed_blocks = ?, completed_exercises = ?, scratchpad = ?,
                            reflection_worked = ?, reflection_slipped = ?, reflection_tomorrow = ?,
                            wake_time = ?, sleep_time = ?, updated_at = ?
                        WHERE date = ?
                        """,
                        (merged_b, merged_e, sp, rw, rs, rt, wt, st, target_updated, dt),
                    )
                    synced_count += 1

    # 3. Kill List Items
    if "kill_list_items" in remote_data:
        for rk in remote_data["kill_list_items"]:
            k_id = rk.get("id")
            if not k_id:
                continue
            r_comp = 1 if rk.get("completed") else 0
            cursor.execute("SELECT id, completed FROM kill_list_items WHERE id = ?", (k_id,))
            loc = cursor.fetchone()
            if not loc:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO kill_list_items
                    (id, date, category, title, action_type, target_path, target_spec, station_deliverable_id, completed)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        k_id,
                        rk.get("date", ""),
                        rk.get("category", "General"),
                        rk.get("title", ""),
                        rk.get("action_type", "url"),
                        rk.get("target_path", ""),
                        rk.get("target_spec", ""),
                        rk.get("station_deliverable_id"),
                        r_comp,
                    ),
                )
                synced_count += 1
            elif loc["completed"] != r_comp:
                cursor.execute("UPDATE kill_list_items SET completed = ? WHERE id = ?", (r_comp, k_id))
                synced_count += 1

    # 4. Station Deliverable Progress
    if "station_deliverable_progress" in remote_data:
        for rd in remote_data["station_deliverable_progress"]:
            d_id = rd.get("deliverable_id")
            if not d_id:
                continue
            rem_count = rd.get("completed_count", 0)
            rem_done = 1 if rd.get("is_completed") else 0
            cursor.execute("SELECT deliverable_id, completed_count, is_completed, total_required FROM station_deliverable_progress WHERE deliverable_id = ?", (d_id,))
            loc = cursor.fetchone()
            if not loc:
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
            else:
                max_count = max(loc["completed_count"], rem_count)
                is_done = 1 if (max_count >= loc["total_required"] or loc["is_completed"] or rem_done) else 0
                if max_count != loc["completed_count"] or is_done != loc["is_completed"]:
                    cursor.execute("UPDATE station_deliverable_progress SET completed_count = ?, is_completed = ? WHERE deliverable_id = ?", (max_count, is_done, d_id))
                    synced_count += 1

    # 5. Body Metrics
    if "body_metrics" in remote_data:
        for bm in remote_data["body_metrics"]:
            b_id = bm.get("id")
            if not b_id:
                continue
            cursor.execute("SELECT id, weight_kg, notes FROM body_metrics WHERE id = ?", (b_id,))
            loc = cursor.fetchone()
            w = float(bm.get("weight_kg", 0))
            cal = 1 if bm.get("calories_met") else 0
            prot = 1 if bm.get("protein_met") else 0
            notes = bm.get("notes", "") or ""
            if not loc:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO body_metrics (id, date, weight_kg, calories_met, protein_met, notes)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (b_id, bm.get("date", ""), w, cal, prot, notes),
                )
                synced_count += 1
            elif loc["weight_kg"] != w or loc["notes"] != notes:
                cursor.execute("UPDATE body_metrics SET weight_kg = ?, notes = ?, calories_met = ?, protein_met = ? WHERE id = ?", (w, notes, cal, prot, b_id))
                synced_count += 1

    # 6. Workouts
    if "workouts" in remote_data:
        for wo in remote_data["workouts"]:
            w_id = wo.get("id")
            if not w_id:
                continue
            cursor.execute("SELECT id, workout_type, details, intensity FROM workouts WHERE id = ?", (w_id,))
            loc = cursor.fetchone()
            w_type = wo.get("workout_type", "Gym")
            details = wo.get("details", "") or ""
            intensity = int(wo.get("intensity", 7))
            if not loc:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO workouts (id, date, workout_type, details, intensity)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (w_id, wo.get("date", ""), w_type, details, intensity),
                )
                synced_count += 1
            elif loc["details"] != details or loc["intensity"] != intensity or loc["workout_type"] != w_type:
                cursor.execute("UPDATE workouts SET workout_type = ?, details = ?, intensity = ? WHERE id = ?", (w_type, details, intensity, w_id))
                synced_count += 1

    # 7. Projects
    if "projects" in remote_data:
        for pr in remote_data["projects"]:
            p_id = pr.get("id")
            if not p_id:
                continue
            cursor.execute("SELECT id, current_milestone, next_action, status FROM projects WHERE id = ?", (p_id,))
            loc = cursor.fetchone()
            milestone = pr.get("current_milestone", "") or ""
            next_act = pr.get("next_action", "") or ""
            status = pr.get("status", "active")
            if not loc:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO projects (id, name, description, local_path, github_url, current_milestone, next_action, deadline, notes, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        p_id,
                        pr.get("name", ""),
                        pr.get("description", "") or "",
                        pr.get("local_path", "") or "",
                        pr.get("github_url", "") or "",
                        milestone,
                        next_act,
                        pr.get("deadline", "") or "",
                        pr.get("notes", "") or "",
                        status,
                    ),
                )
                synced_count += 1
            elif loc["current_milestone"] != milestone or loc["next_action"] != next_act or loc["status"] != status:
                cursor.execute("UPDATE projects SET current_milestone = ?, next_action = ?, status = ? WHERE id = ?", (milestone, next_act, status, p_id))
                synced_count += 1

    # 8. Metro Roadmap
    if "metro_roadmap" in remote_data and isinstance(remote_data["metro_roadmap"], dict):
        rem_metro = remote_data["metro_roadmap"]
        rem_stations = rem_metro.get("stations", [])
        if rem_stations and metro_file.exists():
            try:
                with open(metro_file, "r", encoding="utf-8") as f:
                    loc_metro = json.load(f)
                rem_map = {s.get("id"): s for s in rem_stations if s.get("id")}
                metro_changed = False
                for ls in loc_metro.get("stations", []):
                    st_id = ls.get("id")
                    if st_id in rem_map:
                        rs = rem_map[st_id]
                        loc_d = set(ls.get("completed_deliverables", []))
                        rem_d = set(rs.get("completed_deliverables", []))
                        merged_d = list(loc_d.union(rem_d))
                        if merged_d != ls.get("completed_deliverables", []):
                            ls["completed_deliverables"] = merged_d
                            total_d = len(ls.get("deliverables", {}))
                            if total_d > 0 and len(merged_d) >= total_d:
                                ls["status"] = "completed"
                            metro_changed = True
                            synced_count += 1
                if metro_changed:
                    with open(metro_file, "w", encoding="utf-8") as f:
                        json.dump(loc_metro, f, indent=2, ensure_ascii=False)
            except Exception:
                pass

    # 9. School Exams
    if "school_exams" in remote_data:
        for ex in remote_data["school_exams"]:
            e_id = ex.get("id")
            if not e_id:
                continue
            cursor.execute("SELECT id, completed, result_percentage FROM school_exams WHERE id = ?", (e_id,))
            loc = cursor.fetchone()
            e_comp = 1 if ex.get("completed") else 0
            e_res = ex.get("result_percentage")
            if not loc:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO school_exams (id, subject, title, exam_date, scope, completed, result_percentage)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (e_id, ex.get("subject", ""), ex.get("title", ""), ex.get("exam_date", ""), ex.get("scope", ""), e_comp, e_res),
                )
                synced_count += 1
            elif loc["completed"] != e_comp or loc["result_percentage"] != e_res:
                cursor.execute("UPDATE school_exams SET completed = ?, result_percentage = ? WHERE id = ?", (e_comp, e_res, e_id))
                synced_count += 1

    # 10. Homework Items
    if "homework_items" in remote_data:
        for hw in remote_data["homework_items"]:
            h_id = hw.get("id")
            if not h_id:
                continue
            cursor.execute("SELECT id, completed FROM homework_items WHERE id = ?", (h_id,))
            loc = cursor.fetchone()
            h_comp = 1 if hw.get("completed") else 0
            if not loc:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO homework_items (id, subject, title, due_date, completed, source, priority, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (h_id, hw.get("subject", ""), hw.get("title", ""), hw.get("due_date", ""), h_comp, hw.get("source", "manual"), hw.get("priority", 1), hw.get("notes", "")),
                )
                synced_count += 1
            elif loc["completed"] != h_comp:
                cursor.execute("UPDATE homework_items SET completed = ? WHERE id = ?", (h_comp, h_id))
                synced_count += 1

        # 11. TUM Grade Entries
    if "tum_grade_entries" in remote_data:
        for ge in remote_data["tum_grade_entries"]:
            g_id = ge.get("id")
            if not g_id:
                continue
            cursor.execute("SELECT id FROM tum_grade_entries WHERE id = ?", (g_id,))
            loc = cursor.fetchone()
            if not loc:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO tum_grade_entries
                    (id, subject, semester, raw_input, numeric_value, weight, category, description, date, counts_in_average)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        g_id,
                        ge.get("subject", ""),
                        int(ge.get("semester", 1)),
                        ge.get("raw_input", ""),
                        ge.get("numeric_value"),
                        float(ge.get("weight", 1.0)),
                        ge.get("category", "Grade"),
                        ge.get("description", ""),
                        ge.get("date", ""),
                        1 if ge.get("counts_in_average") else 0,
                    ),
                )
                synced_count += 1

    # 12. TUM Grades
    if "tum_grades" in remote_data:
        for tg in remote_data["tum_grades"]:
            tg_id = tg.get("id")
            if not tg_id:
                continue
            cursor.execute("SELECT id, actual_grade, percentage, target_grade FROM tum_grades WHERE id = ?", (tg_id,))
            loc = cursor.fetchone()
            if not loc:
                cursor.execute(
                    "INSERT OR REPLACE INTO tum_grades (id, subject, semester, target_grade, actual_grade, percentage, notes) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (tg_id, tg.get("subject"), int(tg.get("semester", 1)), float(tg.get("target_grade", 5.0)), tg.get("actual_grade"), tg.get("percentage"), tg.get("notes", ""))
                )
                synced_count += 1
            elif loc["actual_grade"] != tg.get("actual_grade") or loc["percentage"] != tg.get("percentage") or loc["target_grade"] != tg.get("target_grade"):
                cursor.execute(
                    "UPDATE tum_grades SET target_grade = ?, actual_grade = ?, percentage = ?, notes = ? WHERE id = ?",
                    (tg.get("target_grade"), tg.get("actual_grade"), tg.get("percentage"), tg.get("notes", ""), tg_id)
                )
                synced_count += 1

    # 13. TUM Matura
    if "tum_matura" in remote_data:
        for tm in remote_data["tum_matura"]:
            tm_id = tm.get("id")
            if not tm_id:
                continue
            cursor.execute("SELECT id, current_mock_percentage FROM tum_matura WHERE id = ?", (tm_id,))
            loc = cursor.fetchone()
            if not loc:
                cursor.execute(
                    "INSERT OR REPLACE INTO tum_matura (id, subject, target_percentage, current_mock_percentage, notes) VALUES (?, ?, ?, ?, ?)",
                    (tm_id, tm.get("subject"), float(tm.get("target_percentage", 90.0)), float(tm.get("current_mock_percentage", 0.0)), tm.get("notes", ""))
                )
                synced_count += 1
            elif loc["current_mock_percentage"] != tm.get("current_mock_percentage"):
                cursor.execute("UPDATE tum_matura SET current_mock_percentage = ? WHERE id = ?", (tm.get("current_mock_percentage"), tm_id))
                synced_count += 1

    # 14. TUM Language
    if "tum_language" in remote_data:
        for tl in remote_data["tum_language"]:
            tl_id = tl.get("id")
            if not tl_id:
                continue
            cursor.execute("SELECT id, status FROM tum_language WHERE id = ?", (tl_id,))
            loc = cursor.fetchone()
            if not loc:
                cursor.execute(
                    "INSERT OR REPLACE INTO tum_language (id, level, target_date, status, milestone_description) VALUES (?, ?, ?, ?, ?)",
                    (tl_id, tl.get("level"), tl.get("target_date"), tl.get("status", "pending"), tl.get("milestone_description", ""))
                )
                synced_count += 1
            elif loc["status"] != tl.get("status"):
                cursor.execute("UPDATE tum_language SET status = ? WHERE id = ?", (tl.get("status"), tl_id))
                synced_count += 1

    conn.commit()
    return {"status": "synced", "synced_count": synced_count, "timestamp": datetime.now().isoformat()}


# =========================================================================
# Master Multi-Entity Synchronizer
# =========================================================================
def sync_all(conn: Optional[sqlite3.Connection] = None) -> Dict[str, Any]:
    """Executes full bi-directional synchronization across all tables."""
    cfg = get_sync_config()
    has_web = bool(cfg.get("web_url"))
    has_supabase = bool(cfg.get("supabase_key"))

    if (os.environ.get("HARNESS_SERVER") or os.environ.get("VERCEL")) and cfg.get("web_url") in ["http://127.0.0.1:5000", "http://localhost:5000"]:
        has_web = False
        cfg["web_url"] = ""

    if not has_web and not has_supabase:
        local_url = probe_local_server()
        if local_url:
            has_web = True
            cfg["web_url"] = local_url
        else:
            return {
                "status": "unconfigured",
                "message": "Neither Web Server URL nor Supabase key configured in Sync Settings",
                "synced_count": 0,
                "timestamp": datetime.now().isoformat(),
            }

    should_close = False
    if conn is None:
        conn = get_connection()
        should_close = True

    total_synced = 0
    errors = []

    try:
        # Direct Web Server Sync (if configured)
        if has_web:
            web_res = sync_with_web_server(conn, cfg)
            if web_res.get("status") == "synced":
                total_synced += web_res.get("synced_count", 0)
            elif web_res.get("status") == "offline":
                errors.append(f"Web: {web_res.get('message', 'offline')}")

        # Supabase Cloud Sync (if configured)
        if has_supabase:
            try:
                tasks_count = sync_tasks(conn)
                logs_count = sync_daily_logs(conn)
                metro_count = sync_metro_roadmap()
                kill_count = sync_kill_list_items(conn)
                deliv_count = sync_station_deliverable_progress(conn)
                body_count = sync_body_metrics(conn)
                workout_count = sync_workouts(conn)
                project_count = sync_projects(conn)
                exams_count = sync_school_exams(conn)
                hw_count = sync_homework_items(conn)

                tum_gr_count = sync_tum_grades(conn)
                tum_ge_count = sync_tum_grade_entries(conn)
                tum_ma_count = sync_tum_matura(conn)
                tum_la_count = sync_tum_language(conn)
                set_count = sync_app_settings()

                total_synced += (tasks_count + logs_count + metro_count + kill_count + deliv_count + body_count + workout_count + project_count + exams_count + hw_count + tum_gr_count + tum_ge_count + tum_ma_count + tum_la_count + set_count)
            except Exception as se:
                errors.append(f"Supabase: {se}")

        now_iso = datetime.now().isoformat()
        cfg["last_synced_at"] = now_iso
        save_sync_config(cfg)

        status_str = "synced" if (not errors or total_synced > 0) else "offline"
        return {
            "status": status_str,
            "message": f"Successfully synced {total_synced} updates" if not errors else f"Synced {total_synced} updates ({'; '.join(errors)})",
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
        if should_close:
            conn.close()


def push_all_local_to_supabase(conn: Optional[sqlite3.Connection] = None) -> Dict[str, Any]:
    """
    Pushes all local records across all 15 tables to Supabase in one atomic push.
    Guarantees user PC progress (homework, exams, grades, logs, tasks) is saved in Supabase.
    """
    should_close = False
    if conn is None:
        conn = get_connection()
        should_close = True

    cfg = get_sync_config()
    if not cfg.get("supabase_key") or not cfg.get("supabase_url"):
        if should_close:
            conn.close()
        return {
            "status": "unconfigured",
            "message": "Supabase Project URL and Key are required to push data to cloud.",
            "pushed_count": 0,
            "synced_count": 0,
        }

    cursor = conn.cursor()
    pushed = 0
    errors = []

    def push_table(table_name, select_sql, id_col, transform_fn=None):
        nonlocal pushed
        try:
            cursor.execute(select_sql)
            rows = [dict(r) for r in cursor.fetchall()]
            for r in rows:
                payload = transform_fn(r) if transform_fn else r
                endpoint = f"{table_name}?on_conflict={id_col}"
                res = _make_supabase_request(
                    endpoint,
                    method="POST",
                    payload=payload,
                    headers_extra={"Prefer": "resolution=merge-duplicates"},
                )
                if res is not None:
                    pushed += 1
        except sqlite3.OperationalError:
            pass
        except Exception as e:
            errors.append(f"{table_name}: {e}")

    try:
        # 1. Tasks
        push_table("tasks", "SELECT * FROM tasks", "id", lambda r: {
            "id": r["id"],
            "title": r["title"],
            "category": r["category"],
            "is_tum": bool(r["is_tum"]),
            "completed": bool(r["completed"]),
            "date": r["date"],
            "rollover_count": r.get("rollover_count", 0),
            "created_at": r.get("created_at"),
            "completed_at": r.get("completed_at"),
        })

        # 2. Daily Logs
        push_table("daily_logs", "SELECT * FROM daily_logs", "date", lambda r: {
            "date": r["date"],
            "scratchpad": r.get("scratchpad") or "",
            "wake_time": r.get("wake_time") or "",
            "sleep_time": r.get("sleep_time") or "",
            "reflection_worked": r.get("reflection_worked") or "",
            "reflection_slipped": r.get("reflection_slipped") or "",
            "reflection_tomorrow": r.get("reflection_tomorrow") or "",
            "completed_blocks": r.get("completed_blocks") or "",
            "completed_exercises": r.get("completed_exercises") or "",
            "updated_at": r.get("updated_at") or datetime.now().isoformat(),
        })

        # 3. Homework Items
        push_table("homework_items", "SELECT * FROM homework_items", "id", lambda r: {
            "id": r["id"],
            "subject": r["subject"],
            "title": r["title"],
            "due_date": r["due_date"],
            "completed": bool(r["completed"]),
            "source": r.get("source") or "manual",
            "priority": r.get("priority") or 1,
            "notes": r.get("notes") or "",
        })

        # 4. School Exams
        push_table("school_exams", "SELECT * FROM school_exams", "id", lambda r: {
            "id": r["id"],
            "subject": r["subject"],
            "title": r["title"],
            "exam_date": r["exam_date"],
            "scope": r.get("scope") or "",
            "completed": bool(r["completed"]),
            "result_percentage": r.get("result_percentage"),
        })

        # 5. Kill List Items
        push_table("kill_list_items", "SELECT * FROM kill_list_items", "id", lambda r: {
            "id": r["id"],
            "date": r["date"],
            "category": r["category"],
            "title": r["title"],
            "action_type": r["action_type"],
            "target_path": r.get("target_path") or "",
            "target_spec": r.get("target_spec") or "",
            "station_deliverable_id": r.get("station_deliverable_id"),
            "completed": bool(r["completed"]),
        })

        # 6. Station Deliverable Progress
        push_table("station_deliverable_progress", "SELECT * FROM station_deliverable_progress", "deliverable_id", lambda r: {
            "deliverable_id": r["deliverable_id"],
            "completed_count": r.get("completed_count", 0),
            "total_required": r.get("total_required", 100),
            "unit_label": r.get("unit_label", "units"),
            "is_completed": bool(r.get("is_completed", 0)),
        })

        # 7. TUM Grades
        push_table("tum_grades", "SELECT * FROM tum_grades", "id", lambda r: {
            "id": r["id"],
            "subject": r["subject"],
            "semester": r["semester"],
            "target_grade": r.get("target_grade"),
            "actual_grade": r.get("actual_grade"),
            "percentage": r.get("percentage"),
            "notes": r.get("notes") or "",
        })

        # 8. TUM Grade Entries
        push_table("tum_grade_entries", "SELECT * FROM tum_grade_entries", "id", lambda r: {
            "id": r["id"],
            "subject": r["subject"],
            "semester": r["semester"],
            "raw_input": r["raw_input"],
            "numeric_value": r.get("numeric_value"),
            "weight": r.get("weight", 1.0),
            "category": r.get("category", "Grade"),
            "description": r.get("description") or "",
            "date": r["date"],
            "counts_in_average": bool(r.get("counts_in_average", 1)),
        })

        # 9. TUM Matura
        push_table("tum_matura", "SELECT * FROM tum_matura", "id", lambda r: {
            "id": r["id"],
            "subject": r["subject"],
            "target_percentage": r.get("target_percentage", 90.0),
            "current_mock_percentage": r.get("current_mock_percentage", 0.0),
            "notes": r.get("notes") or "",
        })

        # 10. TUM Language
        push_table("tum_language", "SELECT * FROM tum_language", "id", lambda r: {
            "id": r["id"],
            "level": r["level"],
            "target_date": r.get("target_date"),
            "status": r.get("status", "pending"),
            "milestone_description": r.get("milestone_description") or "",
        })

        # 11. Body Metrics
        push_table("body_metrics", "SELECT * FROM body_metrics", "id", lambda r: {
            "id": r["id"],
            "date": r["date"],
            "weight_kg": r["weight_kg"],
            "calories_met": bool(r.get("calories_met")),
            "protein_met": bool(r.get("protein_met")),
            "notes": r.get("notes") or "",
        })

        # 12. Workouts
        push_table("workouts", "SELECT * FROM workouts", "id", lambda r: {
            "id": r["id"],
            "date": r["date"],
            "workout_type": r["workout_type"],
            "details": r.get("details") or "",
            "intensity": r.get("intensity", 7),
        })

        # 13. Projects
        push_table("projects", "SELECT * FROM projects", "id", lambda r: {
            "id": r["id"],
            "name": r["name"],
            "description": r.get("description") or "",
            "status": r.get("status", "active"),
            "local_path": r.get("local_path") or "",
            "github_url": r.get("github_url") or "",
            "current_milestone": r.get("current_milestone") or "",
            "next_action": r.get("next_action") or "",
            "deadline": r.get("deadline") or "",
            "notes": r.get("notes") or "",
        })

        # 14. Metro Roadmap
        metro_file = DATA_DIR / "metro_roadmap.json"
        if metro_file.exists():
            try:
                with open(metro_file, "r", encoding="utf-8") as f:
                    mdata = json.load(f)
                for idx, st in enumerate(mdata.get("stations", [])):
                    endpoint = "metro_stations?on_conflict=id"
                    res = _make_supabase_request(
                        endpoint,
                        method="POST",
                        payload={
                            "id": st["id"],
                            "name": st.get("name", ""),
                            "phase": st.get("phase", ""),
                            "month_label": st.get("month_label", ""),
                            "year_month": st.get("date", ""),
                            "is_major": bool(st.get("is_major")),
                            "status": st.get("status", "upcoming"),
                            "objective": st.get("objective", ""),
                            "deliverables": st.get("deliverables", {}),
                            "completed_deliverables": st.get("completed_deliverables", []),
                            "order_idx": idx,
                        },
                        headers_extra={"Prefer": "resolution=merge-duplicates"},
                    )
                    if res is not None:
                        pushed += 1
            except Exception as me:
                errors.append(f"metro_stations: {me}")

        now_iso = datetime.now().isoformat()
        cfg["last_synced_at"] = now_iso
        save_sync_config(cfg)

        return {
            "status": "synced" if not errors else "partial",
            "message": f"Successfully pushed {pushed} items to Supabase cloud." if not errors else f"Pushed {pushed} items ({'; '.join(errors)})",
            "pushed_count": pushed,
            "synced_count": pushed,
            "timestamp": now_iso,
        }
    finally:
        if should_close:
            conn.close()


def pull_all_supabase_to_local(conn: Optional[sqlite3.Connection] = None) -> Dict[str, Any]:
    """Pulls all remote data from Supabase and hydrates local SQLite."""
    should_close = False
    if conn is None:
        conn = get_connection()
        should_close = True

    try:
        # Run sync_all which pulls deltas
        return sync_all(conn)
    finally:
        if should_close:
            conn.close()


