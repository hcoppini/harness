"""Self-leveling engine, baseline rebase controller, and School Material Deficit ledger."""

import json
import re
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.db import DATA_DIR, get_connection
from app.diagnostics import record_error

OPERATING_MODE_FILE = DATA_DIR / "operating_mode.json"
SCHEDULES_FILE = DATA_DIR / "schedules.json"
METRO_ROADMAP_FILE = DATA_DIR / "metro_roadmap.json"

DEFAULT_MATERIAL_DEFICIT: List[Dict[str, Any]] = [
    {
        "id": "def_math_trygonometria",
        "subject": "Matematyka",
        "topic": "Trygonometria — wzory redukcyjne, miara łukowa, tożsamości i równania",
        "priority": 1,
        "status": "active",
        "source_note": "Upcoming Sprawdzian (2026-11-27). Active defense priority.",
    },
    {
        "id": "def_math_okregi",
        "subject": "Matematyka",
        "topic": "Geometria płaska — okręgi i koła (okrąg wpisany i opisany)",
        "priority": 1,
        "status": "open",
        "source_note": "Concept gap from Oct 26 (grades locked as baseline; repair concept for Matura).",
    },
    {
        "id": "def_math_tozsamosci",
        "subject": "Matematyka",
        "topic": "Tożsamości trygonometryczne — przekształcenia i dowody",
        "priority": 1,
        "status": "open",
        "source_note": "Concept gap from Nov 2 (repair alongside weekly 40-exercise math cadence).",
    },
    {
        "id": "def_cs_iteracje",
        "subject": "Informatyka",
        "topic": "C++ Podstawy i instrukcje iteracyjne (pętle for/while, ręczne śledzenie)",
        "priority": 2,
        "status": "open",
        "source_note": "Missed Oct 22 (nb) — foundational for Matura CS & JetBrains Club.",
    },
    {
        "id": "def_cs_funkcje_nwd",
        "subject": "Informatyka",
        "topic": "Funkcje w C++, algorytm Euklidesa (NWD/NWW) i zadania tekstowe",
        "priority": 2,
        "status": "open",
        "source_note": "Consolidate from Nov 23 sprawdzian.",
    },
    {
        "id": "def_phys_termodynamika",
        "subject": "Fizyka",
        "topic": "Termodynamika — bilans cieplny i przemiany fazowe",
        "priority": 3,
        "status": "open",
        "source_note": "Concept gap from Oct 5 (grades locked as baseline).",
    },
    {
        "id": "def_phys_elektrostatyka",
        "subject": "Fizyka",
        "topic": "Elektrostatyka — prawo Coulomba, pole elektryczne i potencjał",
        "priority": 3,
        "status": "open",
        "source_note": "Missed Nov 16 (nb) — core Semester 1 concept.",
    },
]


def ensure_material_deficit_table(conn: Optional[sqlite3.Connection] = None) -> None:
    """Creates the material_deficit table if it does not exist."""
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS material_deficit (
            id TEXT PRIMARY KEY,
            subject TEXT NOT NULL,
            topic TEXT NOT NULL,
            priority INTEGER NOT NULL DEFAULT 2,
            status TEXT NOT NULL DEFAULT 'open',
            source_note TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    conn.commit()
    if close_conn:
        conn.close()


def seed_material_deficit_ledger(conn: Optional[sqlite3.Connection] = None) -> int:
    """Seeds default school material deficit items idempotently without overwriting user progress."""
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    ensure_material_deficit_table(conn)
    cur = conn.cursor()
    inserted = 0
    for item in DEFAULT_MATERIAL_DEFICIT:
        cur.execute("SELECT id FROM material_deficit WHERE id = ?", (item["id"],))
        if not cur.fetchone():
            cur.execute(
                """
                INSERT INTO material_deficit (id, subject, topic, priority, status, source_note)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    item["id"],
                    item["subject"],
                    item["topic"],
                    item["priority"],
                    item["status"],
                    item["source_note"],
                ),
            )
            inserted += 1
    conn.commit()
    if close_conn:
        conn.close()
    return inserted


def get_material_deficit(
    status: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> List[Dict[str, Any]]:
    """Returns tracked school concept deficit items ordered by priority."""
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    ensure_material_deficit_table(conn)
    cur = conn.cursor()
    if status:
        rows = cur.execute(
            "SELECT * FROM material_deficit WHERE status = ? ORDER BY priority ASC, subject ASC, id ASC",
            (status,),
        ).fetchall()
    else:
        rows = cur.execute(
            "SELECT * FROM material_deficit ORDER BY CASE status WHEN 'active' THEN 0 WHEN 'open' THEN 1 ELSE 2 END, priority ASC, subject ASC"
        ).fetchall()

    items = []
    for r in rows:
        d = dict(r)
        d["mastered"] = d.get("status") == "resolved"
        items.append(d)

    if close_conn:
        conn.close()
    return items


get_material_deficits = get_material_deficit


def add_material_deficit(
    subject: str,
    topic: str,
    priority: Any = 2,
    source_note: str = "",
    item_id: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
    notes: Optional[str] = None,
    **kwargs,
) -> Dict[str, Any]:
    """Adds a new school material deficit unit."""
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    ensure_material_deficit_table(conn)
    slug = re.sub(r"[^a-z0-9]+", "_", f"{subject}_{topic}".lower()).strip("_")[:48]
    uid = item_id or f"def_{slug}"
    
    # Clean priority (e.g. 'P1' -> 1)
    if isinstance(priority, str):
        digits = re.sub(r"\D", "", priority)
        p_val = int(digits) if digits else 2
    else:
        p_val = int(priority) if priority else 2

    final_note = source_note or notes or kwargs.get("notes") or ""

    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO material_deficit (id, subject, topic, priority, status, source_note)
        VALUES (?, ?, ?, ?, 'open', ?)
        ON CONFLICT(id) DO UPDATE SET
            subject = excluded.subject,
            topic = excluded.topic,
            priority = excluded.priority,
            source_note = excluded.source_note,
            updated_at = CURRENT_TIMESTAMP
        """,
        (uid, subject.strip(), topic.strip(), p_val, final_note.strip()),
    )
    conn.commit()
    row = dict(cur.execute("SELECT * FROM material_deficit WHERE id = ?", (uid,)).fetchone())
    row["mastered"] = row.get("status") == "resolved"
    if close_conn:
        conn.close()
    return row


def toggle_material_deficit(item_id: str, conn: Optional[sqlite3.Connection] = None) -> Dict[str, Any]:
    """Toggles a material deficit item between open/active and resolved."""
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    ensure_material_deficit_table(conn)
    cur = conn.cursor()
    row = cur.execute("SELECT * FROM material_deficit WHERE id = ?", (item_id,)).fetchone()
    if not row:
        if close_conn:
            conn.close()
        return {"success": False, "error": f"Material deficit item '{item_id}' not found"}

    new_status = "open" if row["status"] == "resolved" else "resolved"
    cur.execute(
        "UPDATE material_deficit SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (new_status, item_id),
    )
    conn.commit()
    updated = dict(cur.execute("SELECT * FROM material_deficit WHERE id = ?", (item_id,)).fetchone())
    updated["mastered"] = new_status == "resolved"
    if close_conn:
        conn.close()
    return {"success": True, "mastered": new_status == "resolved", "item": updated}


def get_station_baseline_date(station_id: str) -> Optional[str]:
    """Returns the rebase baseline YYYY-MM-DD for station_id if one has been recorded."""
    if OPERATING_MODE_FILE.exists():
        try:
            cfg = json.loads(OPERATING_MODE_FILE.read_text(encoding="utf-8"))
            baselines = cfg.get("station_baselines") or {}
            if station_id in baselines and baselines[station_id]:
                return str(baselines[station_id])[:10]
        except Exception as exc:
            record_error("leveling", "Failed reading station_baselines from operating_mode.json", exc)

    if METRO_ROADMAP_FILE.exists():
        try:
            rm = json.loads(METRO_ROADMAP_FILE.read_text(encoding="utf-8"))
            for st in rm.get("stations", []):
                if st.get("id") == station_id and st.get("baseline_date"):
                    return str(st["baseline_date"])[:10]
        except Exception as exc:
            record_error("leveling", "Failed reading baseline_date from metro_roadmap.json", exc)

    return None


def set_station_baseline_date(station_id: str, baseline_date: str) -> Dict[str, Any]:
    """Persists a station rebase baseline date in operating_mode.json."""
    clean_date = str(baseline_date).strip()[:10]
    cfg: Dict[str, Any] = {"mode": "FORTRESS"}
    if OPERATING_MODE_FILE.exists():
        try:
            cfg = json.loads(OPERATING_MODE_FILE.read_text(encoding="utf-8"))
        except Exception as exc:
            record_error("leveling", "Resetting malformed operating_mode.json", exc)
    baselines = dict(cfg.get("station_baselines") or {})
    baselines[station_id] = clean_date
    cfg["station_baselines"] = baselines
    cfg["last_rebased_at"] = datetime.now().isoformat()
    OPERATING_MODE_FILE.parent.mkdir(parents=True, exist_ok=True)
    OPERATING_MODE_FILE.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"station_id": station_id, "baseline_date": clean_date}


def get_weekly_math_slice(date_str: Optional[str] = None) -> Dict[str, Any]:
    """Returns the daily target math exercise slice (40/week split across Tue-Sat) for date_str."""
    dt = datetime.strptime(date_str[:10], "%Y-%m-%d") if date_str else datetime.now()
    weekday = dt.strftime("%A")
    default_splits = {"Tuesday": 5, "Wednesday": 8, "Thursday": 9, "Friday": 9, "Saturday": 9}
    weekly_total = 40
    splits = default_splits

    if SCHEDULES_FILE.exists():
        try:
            data = json.loads(SCHEDULES_FILE.read_text(encoding="utf-8"))
            wc = data.get("weekly_commitments") or {}
            if wc.get("math_homework_daily_splits"):
                splits = wc["math_homework_daily_splits"]
            if wc.get("math_homework_weekly_total"):
                weekly_total = int(wc["math_homework_weekly_total"])
        except Exception as exc:
            record_error("leveling", "Failed reading weekly_commitments from schedules.json", exc)

    target_today = int(splits.get(weekday, 0))
    return {
        "date": dt.strftime("%Y-%m-%d"),
        "weekday": weekday,
        "daily_target": target_today,
        "weekly_total": weekly_total,
        "daily_splits": splits,
    }


def _canonical_key(text: str) -> str:
    return re.sub(r"[^\w]+", "", (text or "").lower())


def rebase_to_today(
    baseline_date: Optional[str] = None,
    active_station_id: Optional[str] = None,
    delete_exam_ids: Optional[List[int]] = None,
    seed_deficit: bool = True,
    persist_baseline_file: bool = True,
    sync_cloud: bool = False,
    conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, Any]:
    """
    Reusable, idempotent self-leveling engine.
    Clears ghost debt, deduplicates Vulcan exams/homework, removes test junk,
    fixes mojibake, closes past stations, and records a fair baseline date for
    pace calculation — WITHOUT EVER modifying grades (tum_grades / tum_grade_entries).
    """
    clean_date = (baseline_date or datetime.now().strftime("%Y-%m-%d"))[:10]
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    ensure_material_deficit_table(conn)
    cur = conn.cursor()

    summary: Dict[str, Any] = {
        "success": True,
        "baseline_date": clean_date,
        "grades_untouched": True,
        "past_deliverables_closed": 0,
        "junk_kill_items_removed": 0,
        "expired_homework_pruned": 0,
        "duplicate_exams_removed": 0,
        "past_exams_completed": 0,
        "mojibake_fixed": 0,
        "material_deficit_seeded": 0,
    }

    # Determine active station
    if not active_station_id:
        from engine import kill_list_controller
        active_station_id = kill_list_controller.get_station_id_for_date(clean_date)
    summary["active_station_id"] = active_station_id

    # 1. Close all deliverables on stations strictly prior to active_station_id
    station_order: List[str] = []
    roadmap_data: Dict[str, Any] = {}
    if METRO_ROADMAP_FILE.exists():
        try:
            roadmap_data = json.loads(METRO_ROADMAP_FILE.read_text(encoding="utf-8"))
            station_order = [s.get("id", "") for s in roadmap_data.get("stations", [])]
        except Exception as exc:
            record_error("leveling", "Failed loading metro_roadmap.json during rebase", exc)

    if active_station_id in station_order:
        active_idx = station_order.index(active_station_id)
        past_station_ids = [sid for sid in station_order[:active_idx] if sid]
        if past_station_ids:
            placeholders = ",".join(["?"] * len(past_station_ids))
            cur.execute(
                f"""
                UPDATE station_deliverable_progress
                SET is_completed = 1,
                    completed_count = CASE WHEN completed_count < total_required THEN total_required ELSE completed_count END
                WHERE station_id IN ({placeholders}) AND is_completed = 0
                """,
                past_station_ids,
            )
            summary["past_deliverables_closed"] = cur.rowcount

        # Sync active station's deliverable_counts from metro_roadmap.json into SQLite
        active_st = next((s for s in roadmap_data.get("stations", []) if s.get("id") == active_station_id), None)
        if active_st and active_st.get("deliverable_counts"):
            deliv_titles = active_st.get("deliverables") or {}
            for stream_label, meta in active_st["deliverable_counts"].items():
                stream_key = stream_label.strip().lower()
                total_req = int(meta.get("total", 1))
                unit_lbl = str(meta.get("unit", "sessions"))
                title_txt = str(deliv_titles.get(stream_label, stream_label))
                cur.execute(
                    """
                    UPDATE station_deliverable_progress
                    SET total_required = ?, unit_label = ?, title = ?, completed_count = ?, is_completed = 0
                    WHERE station_id = ? AND LOWER(stream) = ?
                    """,
                    (total_req, unit_lbl, title_txt, int(meta.get("count", 0)), active_station_id, stream_key),
                )

    # 2. Remove junk test kill_list rows (e.g. 'Cross-sync test')
    junk_kill_ids = [
        r["id"] for r in cur.execute(
            """
            SELECT id FROM kill_list_items
            WHERE LOWER(title) LIKE '%cross-sync test%'
               OR LOWER(target_path) LIKE '%/heito/%'
               OR LOWER(target_path) LIKE '%\\heito\\%'
            """
        ).fetchall()
    ]
    if junk_kill_ids:
        placeholders = ",".join(["?"] * len(junk_kill_ids))
        cur.execute(f"DELETE FROM kill_list_items WHERE id IN ({placeholders})", junk_kill_ids)
    summary["junk_kill_items_removed"] = len(junk_kill_ids)

    # 3. Prune expired homework strictly before baseline_date
    expired_hw_ids = [
        r["id"] for r in cur.execute(
            "SELECT id FROM homework_items WHERE substr(trim(due_date), 1, 10) < ?",
            (clean_date,),
        ).fetchall()
    ]
    if expired_hw_ids:
        placeholders = ",".join(["?"] * len(expired_hw_ids))
        cur.execute(f"DELETE FROM homework_items WHERE id IN ({placeholders})", expired_hw_ids)
    summary["expired_homework_pruned"] = len(expired_hw_ids)

    # 4. Delete explicitly requested obsolete/moved exam IDs
    deleted_exam_ids: List[int] = []
    if delete_exam_ids:
        deleted_exam_ids.extend(int(x) for x in delete_exam_ids)
        placeholders = ",".join(["?"] * len(delete_exam_ids))
        cur.execute(f"DELETE FROM school_exams WHERE id IN ({placeholders})", list(delete_exam_ids))
        summary["duplicate_exams_removed"] += cur.rowcount

    # 5. Deduplicate school_exams by canonical (exam_date, subject, title)
    rows = cur.execute("SELECT id, subject, title, exam_date, completed FROM school_exams ORDER BY id ASC").fetchall()
    seen_exams = set()
    dup_exam_ids = []
    for r in rows:
        key = (
            str(r["exam_date"] or "")[:10],
            _canonical_key(r["subject"]),
            _canonical_key(r["title"]),
        )
        if key in seen_exams:
            dup_exam_ids.append(r["id"])
        else:
            seen_exams.add(key)
    if dup_exam_ids:
        deleted_exam_ids.extend(int(x) for x in dup_exam_ids)
        placeholders = ",".join(["?"] * len(dup_exam_ids))
        cur.execute(f"DELETE FROM school_exams WHERE id IN ({placeholders})", dup_exam_ids)
        summary["duplicate_exams_removed"] += cur.rowcount

    # 6. Mark exams strictly before baseline_date as completed
    cur.execute(
        "UPDATE school_exams SET completed = 1 WHERE substr(trim(exam_date), 1, 10) < ? AND completed = 0",
        (clean_date,),
    )
    summary["past_exams_completed"] = cur.rowcount

    # 7. Fix mojibake (\ufffd) in projects and kill_list_items
    for tbl, col in (("projects", "name"), ("kill_list_items", "title"), ("kill_list_items", "target_spec")):
        try:
            cur.execute(
                f"UPDATE {tbl} SET {col} = REPLACE({col}, char(65533), '–') WHERE instr({col}, char(65533)) > 0"
            )
            summary["mojibake_fixed"] += cur.rowcount
        except Exception as exc:
            record_error("leveling", f"Mojibake cleanup skipped on {tbl}.{col}", exc)

    # 8. Seed Material Deficit Ledger
    if seed_deficit:
        summary["material_deficit_seeded"] = seed_material_deficit_ledger(conn=conn)

    conn.commit()
    if close_conn:
        conn.close()

    # 9. Persist station baseline date for fair pace velocity
    if persist_baseline_file and active_station_id:
        set_station_baseline_date(active_station_id, clean_date)

    # 10. Optional cloud propagation so Supabase never resurrects leveled/deleted rows
    if sync_cloud:
        cloud_deleted = 0
        try:
            from app.services import sync_service
            for kid in junk_kill_ids:
                if sync_service.delete_remote_item("kill_list_items", "id", kid):
                    cloud_deleted += 1
            for eid in set(deleted_exam_ids):
                if sync_service.delete_remote_item("school_exams", "id", eid):
                    cloud_deleted += 1
            for hid in expired_hw_ids:
                if sync_service.delete_remote_item("homework_items", "id", hid):
                    cloud_deleted += 1
            c2 = get_connection()
            try:
                rows_deliv = [
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
                    for r in c2.execute(
                        "SELECT deliverable_id, station_id, stream, title, total_required, completed_count, unit_label, is_completed FROM station_deliverable_progress"
                    ).fetchall()
                ]
                if rows_deliv:
                    sync_service._make_supabase_request(
                        "station_deliverable_progress?on_conflict=deliverable_id",
                        method="POST",
                        payload=rows_deliv,
                        headers_extra={"Prefer": "resolution=merge-duplicates"},
                    )
                ex_rows = [
                    {
                        "id": r["id"],
                        "subject": r["subject"],
                        "title": r["title"],
                        "exam_date": str(r["exam_date"] or "")[:10],
                        "scope": r["scope"] or "",
                        "completed": bool(r["completed"]),
                        "result_percentage": r["result_percentage"],
                    }
                    for r in c2.execute(
                        "SELECT id, subject, title, exam_date, scope, completed, result_percentage FROM school_exams"
                    ).fetchall()
                ]
                if ex_rows:
                    sync_service._make_supabase_request(
                        "school_exams?on_conflict=id",
                        method="POST",
                        payload=ex_rows,
                        headers_extra={"Prefer": "resolution=merge-duplicates"},
                    )
            finally:
                c2.close()
        except Exception as exc:
            record_error("leveling", "Cloud propagation during rebase encountered an error", exc)
        summary["cloud_deleted"] = cloud_deleted

    return summary
