"""
Generates a complete, ready-to-run PostgreSQL SQL script from local data/harness.db
and data/metro_roadmap.json.
This SQL script can be pasted directly into the Supabase SQL Editor to populate all tables instantly.
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime

ROOT_DIR = Path(__file__).resolve().parent.parent
DB_PATH = ROOT_DIR / "data" / "harness.db"
METRO_PATH = ROOT_DIR / "data" / "metro_roadmap.json"
VULCAN_PATH = ROOT_DIR / "data" / "vulcan_config.json"
OUTPUT_SQL = ROOT_DIR / "supabase" / "populate_all_tables.sql"

def sql_quote(val):
    if val is None:
        return "NULL"
    if isinstance(val, bool):
        return "TRUE" if val else "FALSE"
    if isinstance(val, (int, float)):
        return str(val)
    if isinstance(val, (dict, list)):
        s = json.dumps(val, ensure_ascii=False)
        return "'" + s.replace("'", "''") + "'::jsonb"
    s = str(val)
    return "'" + s.replace("'", "''") + "'"

def make_setval_sql(table_name, col_name='id'):
    return (
        f"DO $$\n"
        f"BEGIN\n"
        f"  IF pg_get_serial_sequence('public.{table_name}', '{col_name}') IS NOT NULL THEN\n"
        f"    PERFORM setval(pg_get_serial_sequence('public.{table_name}', '{col_name}'), COALESCE(MAX({col_name}), 1)) FROM public.{table_name};\n"
        f"  END IF;\n"
        f"EXCEPTION WHEN OTHERS THEN\n"
        f"  NULL;\n"
        f"END $$;\n"
    )

def generate_sql():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    lines = []
    lines.append("-- ==========================================================================")
    lines.append("-- HARNESS // Executive OS - Supabase Database Population Script")
    lines.append(f"-- Generated: {datetime.now().isoformat()}")
    lines.append("-- Run this in Supabase Dashboard -> SQL Editor -> New Query -> Run")
    lines.append("-- ==========================================================================\n")

    # 1. tum_grades
    cur.execute("SELECT id, subject, semester, target_grade, actual_grade, percentage, notes FROM tum_grades")
    rows = cur.fetchall()
    if rows:
        lines.append("-- 1. TUM Curriculum Target & Actual Grades")
        lines.append("INSERT INTO public.tum_grades (id, subject, semester, target_grade, actual_grade, percentage, notes)")
        lines.append("VALUES")
        val_rows = []
        for r in rows:
            val_rows.append(f"  ({sql_quote(r['id'])}, {sql_quote(r['subject'])}, {sql_quote(r['semester'])}, {sql_quote(r['target_grade'])}, {sql_quote(r['actual_grade'])}, {sql_quote(r['percentage'])}, {sql_quote(r['notes'])})")
        lines.append(",\n".join(val_rows))
        lines.append("ON CONFLICT (id) DO UPDATE SET")
        lines.append("  subject = EXCLUDED.subject, semester = EXCLUDED.semester, target_grade = EXCLUDED.target_grade, actual_grade = EXCLUDED.actual_grade, percentage = EXCLUDED.percentage, notes = EXCLUDED.notes;\n")
        lines.append(make_setval_sql('tum_grades'))

    # 2. tum_grade_entries
    cur.execute("SELECT id, subject, semester, raw_input, numeric_value, weight, category, description, date, counts_in_average, created_at FROM tum_grade_entries")
    rows = cur.fetchall()
    if rows:
        lines.append("-- 2. TUM Grade Ledger Entries (Clean Vulcan & Manual Grades)")
        lines.append("INSERT INTO public.tum_grade_entries (id, subject, semester, raw_input, numeric_value, weight, category, description, date, counts_in_average, created_at)")
        lines.append("VALUES")
        val_rows = []
        for r in rows:
            counts = True if r['counts_in_average'] else False
            val_rows.append(f"  ({sql_quote(r['id'])}, {sql_quote(r['subject'])}, {sql_quote(r['semester'])}, {sql_quote(r['raw_input'])}, {sql_quote(r['numeric_value'])}, {sql_quote(r['weight'])}, {sql_quote(r['category'])}, {sql_quote(r['description'])}, {sql_quote(r['date'])}, {sql_quote(counts)}, {sql_quote(r['created_at'])})")
        lines.append(",\n".join(val_rows))
        lines.append("ON CONFLICT (id) DO UPDATE SET")
        lines.append("  subject = EXCLUDED.subject, semester = EXCLUDED.semester, raw_input = EXCLUDED.raw_input, numeric_value = EXCLUDED.numeric_value, weight = EXCLUDED.weight, category = EXCLUDED.category, description = EXCLUDED.description, date = EXCLUDED.date, counts_in_average = EXCLUDED.counts_in_average;\n")
        lines.append(make_setval_sql('tum_grade_entries'))

    # 3. tum_matura
    cur.execute("SELECT id, subject, target_percentage, current_mock_percentage, notes FROM tum_matura")
    rows = cur.fetchall()
    if rows:
        lines.append("-- 3. TUM Matura Benchmarks")
        lines.append("INSERT INTO public.tum_matura (id, subject, target_percentage, current_mock_percentage, notes)")
        lines.append("VALUES")
        val_rows = []
        for r in rows:
            val_rows.append(f"  ({sql_quote(r['id'])}, {sql_quote(r['subject'])}, {sql_quote(r['target_percentage'])}, {sql_quote(r['current_mock_percentage'])}, {sql_quote(r['notes'])})")
        lines.append(",\n".join(val_rows))
        lines.append("ON CONFLICT (subject) DO UPDATE SET")
        lines.append("  target_percentage = EXCLUDED.target_percentage, current_mock_percentage = EXCLUDED.current_mock_percentage, notes = EXCLUDED.notes;\n")
        lines.append(make_setval_sql('tum_matura'))

    # 4. tum_language
    cur.execute("SELECT id, level, target_date, status, milestone_description FROM tum_language")
    rows = cur.fetchall()
    if rows:
        lines.append("-- 4. TUM German Language Roadmap")
        lines.append("INSERT INTO public.tum_language (id, level, target_date, status, milestone_description)")
        lines.append("VALUES")
        val_rows = []
        for r in rows:
            val_rows.append(f"  ({sql_quote(r['id'])}, {sql_quote(r['level'])}, {sql_quote(r['target_date'])}, {sql_quote(r['status'])}, {sql_quote(r['milestone_description'])})")
        lines.append(",\n".join(val_rows))
        lines.append("ON CONFLICT (level) DO UPDATE SET")
        lines.append("  target_date = EXCLUDED.target_date, status = EXCLUDED.status, milestone_description = EXCLUDED.milestone_description;\n")
        lines.append(make_setval_sql('tum_language'))

    # 5. school_exams
    cur.execute("SELECT id, subject, title, exam_date, scope, completed, result_percentage, created_at FROM school_exams")
    rows = cur.fetchall()
    if rows:
        lines.append("-- 5. School Exams (Live Vulcan & Manual Tests)")
        lines.append("INSERT INTO public.school_exams (id, subject, title, exam_date, scope, completed, result_percentage, created_at)")
        lines.append("VALUES")
        val_rows = []
        for r in rows:
            comp = True if r['completed'] else False
            val_rows.append(f"  ({sql_quote(r['id'])}, {sql_quote(r['subject'])}, {sql_quote(r['title'])}, {sql_quote(r['exam_date'])}, {sql_quote(r['scope'])}, {sql_quote(comp)}, {sql_quote(r['result_percentage'])}, {sql_quote(r['created_at'])})")
        lines.append(",\n".join(val_rows))
        lines.append("ON CONFLICT (id) DO UPDATE SET")
        lines.append("  subject = EXCLUDED.subject, title = EXCLUDED.title, exam_date = EXCLUDED.exam_date, scope = EXCLUDED.scope, completed = EXCLUDED.completed, result_percentage = EXCLUDED.result_percentage;\n")
        lines.append(make_setval_sql('school_exams'))

    # 6. homework_items
    cur.execute("SELECT id, subject, title, due_date, completed, source, priority, notes, created_at FROM homework_items")
    rows = cur.fetchall()
    if rows:
        lines.append("-- 6. Homework Deliverables (Live Vulcan & Manual Homework)")
        lines.append("INSERT INTO public.homework_items (id, subject, title, due_date, completed, source, priority, notes, created_at)")
        lines.append("VALUES")
        val_rows = []
        for r in rows:
            comp = True if r['completed'] else False
            val_rows.append(f"  ({sql_quote(r['id'])}, {sql_quote(r['subject'])}, {sql_quote(r['title'])}, {sql_quote(r['due_date'])}, {sql_quote(comp)}, {sql_quote(r['source'])}, {sql_quote(r['priority'])}, {sql_quote(r['notes'])}, {sql_quote(r['created_at'])})")
        lines.append(",\n".join(val_rows))
        lines.append("ON CONFLICT (id) DO UPDATE SET")
        lines.append("  subject = EXCLUDED.subject, title = EXCLUDED.title, due_date = EXCLUDED.due_date, completed = EXCLUDED.completed, source = EXCLUDED.source, priority = EXCLUDED.priority, notes = EXCLUDED.notes;\n")
        lines.append(make_setval_sql('homework_items'))

    # 7. kill_list_items
    cur.execute("SELECT id, date, category, title, action_type, target_path, target_spec, station_deliverable_id, quantity, completed, created_at FROM kill_list_items")
    rows = cur.fetchall()
    if rows:
        lines.append("-- 7. SGH Library Kill List (Daily 3-Item Execution Engine)")
        lines.append("INSERT INTO public.kill_list_items (id, date, category, title, action_type, target_path, target_spec, station_deliverable_id, quantity, completed, created_at)")
        lines.append("VALUES")
        val_rows = []
        for r in rows:
            comp = True if r['completed'] else False
            val_rows.append(f"  ({sql_quote(r['id'])}, {sql_quote(r['date'])}, {sql_quote(r['category'])}, {sql_quote(r['title'])}, {sql_quote(r['action_type'])}, {sql_quote(r['target_path'])}, {sql_quote(r['target_spec'])}, {sql_quote(r['station_deliverable_id'])}, {sql_quote(r['quantity'])}, {sql_quote(comp)}, {sql_quote(r['created_at'])})")
        lines.append(",\n".join(val_rows))
        lines.append("ON CONFLICT (id) DO UPDATE SET")
        lines.append("  completed = EXCLUDED.completed, date = EXCLUDED.date, quantity = EXCLUDED.quantity;\n")

    # 8. station_deliverable_progress
    cur.execute("SELECT deliverable_id, station_id, stream, title, total_required, completed_count, unit_label, is_completed FROM station_deliverable_progress")
    rows = cur.fetchall()
    if rows:
        lines.append("-- 8. Station Deliverable Progress")
        lines.append("INSERT INTO public.station_deliverable_progress (deliverable_id, station_id, stream, title, total_required, completed_count, unit_label, is_completed)")
        lines.append("VALUES")
        val_rows = []
        for r in rows:
            comp = True if r['is_completed'] else False
            val_rows.append(f"  ({sql_quote(r['deliverable_id'])}, {sql_quote(r['station_id'])}, {sql_quote(r['stream'])}, {sql_quote(r['title'])}, {sql_quote(r['total_required'])}, {sql_quote(r['completed_count'])}, {sql_quote(r['unit_label'])}, {sql_quote(comp)})")
        lines.append(",\n".join(val_rows))
        lines.append("ON CONFLICT (deliverable_id) DO UPDATE SET")
        lines.append("  completed_count = EXCLUDED.completed_count, is_completed = EXCLUDED.is_completed;\n")

    # 9. daily_logs
    cur.execute("SELECT date, wake_time, sleep_time, scratchpad, reflection_worked, reflection_slipped, reflection_tomorrow, completed_blocks, completed_exercises, updated_at FROM daily_logs")
    rows = cur.fetchall()
    if rows:
        lines.append("-- 9. Daily Logs & Historical Velocity (25+ Days of Tracked Performance)")
        lines.append("INSERT INTO public.daily_logs (date, wake_time, sleep_time, scratchpad, reflection_worked, reflection_slipped, reflection_tomorrow, completed_blocks, completed_exercises, updated_at)")
        lines.append("VALUES")
        val_rows = []
        for r in rows:
            upd = r['updated_at'] or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            val_rows.append(f"  ({sql_quote(r['date'])}, {sql_quote(r['wake_time'])}, {sql_quote(r['sleep_time'])}, {sql_quote(r['scratchpad'])}, {sql_quote(r['reflection_worked'])}, {sql_quote(r['reflection_slipped'])}, {sql_quote(r['reflection_tomorrow'])}, {sql_quote(r['completed_blocks'])}, {sql_quote(r['completed_exercises'])}, {sql_quote(upd)}::timestamp with time zone)")
        lines.append(",\n".join(val_rows))
        lines.append("ON CONFLICT (date) DO UPDATE SET")
        lines.append("  wake_time = EXCLUDED.wake_time, sleep_time = EXCLUDED.sleep_time, scratchpad = EXCLUDED.scratchpad, reflection_worked = EXCLUDED.reflection_worked, reflection_slipped = EXCLUDED.reflection_slipped, reflection_tomorrow = EXCLUDED.reflection_tomorrow, completed_blocks = EXCLUDED.completed_blocks, completed_exercises = EXCLUDED.completed_exercises, updated_at = EXCLUDED.updated_at;\n")

    # 10. body_metrics
    cur.execute("SELECT * FROM body_metrics")
    rows = cur.fetchall()
    if rows:
        lines.append("-- 10. Body Metrics")
        lines.append("INSERT INTO public.body_metrics (id, date, weight_kg, calories_met, protein_met, notes)")
        lines.append("VALUES")
        val_rows = []
        for r in rows:
            cal = True if r['calories_met'] else False
            prot = True if r['protein_met'] else False
            val_rows.append(f"  ({sql_quote(r['id'])}, {sql_quote(r['date'])}, {sql_quote(r['weight_kg'])}, {sql_quote(cal)}, {sql_quote(prot)}, {sql_quote(r['notes'])})")
        lines.append(",\n".join(val_rows))
        lines.append("ON CONFLICT (id) DO UPDATE SET")
        lines.append("  weight_kg = EXCLUDED.weight_kg, protein_met = EXCLUDED.protein_met, calories_met = EXCLUDED.calories_met;\n")
        lines.append(make_setval_sql('body_metrics'))

    # 11. workouts
    cur.execute("SELECT id, date, workout_type, details, intensity, created_at FROM workouts")
    rows = cur.fetchall()
    if rows:
        lines.append("-- 11. Workouts")
        lines.append("INSERT INTO public.workouts (id, date, workout_type, details, intensity, created_at)")
        lines.append("VALUES")
        val_rows = []
        for r in rows:
            val_rows.append(f"  ({sql_quote(r['id'])}, {sql_quote(r['date'])}, {sql_quote(r['workout_type'])}, {sql_quote(r['details'])}, {sql_quote(r['intensity'])}, {sql_quote(r['created_at'])})")
        lines.append(",\n".join(val_rows))
        lines.append("ON CONFLICT (id) DO UPDATE SET")
        lines.append("  workout_type = EXCLUDED.workout_type, details = EXCLUDED.details, intensity = EXCLUDED.intensity;\n")
        lines.append(make_setval_sql('workouts'))

    # 12. projects
    cur.execute("SELECT id, name, description, local_path, github_url, current_milestone, next_action, deadline, notes, status, created_at FROM projects")
    rows = cur.fetchall()
    if rows:
        lines.append("-- 12. Projects")
        lines.append("INSERT INTO public.projects (id, name, description, local_path, github_url, current_milestone, next_action, deadline, notes, status, created_at)")
        lines.append("VALUES")
        val_rows = []
        for r in rows:
            val_rows.append(f"  ({sql_quote(r['id'])}, {sql_quote(r['name'])}, {sql_quote(r['description'])}, {sql_quote(r['local_path'])}, {sql_quote(r['github_url'])}, {sql_quote(r['current_milestone'])}, {sql_quote(r['next_action'])}, {sql_quote(r['deadline'])}, {sql_quote(r['notes'])}, {sql_quote(r['status'])}, {sql_quote(r['created_at'])})")
        lines.append(",\n".join(val_rows))
        lines.append("ON CONFLICT (id) DO UPDATE SET")
        lines.append("  name = EXCLUDED.name, current_milestone = EXCLUDED.current_milestone, next_action = EXCLUDED.next_action, status = EXCLUDED.status;\n")
        lines.append(make_setval_sql('projects'))

    # 13. metro_stations (from metro_roadmap.json)
    if METRO_PATH.exists():
        try:
            with open(METRO_PATH, "r", encoding="utf-8") as f:
                metro_json = json.load(f)
            stations = metro_json.get("stations", [])
            if stations:
                lines.append("-- 13. Metro Stations & Milestones")
                lines.append("INSERT INTO public.metro_stations (id, name, phase, month_label, year_month, is_major, status, objective, deliverables, completed_deliverables, order_idx)")
                lines.append("VALUES")
                val_rows = []
                for idx, st in enumerate(stations):
                    val_rows.append(f"  ({sql_quote(st.get('id'))}, {sql_quote(st.get('name'))}, {sql_quote(st.get('phase'))}, {sql_quote(st.get('month_label'))}, {sql_quote(st.get('date'))}, {sql_quote(bool(st.get('is_major')))}, {sql_quote(st.get('status', 'upcoming'))}, {sql_quote(st.get('objective', ''))}, {sql_quote(st.get('deliverables', {}))}, {sql_quote(st.get('completed_deliverables', []))}, {idx})")
                lines.append(",\n".join(val_rows))
                lines.append("ON CONFLICT (id) DO UPDATE SET")
                lines.append("  status = EXCLUDED.status, deliverables = EXCLUDED.deliverables, completed_deliverables = EXCLUDED.completed_deliverables;\n")
        except Exception as e:
            print("Error loading metro roadmap:", e)

    # 14. app_settings (sync config + vulcan credentials)
    lines.append("-- 14. App Settings")
    if VULCAN_PATH.exists():
        try:
            with open(VULCAN_PATH, "r", encoding="utf-8") as f:
                v_cfg = json.load(f)
            lines.append(f"INSERT INTO public.app_settings (key, value) VALUES ('vulcan_config', {sql_quote(v_cfg)}) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = now();")
        except Exception:
            pass

    conn.close()

    full_sql = "\n".join(lines)
    OUTPUT_SQL.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_SQL, "w", encoding="utf-8") as f:
        f.write(full_sql)

    print(f"Successfully generated SQL population script at: {OUTPUT_SQL}")
    print(f"Total size: {len(full_sql)} characters, {len(lines)} lines.")
    return OUTPUT_SQL

if __name__ == "__main__":
    generate_sql()
