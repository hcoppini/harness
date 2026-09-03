"""
Harness Executive OS - REST API & Mobile Companion Server
Enables real-time cross-device sync between iPhone PWA and Desktop Application.
Deployable on Render, Railway, Fly.io, or run locally via Cloudflare Tunnel.
"""

import os
import json
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory, send_file

# Initialize SQLite database on launch
from app.db import init_db
init_db()

from app.api import HarnessAPI

BASE_DIR = Path(__file__).resolve().parent
UI_DIR = BASE_DIR / "ui"
MOBILE_DIR = BASE_DIR / "mobile"

app = Flask(__name__, static_folder=None)

# --------------------------------------------------------------------------
# CORS & Header Middleware
# --------------------------------------------------------------------------
@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Harness-Key"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    return response

@app.route("/api/<path:path>", methods=["OPTIONS"])
def api_options(path):
    return jsonify({"status": "ok"}), 200

# --------------------------------------------------------------------------
# Static & PWA Routes
# --------------------------------------------------------------------------
@app.route("/")
def index():
    # If mobile user agent, default to mobile companion
    user_agent = request.headers.get("User-Agent", "").lower()
    is_mobile = any(m in user_agent for m in ["iphone", "ipad", "android", "mobile"])
    if is_mobile and (MOBILE_DIR / "index.html").exists():
        return send_file(MOBILE_DIR / "index.html")
    return send_file(UI_DIR / "index.html")

@app.route("/mobile")
@app.route("/mobile/")
def mobile_index():
    if (MOBILE_DIR / "index.html").exists():
        return send_file(MOBILE_DIR / "index.html")
    return send_file(UI_DIR / "index.html")

@app.route("/manifest.json")
def pwa_manifest():
    if (MOBILE_DIR / "manifest.json").exists():
        return send_file(MOBILE_DIR / "manifest.json", mimetype="application/manifest+json")
    return jsonify({"name": "Harness", "display": "standalone"})

@app.route("/sw.js")
def service_worker():
    if (MOBILE_DIR / "sw.js").exists():
        return send_file(MOBILE_DIR / "sw.js", mimetype="application/javascript")
    return "", 404

@app.route("/mobile/<path:filename>")
def mobile_static(filename):
    return send_from_directory(MOBILE_DIR, filename)

@app.route("/css/<path:filename>")
def css_static(filename):
    return send_from_directory(UI_DIR / "css", filename)

@app.route("/js/<path:filename>")
def js_static(filename):
    return send_from_directory(UI_DIR / "js", filename)

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
        return jsonify({"result": result, "status": "ok"}), 200
    except Exception as e:
        return jsonify({"error": str(e), "status": "error"}), 500

# --- Layer 0: Dashboard ---
@app.route("/api/dashboard", methods=["GET"])
def get_dashboard():
    data = api.get_dashboard()
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

# --- Layer 2: TUM Metro ---
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
