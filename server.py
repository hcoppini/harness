"""
Harness Executive OS - REST API & Mobile Companion Server
Enables real-time cross-device sync between iPhone PWA and Desktop Application.
Deployable on Render, Railway, Fly.io, or run locally via Cloudflare Tunnel.
"""

import os
os.environ["HARNESS_SERVER"] = "1"
import json
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory, send_file

# Initialize SQLite database on launch
from app.db import init_db
from app.api import HarnessAPI
from app.services import sync_service

# Preload state from Supabase on startup if configured
try:
    sync_service.sync_all()
except Exception:
    pass

try:
    from app.services import vulcan_service
    vulcan_service.auto_sync_vulcan_if_needed()
    vulcan_service.start_vulcan_daily_scheduler()
except Exception:
    pass

BASE_DIR = Path(__file__).resolve().parent
UI_DIR = BASE_DIR / "ui"
DATA_DIR = BASE_DIR / "data"

app = Flask(__name__, static_folder=None)

# --------------------------------------------------------------------------
# CORS & Header Middleware
# --------------------------------------------------------------------------
@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Harness-Key"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@app.route("/api/<path:path>", methods=["OPTIONS"])
def api_options(path):
    return jsonify({"status": "ok"}), 200

# --------------------------------------------------------------------------
# Static & PWA Routes
# --------------------------------------------------------------------------
@app.route("/")
def index():
    # Always serve the unified full-fledged Harness OS for both desktop and mobile
    return send_file(UI_DIR / "index.html")

@app.route("/mobile")
@app.route("/mobile/")
def mobile_index():
    return send_file(UI_DIR / "index.html")

@app.route("/manifest.json")
def pwa_manifest():
    if (UI_DIR / "manifest.json").exists():
        return send_file(UI_DIR / "manifest.json", mimetype="application/manifest+json")
    if (BASE_DIR / "manifest.json").exists():
        return send_file(BASE_DIR / "manifest.json", mimetype="application/manifest+json")
    return jsonify({
        "name": "HARNESS // Executive OS",
        "short_name": "Harness",
        "description": "Executive OS & Personal Execution Tracker for TUM Heilbronn Aspirants",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#050505",
        "theme_color": "#050505"
    })

@app.route("/apple-touch-icon.png")
def apple_touch_icon():
    if (UI_DIR / "apple-touch-icon.png").exists():
        return send_file(UI_DIR / "apple-touch-icon.png", mimetype="image/png")
    if (BASE_DIR / "apple-touch-icon.png").exists():
        return send_file(BASE_DIR / "apple-touch-icon.png", mimetype="image/png")
    if (UI_DIR / "favicon.png").exists():
        return send_file(UI_DIR / "favicon.png", mimetype="image/png")
    return "", 404

@app.route("/icon-192.png")
def icon_192():
    if (UI_DIR / "icon-192.png").exists():
        return send_file(UI_DIR / "icon-192.png", mimetype="image/png")
    if (BASE_DIR / "icon-192.png").exists():
        return send_file(BASE_DIR / "icon-192.png", mimetype="image/png")
    return "", 404

@app.route("/icon-512.png")
def icon_512():
    if (UI_DIR / "icon-512.png").exists():
        return send_file(UI_DIR / "icon-512.png", mimetype="image/png")
    if (BASE_DIR / "icon-512.png").exists():
        return send_file(BASE_DIR / "icon-512.png", mimetype="image/png")
    return "", 404

@app.route("/sw.js")
def service_worker():
    if (UI_DIR / "sw.js").exists():
        return send_file(UI_DIR / "sw.js", mimetype="application/javascript")
    if (BASE_DIR / "sw.js").exists():
        return send_file(BASE_DIR / "sw.js", mimetype="application/javascript")
    return "", 404

@app.route("/mobile/<path:filename>")
def mobile_static(filename):
    if (UI_DIR / filename).exists():
        return send_from_directory(UI_DIR, filename)
    if (BASE_DIR / filename).exists():
        return send_from_directory(BASE_DIR, filename)
    if (UI_DIR / "favicon.png").exists():
        return send_file(UI_DIR / "favicon.png")
    return jsonify({"status": "redirected"}), 200

@app.route("/css/<path:filename>")
def css_static(filename):
    return send_from_directory(UI_DIR / "css", filename)

@app.route("/js/<path:filename>")
def js_static(filename):
    return send_from_directory(UI_DIR / "js", filename)

@app.route("/data/<path:filename>")
def data_static(filename):
    if (UI_DIR / "data" / filename).exists():
        return send_from_directory(UI_DIR / "data", filename)
    if (BASE_DIR / "data" / filename).exists():
        return send_from_directory(BASE_DIR / "data", filename)
    return jsonify({"error": "File not found"}), 404

@app.route("/favicon.png")
def favicon_png():
    if (BASE_DIR / "favicon.png").exists():
        return send_file(BASE_DIR / "favicon.png", mimetype="image/png")
    if (UI_DIR / "favicon.png").exists():
        return send_file(UI_DIR / "favicon.png", mimetype="image/png")
    return "", 404

@app.route("/favicon.ico")
def favicon_ico():
    if (BASE_DIR / "favicon.ico").exists():
        return send_file(BASE_DIR / "favicon.ico", mimetype="image/x-icon")
    if (UI_DIR / "favicon.ico").exists():
        return send_file(UI_DIR / "favicon.ico", mimetype="image/x-icon")
    return "", 404

# --------------------------------------------------------------------------
# REST API Endpoints
# --------------------------------------------------------------------------
api = HarnessAPI()

@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "healthy",
        "service": "Harness Executive OS",
        "timestamp": datetime.now().isoformat()
    })

# --------------------------------------------------------------------------
# Universal RPC Bridge (For Web Browsers & Cloud Deployments)
# --------------------------------------------------------------------------
@app.route("/api/rpc/<method_name>", methods=["GET", "POST"])
def rpc_dispatcher(method_name):
    """
    Universal RPC dispatcher that dynamically invokes HarnessAPI methods.
    Allows web browsers on Render/Railway/localhost to use the exact same
    API contract as desktop PyWebView.
    """
    if not hasattr(api, method_name) or method_name.startswith("_"):
        return jsonify({"error": f"Method '{method_name}' not found on HarnessAPI", "status": "error"}), 404

    if request.method == "POST":
        payload = request.get_json(silent=True) or {}
        args = payload.get("args", [])
        kwargs = payload.get("kwargs", {})
    else:
        args = []
        kwargs = dict(request.args)

    if not isinstance(args, list):
        args = [args]
    if not isinstance(kwargs, dict):
        kwargs = {}

    try:
        method = getattr(api, method_name)
        result = method(*args, **kwargs)

        # If write mutation, trigger immediate background sync to Supabase
        if any(method_name.startswith(p) for p in ["add_", "toggle_", "delete_", "update_", "save_", "log_", "rollover_", "import_", "quick_"]):
            try:
                sync_service.sync_all()
            except Exception:
                pass

        return jsonify({"result": result, "status": "ok"}), 200
    except Exception as e:
        return jsonify({"error": str(e), "status": "error"}), 500

# --------------------------------------------------------------------------
# Direct Cross-Device Sync Endpoints (Local Executable <-> Web Server)
# --------------------------------------------------------------------------
@app.route("/api/sync/status", methods=["GET"])
def sync_status_endpoint():
    return jsonify(api.get_sync_status())

@app.route("/api/sync/exchange", methods=["POST"])
def sync_exchange_endpoint():
    """
    Accepts local payload from desktop executable or client, merges it into the server database,
    and returns latest merged state for all entities in a single atomic transaction.
    """
    payload = request.get_json(silent=True) or {}
    client_data = payload.get("data") if ("data" in payload and isinstance(payload.get("data"), dict)) else payload
    from app.db import get_connection, DATA_DIR
    conn = get_connection()
    synced_count = 0
    try:
        cursor = conn.cursor()

        # 1. Merge Tasks
        for t in client_data.get("tasks", []):
            t_id = t.get("id")
            if not t_id:
                continue
            cursor.execute("SELECT id, completed FROM tasks WHERE id = ?", (t_id,))
            loc = cursor.fetchone()
            comp = 1 if t.get("completed") else 0
            if not loc:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO tasks (id, title, category, is_tum, completed, date, rollover_count, created_at, completed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        t_id,
                        t.get("title", ""),
                        t.get("category", "personal"),
                        1 if t.get("is_tum") else 0,
                        comp,
                        t.get("date", datetime.now().strftime("%Y-%m-%d")),
                        t.get("rollover_count", 0),
                        t.get("created_at"),
                        t.get("completed_at"),
                    ),
                )
                synced_count += 1
            elif loc["completed"] != comp:
                cursor.execute("UPDATE tasks SET completed = ? WHERE id = ?", (comp, t_id))
                synced_count += 1

        # 2. Merge Daily Logs
        for dl in client_data.get("daily_logs", []):
            dt = dl.get("date")
            if not dt:
                continue
            cursor.execute("SELECT * FROM daily_logs WHERE date = ?", (dt,))
            loc = cursor.fetchone()
            rem_updated = dl.get("updated_at") or ""
            if not loc:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO daily_logs
                    (date, scratchpad, wake_time, sleep_time, reflection_worked, reflection_slipped, reflection_tomorrow, completed_blocks, completed_exercises, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        dt,
                        dl.get("scratchpad", "") or "",
                        dl.get("wake_time", "") or "",
                        dl.get("sleep_time", "") or "",
                        dl.get("reflection_worked", "") or "",
                        dl.get("reflection_slipped", "") or "",
                        dl.get("reflection_tomorrow", "") or "",
                        dl.get("completed_blocks", "") or "",
                        dl.get("completed_exercises", "") or "",
                        rem_updated or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    ),
                )
                synced_count += 1
            else:
                loc_dict = dict(loc)
                loc_updated = loc_dict.get("updated_at") or ""

                if rem_updated and loc_updated and rem_updated != loc_updated:
                    if rem_updated > loc_updated:
                        merged_b = dl.get("completed_blocks", "") or ""
                        merged_e = dl.get("completed_exercises", "") or ""
                        sp = dl.get("scratchpad") if dl.get("scratchpad") is not None else (loc_dict.get("scratchpad") or "")
                        rw = dl.get("reflection_worked") or loc_dict.get("reflection_worked") or ""
                        rs = dl.get("reflection_slipped") or loc_dict.get("reflection_slipped") or ""
                        rt = dl.get("reflection_tomorrow") or loc_dict.get("reflection_tomorrow") or ""
                        wt = dl.get("wake_time") or loc_dict.get("wake_time") or ""
                        st = dl.get("sleep_time") or loc_dict.get("sleep_time") or ""
                        target_updated = rem_updated
                    else:
                        merged_b = loc_dict.get("completed_blocks", "") or ""
                        merged_e = loc_dict.get("completed_exercises", "") or ""
                        sp = loc_dict.get("scratchpad") or dl.get("scratchpad") or ""
                        rw = loc_dict.get("reflection_worked") or dl.get("reflection_worked") or ""
                        rs = loc_dict.get("reflection_slipped") or dl.get("reflection_slipped") or ""
                        rt = loc_dict.get("reflection_tomorrow") or dl.get("reflection_tomorrow") or ""
                        wt = loc_dict.get("wake_time") or dl.get("wake_time") or ""
                        st = loc_dict.get("sleep_time") or dl.get("sleep_time") or ""
                        target_updated = loc_updated
                else:
                    loc_b = set(filter(None, (loc_dict.get("completed_blocks") or "").split(",")))
                    rem_b = set(filter(None, (dl.get("completed_blocks") or "").split(",")))
                    merged_b = ",".join(sorted(loc_b.union(rem_b)))

                    loc_e = set(filter(None, (loc_dict.get("completed_exercises") or "").split(",")))
                    rem_e = set(filter(None, (dl.get("completed_exercises") or "").split(",")))
                    merged_e = ",".join(sorted(loc_e.union(rem_e)))

                    sp = dl.get("scratchpad") if len(dl.get("scratchpad") or "") >= len(loc_dict.get("scratchpad") or "") else loc_dict.get("scratchpad")
                    rw = dl.get("reflection_worked") if len(dl.get("reflection_worked", "") or "") >= len(loc_dict.get("reflection_worked", "") or "") else loc_dict.get("reflection_worked", "")
                    rs = dl.get("reflection_slipped") if len(dl.get("reflection_slipped", "") or "") >= len(loc_dict.get("reflection_slipped", "") or "") else loc_dict.get("reflection_slipped", "")
                    rt = dl.get("reflection_tomorrow") if len(dl.get("reflection_tomorrow", "") or "") >= len(loc_dict.get("reflection_tomorrow", "") or "") else loc_dict.get("reflection_tomorrow", "")
                    wt = dl.get("wake_time") or loc_dict.get("wake_time") or ""
                    st = dl.get("sleep_time") or loc_dict.get("sleep_time") or ""
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

        # 3. Merge Kill List Items
        for kl in client_data.get("kill_list_items", []):
            k_id = kl.get("id")
            if not k_id:
                continue
            k_comp = 1 if kl.get("completed") else 0
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
                        kl.get("date", ""),
                        kl.get("category", "General"),
                        kl.get("title", ""),
                        kl.get("action_type", "url"),
                        kl.get("target_path", ""),
                        kl.get("target_spec", ""),
                        kl.get("station_deliverable_id"),
                        k_comp,
                    ),
                )
                synced_count += 1
            elif loc["completed"] != k_comp:
                cursor.execute("UPDATE kill_list_items SET completed = ? WHERE id = ?", (k_comp, k_id))
                synced_count += 1

        # 4. Merge Station Deliverable Progress
        for sdp in client_data.get("station_deliverable_progress", []):
            d_id = sdp.get("deliverable_id")
            if not d_id:
                continue
            rem_count = sdp.get("completed_count", 0)
            rem_done = 1 if sdp.get("is_completed") else 0
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
                        sdp.get("station_id", "sep-2026"),
                        sdp.get("stream", "code"),
                        sdp.get("title", ""),
                        sdp.get("total_required", 1),
                        rem_count,
                        sdp.get("unit_label", "reps"),
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

        # 5. Merge Body Metrics
        for bm in client_data.get("body_metrics", []):
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

        # 6. Merge Workouts
        for wo in client_data.get("workouts", []):
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

        # 7. Merge Projects
        for pr in client_data.get("projects", []):
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

        # 8. Merge Metro Roadmap
        if "metro_roadmap" in client_data and isinstance(client_data["metro_roadmap"], dict):
            rem_metro = client_data["metro_roadmap"]
            rem_stations = rem_metro.get("stations", [])
            metro_file = DATA_DIR / "metro_roadmap.json"
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

        # 9. Merge School Exams
        for ex in client_data.get("school_exams", []):
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

        # 10. Merge Homework Items
        for hw in client_data.get("homework_items", []):
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

        # 11. Merge TUM Grade Entries
        for ge in client_data.get("tum_grade_entries", []):
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

        # 12. Merge TUM Target Grades
        for tg in client_data.get("tum_grades", []):
            tg_id = tg.get("id")
            if not tg_id:
                continue
            cursor.execute("SELECT id, actual_grade, percentage, target_grade FROM tum_grades WHERE id = ?", (tg_id,))
            loc = cursor.fetchone()
            if not loc:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO tum_grades (id, subject, semester, target_grade, actual_grade, percentage, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (tg_id, tg.get("subject"), int(tg.get("semester", 1)), float(tg.get("target_grade", 5.0)), tg.get("actual_grade"), tg.get("percentage"), tg.get("notes", ""))
                )
                synced_count += 1
            elif loc["actual_grade"] != tg.get("actual_grade") or loc["percentage"] != tg.get("percentage") or loc["target_grade"] != tg.get("target_grade"):
                cursor.execute(
                    "UPDATE tum_grades SET target_grade = ?, actual_grade = ?, percentage = ?, notes = ? WHERE id = ?",
                    (tg.get("target_grade"), tg.get("actual_grade"), tg.get("percentage"), tg.get("notes", ""), tg_id)
                )
                synced_count += 1

        # 13. Merge TUM Matura
        for tm in client_data.get("tum_matura", []):
            tm_id = tm.get("id")
            if not tm_id:
                continue
            cursor.execute("SELECT id, current_mock_percentage FROM tum_matura WHERE id = ?", (tm_id,))
            loc = cursor.fetchone()
            if not loc:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO tum_matura (id, subject, target_percentage, current_mock_percentage, notes)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (tm_id, tm.get("subject"), float(tm.get("target_percentage", 90.0)), float(tm.get("current_mock_percentage", 0.0)), tm.get("notes", ""))
                )
                synced_count += 1
            elif loc["current_mock_percentage"] != tm.get("current_mock_percentage"):
                cursor.execute("UPDATE tum_matura SET current_mock_percentage = ? WHERE id = ?", (tm.get("current_mock_percentage"), tm_id))
                synced_count += 1

        # 14. Merge TUM Language
        for tl in client_data.get("tum_language", []):
            tl_id = tl.get("id")
            if not tl_id:
                continue
            cursor.execute("SELECT id, status FROM tum_language WHERE id = ?", (tl_id,))
            loc = cursor.fetchone()
            if not loc:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO tum_language (id, level, target_date, status, milestone_description)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (tl_id, tl.get("level"), tl.get("target_date"), tl.get("status", "pending"), tl.get("milestone_description", ""))
                )
                synced_count += 1
            elif loc["status"] != tl.get("status"):
                cursor.execute("UPDATE tum_language SET status = ? WHERE id = ?", (tl.get("status"), tl_id))
                synced_count += 1

        conn.commit()

        # Query and return the full merged server state
        def fetch_all(q):
            try:
                cursor.execute(q)
                return [dict(r) for r in cursor.fetchall()]
            except Exception:
                return []

        server_state = {
            "tasks": fetch_all("SELECT * FROM tasks"),
            "daily_logs": fetch_all("SELECT * FROM daily_logs"),
            "kill_list_items": fetch_all("SELECT * FROM kill_list_items"),
            "station_deliverable_progress": fetch_all("SELECT * FROM station_deliverable_progress"),
            "school_exams": fetch_all("SELECT * FROM school_exams"),
            "homework_items": fetch_all("SELECT * FROM homework_items"),
            "tum_grade_entries": fetch_all("SELECT * FROM tum_grade_entries"),
            "tum_grades": fetch_all("SELECT * FROM tum_grades"),
            "tum_matura": fetch_all("SELECT * FROM tum_matura"),
            "tum_language": fetch_all("SELECT * FROM tum_language"),
            "body_metrics": fetch_all("SELECT * FROM body_metrics"),
            "workouts": fetch_all("SELECT * FROM workouts"),
            "projects": fetch_all("SELECT * FROM projects"),
        }
        metro_file = DATA_DIR / "metro_roadmap.json"
        if metro_file.exists():
            try:
                with open(metro_file, "r", encoding="utf-8") as f:
                    server_state["metro_roadmap"] = json.load(f)
            except Exception:
                server_state["metro_roadmap"] = {}

        # Trigger background Supabase sync on server if configured
        try:
            cfg = sync_service.get_sync_config()
            if cfg.get("supabase_key"):
                import threading
                threading.Thread(target=sync_service.sync_all, daemon=True).start()
        except Exception:
            pass

        return jsonify({
            "status": "ok",
            "synced_count": synced_count,
            "timestamp": datetime.now().isoformat(),
            "data": server_state,
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500
    finally:
        conn.close()

# --- Layer 0: Dashboard ---
@app.route("/api/dashboard", methods=["GET"])
def get_dashboard():
    date_str = request.args.get("date")
    data = api.get_dashboard(client_date=date_str)
    return jsonify(data)

# --- Layer 1: Today ---
@app.route("/api/today", methods=["GET"])
def get_today():
    date_str = request.args.get("date")
    data = api.get_today(date_str)
    return jsonify(data)

@app.route("/api/today/log", methods=["POST"])
def update_daily_log():
    payload = request.get_json(silent=True) or {}
    success = api.update_daily_log(
        scratchpad=payload.get("scratchpad"),
        wake_time=payload.get("wake_time"),
        sleep_time=payload.get("sleep_time"),
        reflection_worked=payload.get("reflection_worked"),
        reflection_slipped=payload.get("reflection_slipped"),
        reflection_tomorrow=payload.get("reflection_tomorrow"),
        completed_blocks=payload.get("completed_blocks"),
        completed_exercises=payload.get("completed_exercises"),
        date_str=payload.get("date"),
    )
    return jsonify({"success": success})

@app.route("/api/tasks", methods=["POST"])
def add_task():
    payload = request.get_json(silent=True) or {}
    title = payload.get("title", "").strip()
    if not title:
        return jsonify({"error": "Task title is required"}), 400
    task = api.add_task(
        title=title,
        category=payload.get("category", "General"),
        is_tum=bool(payload.get("is_tum", False)),
        date_str=payload.get("date"),
    )
    return jsonify(task)

@app.route("/api/tasks/<int:task_id>/toggle", methods=["POST"])
def toggle_task(task_id):
    task = api.toggle_task(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404
    return jsonify(task)

@app.route("/api/tasks/<int:task_id>/delete", methods=["POST"])
def delete_task(task_id):
    success = api.delete_task(task_id)
    return jsonify({"success": success})

@app.route("/api/tasks/rollover", methods=["POST"])
def rollover_tasks():
    count = api.rollover_tasks()
    return jsonify({"rolled_over_count": count})

# --- Kill List Drawer & Execution Engine (Harness 2.1) ---
@app.route("/api/kill-list", methods=["GET"])
def get_kill_list():
    date_str = request.args.get("date")
    return jsonify(api.get_kill_list(date_str))

@app.route("/api/kill-list", methods=["POST"])
def add_kill_item():
    payload = request.get_json(silent=True) or {}
    try:
        item = api.add_kill_item(
            category=payload.get("category", "Math R"),
            title=payload.get("title", "").strip(),
            action_type=payload.get("action_type", "url"),
            target_path=payload.get("target_path", ""),
            target_spec=payload.get("target_spec", ""),
            station_deliverable_id=payload.get("station_deliverable_id"),
            quantity=int(payload.get("quantity", 1)),
            date_str=payload.get("date"),
        )
        return jsonify(item), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/kill-list/<item_id>/complete", methods=["POST"])
def complete_kill_item(item_id):
    res = api.complete_kill_item(item_id)
    return jsonify(res)

@app.route("/api/kill-list/<item_id>/toggle", methods=["POST"])
def toggle_kill_item(item_id):
    res = api.toggle_kill_item(item_id)
    return jsonify(res)

@app.route("/api/kill-list/<item_id>", methods=["DELETE"])
def delete_kill_item(item_id):
    success = api.delete_kill_item(item_id)
    return jsonify({"success": success})

@app.route("/api/kill-list/launch", methods=["POST"])
def launch_kill_item():
    payload = request.get_json(silent=True) or {}
    res = api.launch_kill_item(payload.get("action_type", "url"), payload.get("target_path", ""))
    return jsonify(res)

@app.route("/api/kill-list/enqueue-progressive", methods=["POST"])
def enqueue_progressive_deliverable():
    payload = request.get_json(silent=True) or {}
    deliverable_id = payload.get("deliverable_id", "")
    date_str = payload.get("date")
    res = api.enqueue_progressive_deliverable(deliverable_id, date_str)
    return jsonify(res)

@app.route("/api/kill-list/enqueue-exam-prep", methods=["POST"])
def enqueue_exam_prep():
    payload = request.get_json(silent=True) or {}
    exam_id = int(payload.get("exam_id", 0))
    date_str = payload.get("date")
    res = api.enqueue_exam_prep(exam_id, date_str)
    return jsonify(res)

@app.route("/api/kill-list/auto-populate", methods=["POST"])
def auto_populate_kill_list_route():
    payload = request.get_json(silent=True) or {}
    date_str = payload.get("date")
    res = api.auto_populate_kill_list(date_str)
    return jsonify(res)

# --- Harness 3.0: Adaptive Workload Governor & Vulcan UONET+ ---
@app.route("/api/workload", methods=["GET"])
def get_workload_analysis():
    date_str = request.args.get("date")
    return jsonify(api.get_workload_analysis(date_str))

@app.route("/api/workload/recommended", methods=["GET"])
def get_recommended_kill_items():
    date_str = request.args.get("date")
    return jsonify(api.get_recommended_kill_items(date_str))

@app.route("/api/vulcan/sync", methods=["POST"])
def sync_vulcan():
    payload = request.get_json(silent=True) or {}
    client_date = payload.get("date")
    force = bool(payload.get("force", False))
    res = api.sync_vulcan_data(client_date, force)
    return jsonify(res)

@app.route("/api/vulcan/config", methods=["GET", "POST"])
def vulcan_config():
    if request.method == "POST":
        payload = request.get_json(silent=True) or {}
        success = api.save_vulcan_config(payload)
        return jsonify({"success": success})
    return jsonify(api.get_vulcan_config())

@app.route("/api/vulcan/register", methods=["POST"])
def register_vulcan():
    payload = request.get_json(silent=True) or {}
    token_input = payload.get("token") or payload.get("token_input") or ""
    res = api.register_eduvulcan(token_input)
    return jsonify(res)

@app.route("/api/vulcan/status", methods=["GET"])
def get_vulcan_status_route():
    return jsonify(api.get_vulcan_status())

@app.route("/api/vulcan/disconnect", methods=["POST"])
def disconnect_vulcan_route():
    success = api.disconnect_vulcan()
    return jsonify({"success": success})

@app.route("/api/school/exam/manual", methods=["POST"])
def add_manual_exam_route():
    payload = request.get_json(silent=True) or {}
    subject = payload.get("subject", "General")
    title = payload.get("title", "Exam")
    exam_date = payload.get("exam_date") or datetime.now().strftime("%Y-%m-%d")
    scope = payload.get("scope", "")
    weight = int(payload.get("weight", 2))
    res = api.add_manual_exam(subject, title, exam_date, scope, weight)
    return jsonify(res)

@app.route("/api/vulcan/auto-sync", methods=["POST"])
def auto_sync_vulcan_route():
    payload = request.get_json(silent=True) or {}
    client_date = payload.get("date")
    res = api.auto_sync_vulcan(client_date)
    return jsonify(res or {"status": "fresh"})


# --- Layer 2: TUM Metro & Bavarian Aptitude ---
@app.route("/api/tum/overview", methods=["GET"])
def get_tum_overview():
    return jsonify(api.get_tum_overview())

@app.route("/api/tum/aptitude", methods=["POST"])
def calculate_tum_aptitude():
    payload = request.get_json(silent=True) or {}
    gpa = float(payload.get("gpa_pl", 5.0))
    math_val = float(payload.get("math_pl", 5.0))
    cs_val = float(payload.get("cs_pl", 5.0))
    lang_val = float(payload.get("lang_pl", 5.0))
    return jsonify(api.calculate_tum_aptitude(gpa, math_val, cs_val, lang_val))

@app.route("/api/tum/grades/entries", methods=["GET", "POST"])
def tum_grade_entries():
    if request.method == "POST":
        payload = request.get_json(silent=True) or {}
        res = api.add_grade_entry(
            subject=payload.get("subject", ""),
            semester=int(payload.get("semester", 1)),
            raw_input=payload.get("raw_input", ""),
            weight=float(payload.get("weight", 1.0)),
            category=payload.get("category", "Grade"),
            description=payload.get("description", ""),
            date_str=payload.get("date"),
        )
        return jsonify(res), 201
    else:
        subject = request.args.get("subject")
        semester = request.args.get("semester")
        sem_int = int(semester) if semester and semester.isdigit() else None
        return jsonify(api.get_grade_entries(subject=subject, semester=sem_int))

@app.route("/api/tum/grades/entries/<int:entry_id>", methods=["DELETE"])
def delete_tum_grade_entry(entry_id):
    success = api.delete_grade_entry(entry_id)
    return jsonify({"success": success})

@app.route("/api/metro/deliverables/<deliverable_id>/progress", methods=["POST"])
def update_deliverable_progress_route(deliverable_id):
    payload = request.get_json(silent=True) or {}
    new_count = payload.get("new_count")
    delta = payload.get("delta")
    res = api.update_deliverable_progress(deliverable_id, new_count=new_count, delta=delta)
    return jsonify(res)

@app.route("/api/metro/deliverables/<deliverable_id>/reps", methods=["POST"])
def log_study_reps_route(deliverable_id):
    payload = request.get_json(silent=True) or {}
    count = int(payload.get("count", 1))
    notes = payload.get("notes", "")
    res = api.log_study_reps(deliverable_id, count=count, notes=notes)
    return jsonify(res)

@app.route("/api/metro/<station_id>/progress", methods=["GET"])
def get_station_progress(station_id):
    return jsonify(api.get_station_deliverables(station_id))

@app.route("/api/metro/<station_id>/velocity", methods=["GET"])
def get_station_velocity(station_id):
    date_str = request.args.get("date")
    return jsonify(api.get_station_pace_velocity(station_id, date_str))
@app.route("/api/metro", methods=["GET"])
def get_metro():
    data = api.get_metro_roadmap()
    return jsonify(data)

@app.route("/api/metro/<station_id>/deliverable", methods=["POST"])
def toggle_metro_deliverable(station_id):
    payload = request.get_json(silent=True) or {}
    key = payload.get("deliverable_key", "")
    if not key:
        return jsonify({"error": "deliverable_key is required"}), 400
    res = api.toggle_station_deliverable(station_id, key)
    return jsonify(res)

@app.route("/api/metro/<station_id>/status", methods=["POST"])
def update_metro_status(station_id):
    payload = request.get_json(silent=True) or {}
    status = payload.get("status", "upcoming")
    success = api.update_station_status(station_id, status)
    return jsonify({"success": success})

# --- Layer 3: Projects ---
@app.route("/api/projects", methods=["GET"])
def get_projects():
    data = api.get_projects()
    return jsonify(data)

@app.route("/api/projects/<int:project_id>/next_action", methods=["POST"])
def update_project_next_action(project_id):
    payload = request.get_json(silent=True) or {}
    next_action = payload.get("next_action", "")
    milestone = payload.get("current_milestone", "")
    success = api.update_project(project_id, next_action=next_action, current_milestone=milestone)
    return jsonify({"success": success})

# --- Layer 4: Body ---
@app.route("/api/body", methods=["GET"])
def get_body():
    summary = api.get_body_summary()
    history = api.get_body_history(30)
    return jsonify({
        "summary": summary,
        "history": history,
        "target_weight_kg": 80.0
    })

@app.route("/api/body/metric", methods=["POST"])
def add_body_metric():
    payload = request.get_json(silent=True) or {}
    weight_kg = float(payload.get("weight_kg", 0))
    calories_met = bool(payload.get("calories_met", False))
    protein_met = bool(payload.get("protein_met", False))
    notes = payload.get("notes", "")
    date_str = payload.get("date")
    metric = api.log_body_metric(weight_kg, calories_met, protein_met, notes, date_str)
    return jsonify(metric)

@app.route("/api/body/workout", methods=["POST"])
def log_workout():
    payload = request.get_json(silent=True) or {}
    workout_type = payload.get("workout_type", "Gym")
    details = payload.get("details", "")
    date_str = payload.get("date")
    w = api.log_workout(workout_type, details, date_str=date_str)
    return jsonify(w)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "0.0.0.0")
    print(f"==================================================")
    print(f"  HARNESS EXECUTIVE OS - SYNC SERVER ACTIVE")
    print(f"  Local Desktop View: http://localhost:{port}")
    print(f"  iPhone Companion:   http://localhost:{port}/mobile")
    print(f"==================================================")
    app.run(host=host, port=port, debug=False)
