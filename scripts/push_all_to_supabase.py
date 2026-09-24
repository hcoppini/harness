"""
Direct REST API Cloud Synchronizer & Migrator
Pushes all local data from SQLite and JSON files into Supabase.
"""

import sqlite3
import json
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime

ROOT_DIR = Path(__file__).resolve().parent.parent
DB_PATH = ROOT_DIR / "data" / "harness.db"
METRO_PATH = ROOT_DIR / "data" / "metro_roadmap.json"
VULCAN_PATH = ROOT_DIR / "data" / "vulcan_config.json"
CONFIG_PATH = ROOT_DIR / "data" / "sync_config.json"

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    SYNC_CFG = json.load(f)

SUPABASE_URL = SYNC_CFG["supabase_url"].rstrip("/")
SUPABASE_KEY = SYNC_CFG["supabase_key"]

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Prefer": "resolution=merge-duplicates,return=minimal"
}

def post_to_supabase(table: str, records: list):
    if not records:
        print(f"[{table}] No local records to upload.")
        return 0

    url = f"{SUPABASE_URL}/rest/v1/{table}"
    payload_bytes = json.dumps(records, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=payload_bytes, headers=HEADERS, method="POST")

    try:
        with urllib.request.urlopen(req) as resp:
            print(f"[{table}] Uploaded {len(records)} records successfully (Status {resp.status})")
            return len(records)
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8", errors="replace")
        print(f"[{table}] FAILED (Status {e.code}): {err_msg}")
        return 0
    except Exception as e:
        print(f"[{table}] Network error: {e}")
        return 0

def run_migration():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    total_uploaded = 0

    # 1. tum_grades
    cur.execute("SELECT id, subject, semester, target_grade, actual_grade, percentage, notes FROM tum_grades")
    rows = [dict(r) for r in cur.fetchall()]
    total_uploaded += post_to_supabase("tum_grades", rows)

    # 2. tum_grade_entries
    cur.execute("SELECT id, subject, semester, raw_input, numeric_value, weight, category, description, date, counts_in_average, created_at FROM tum_grade_entries")
    rows = [dict(r) for r in cur.fetchall()]
    for r in rows:
        r["counts_in_average"] = bool(r["counts_in_average"])
    total_uploaded += post_to_supabase("tum_grade_entries", rows)

    # 3. tum_matura
    cur.execute("SELECT id, subject, target_percentage, current_mock_percentage, notes FROM tum_matura")
    rows = [dict(r) for r in cur.fetchall()]
    total_uploaded += post_to_supabase("tum_matura", rows)

    # 4. tum_language
    cur.execute("SELECT id, level, target_date, status, milestone_description FROM tum_language")
    rows = [dict(r) for r in cur.fetchall()]
    total_uploaded += post_to_supabase("tum_language", rows)

    # 5. school_exams
    cur.execute("SELECT id, subject, title, exam_date, scope, completed, result_percentage, created_at FROM school_exams")
    rows = [dict(r) for r in cur.fetchall()]
    for r in rows:
        r["completed"] = bool(r["completed"])
    total_uploaded += post_to_supabase("school_exams", rows)

    # 6. homework_items
    cur.execute("SELECT id, subject, title, due_date, completed, source, priority, notes, created_at FROM homework_items")
    rows = [dict(r) for r in cur.fetchall()]
    for r in rows:
        r["completed"] = bool(r["completed"])
    total_uploaded += post_to_supabase("homework_items", rows)

    # 7. kill_list_items
    cur.execute("SELECT id, date, category, title, action_type, target_path, target_spec, station_deliverable_id, quantity, completed, created_at FROM kill_list_items")
    rows = [dict(r) for r in cur.fetchall()]
    for r in rows:
        r["completed"] = bool(r["completed"])
    total_uploaded += post_to_supabase("kill_list_items", rows)

    # 8. station_deliverable_progress
    cur.execute("SELECT deliverable_id, station_id, stream, title, total_required, completed_count, unit_label, is_completed FROM station_deliverable_progress")
    rows = [dict(r) for r in cur.fetchall()]
    for r in rows:
        r["is_completed"] = bool(r["is_completed"])
    total_uploaded += post_to_supabase("station_deliverable_progress", rows)

    # 9. app_settings
    if VULCAN_PATH.exists():
        with open(VULCAN_PATH, "r", encoding="utf-8") as f:
            v_cfg = json.load(f)
        total_uploaded += post_to_supabase("app_settings", [{"key": "vulcan_config", "value": v_cfg}])

    # 10. Optional Tables (If created in Supabase)
    for opt_table, query in [
        ("daily_logs", "SELECT date, wake_time, sleep_time, scratchpad, reflection_worked, reflection_slipped, reflection_tomorrow, completed_blocks, completed_exercises, updated_at FROM daily_logs"),
        ("body_metrics", "SELECT id, date, weight_kg, calories_met, protein_met, notes FROM body_metrics"),
        ("workouts", "SELECT id, date, workout_type, details, intensity, created_at FROM workouts"),
        ("projects", "SELECT id, name, description, local_path, github_url, current_milestone, next_action, deadline, notes, status, created_at FROM projects"),
    ]:
        try:
            cur.execute(query)
            rows = [dict(r) for r in cur.fetchall()]
            if opt_table == "body_metrics":
                for r in rows:
                    r["calories_met"] = bool(r["calories_met"])
                    r["protein_met"] = bool(r["protein_met"])
            if opt_table == "projects":
                for r in rows:
                    if r.get("local_path"):
                        r["local_path"] = r["local_path"].replace("\\", "/")
            total_uploaded += post_to_supabase(opt_table, rows)
        except Exception as e:
            print(f"[{opt_table}] Skipped/Error: {e}")

    # 11. metro_stations
    if METRO_PATH.exists():
        try:
            with open(METRO_PATH, "r", encoding="utf-8") as f:
                metro_json = json.load(f)
            stations = metro_json.get("stations", [])
            metro_rows = []
            for idx, st in enumerate(stations):
                metro_rows.append({
                    "id": st.get("id"),
                    "name": st.get("name"),
                    "phase": st.get("phase"),
                    "month_label": st.get("month_label"),
                    "year_month": st.get("date"),
                    "is_major": bool(st.get("is_major")),
                    "status": st.get("status", "upcoming"),
                    "objective": st.get("objective", ""),
                    "deliverables": st.get("deliverables", {}),
                    "completed_deliverables": st.get("completed_deliverables", []),
                    "order_idx": idx,
                })
            total_uploaded += post_to_supabase("metro_stations", metro_rows)
        except Exception as e:
            print(f"[metro_stations] Skipped/Error: {e}")

    conn.close()
    print(f"\nMigration completed: {total_uploaded} total items synced directly to Supabase cloud.")

if __name__ == "__main__":
    run_migration()
