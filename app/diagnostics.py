"""Centralized structured logging and runtime diagnostics for Harness Executive OS."""

import json
import logging
import sqlite3
import threading
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional

logger = logging.getLogger("harness")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s %(name)s: %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

_ERROR_LOCK = threading.Lock()
_RECENT_ERRORS: Deque[Dict[str, Any]] = deque(maxlen=40)
_SYNC_STATE: Dict[str, Any] = {
    "last_background_sync_at": None,
    "last_background_sync_ok": None,
    "last_background_sync_error": "",
}


def record_error(component: str, message: str, exc: Optional[BaseException] = None) -> None:
    """Logs a warning/error and records it into the bounded diagnostics ring buffer."""
    detail = f"{message}: {exc}" if exc is not None else message
    logger.warning("[%s] %s", component, detail)
    with _ERROR_LOCK:
        _RECENT_ERRORS.appendleft(
            {
                "timestamp": datetime.now().isoformat(),
                "component": component,
                "message": str(message),
                "error": str(exc) if exc is not None else "",
            }
        )


def record_sync_result(ok: bool, error: str = "") -> None:
    """Tracks the outcome of the latest background sync run."""
    with _ERROR_LOCK:
        _SYNC_STATE["last_background_sync_at"] = datetime.now().isoformat()
        _SYNC_STATE["last_background_sync_ok"] = bool(ok)
        _SYNC_STATE["last_background_sync_error"] = str(error or "")


def get_recent_errors(limit: int = 20) -> List[Dict[str, Any]]:
    with _ERROR_LOCK:
        return list(_RECENT_ERRORS)[:limit]


def get_system_diagnostics(conn: Optional[sqlite3.Connection] = None) -> Dict[str, Any]:
    """Returns a complete operational health snapshot across DB, timetable, sync, and engine."""
    from app.db import DATA_DIR, get_connection, get_db_path
    from engine import workload_governor

    close_conn = False
    db_ok = False
    table_counts: Dict[str, int] = {}
    material_deficit_open = 0

    try:
        if conn is None:
            conn = get_connection()
            close_conn = True
        cur = conn.cursor()
        integrity = cur.execute("PRAGMA quick_check;").fetchone()
        db_ok = bool(integrity and str(integrity[0]).lower() == "ok")
        for tbl in (
            "tasks",
            "daily_logs",
            "school_exams",
            "homework_items",
            "tum_grade_entries",
            "kill_list_items",
            "station_deliverable_progress",
            "material_deficit",
        ):
            try:
                row = cur.execute(f'SELECT COUNT(*) FROM "{tbl}"').fetchone()
                table_counts[tbl] = int(row[0]) if row else 0
            except Exception:
                table_counts[tbl] = -1
        try:
            row = cur.execute("SELECT COUNT(*) FROM material_deficit WHERE status != 'resolved'").fetchone()
            material_deficit_open = int(row[0]) if row else 0
        except Exception:
            material_deficit_open = 0
    except Exception as exc:
        record_error("diagnostics", "Database health probe failed", exc)
    finally:
        if close_conn and conn is not None:
            conn.close()

    # Timetable freshness
    timetable_info: Dict[str, Any] = {"present": False, "fetched_at": None, "age_days": None, "is_stale": True}
    tt_file = DATA_DIR / "school_timetable.json"
    if tt_file.exists():
        try:
            tt_data = json.loads(tt_file.read_text(encoding="utf-8"))
            fetched_at = tt_data.get("fetched_at")
            age_days = None
            if fetched_at:
                dt = datetime.fromisoformat(str(fetched_at).replace("Z", ""))
                age_days = round((datetime.now() - dt).total_seconds() / 86400.0, 2)
            timetable_info = {
                "present": True,
                "fetched_at": fetched_at,
                "age_days": age_days,
                "is_stale": age_days is None or age_days > 7.0,
                "source_url": tt_data.get("source_url", ""),
            }
        except Exception as exc:
            record_error("diagnostics", "Timetable metadata probe failed", exc)

    # Operating mode & station baselines
    op_mode = workload_governor.get_operating_mode()
    baselines: Dict[str, str] = {}
    op_file = DATA_DIR / "operating_mode.json"
    if op_file.exists():
        try:
            op_cfg = json.loads(op_file.read_text(encoding="utf-8"))
            baselines = op_cfg.get("station_baselines") or {}
        except Exception as exc:
            record_error("diagnostics", "Operating mode read failed", exc)

    with _ERROR_LOCK:
        sync_telemetry = dict(_SYNC_STATE)
        errors = list(_RECENT_ERRORS)[:20]

    return {
        "status": "healthy" if db_ok else "degraded",
        "timestamp": datetime.now().isoformat(),
        "database": {
            "ok": db_ok,
            "path": str(get_db_path()),
            "counts": table_counts,
        },
        "timetable": timetable_info,
        "engine": {
            "operating_mode": op_mode,
            "station_baselines": baselines,
            "material_deficit_open": material_deficit_open,
        },
        "sync": sync_telemetry,
        "recent_errors": errors,
    }
