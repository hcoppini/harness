"""Service for Dashboard Layer 0: GitHub-style activity heatmap, upcoming schedule forecast, and executive summaries."""

import json
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from app.db import get_connection, DATA_DIR
from app.services import today_service, tum_service, body_service, project_service


def get_app_inception_date(conn: sqlite3.Connection) -> str:
    """Finds the earliest date recorded in the system, or today if empty."""
    cursor = conn.cursor()
    dates = []
    for table in ["daily_logs", "tasks", "workouts", "body_metrics"]:
        try:
            cursor.execute(f"SELECT MIN(date) FROM {table} WHERE date IS NOT NULL AND date != ''")
            row = cursor.fetchone()
            if row and row[0]:
                dates.append(row[0])
        except Exception:
            pass
    if dates:
        return min(dates)
    return datetime.now().strftime("%Y-%m-%d")


def get_heatmap_data(
    start_date: Optional[str] = "2026-08-30",
    days: int = 90,
    weeks: Optional[int] = None,
    end_date: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
    include_git: bool = False,
) -> Dict[str, Any]:
    """
    Builds the daily execution heatmap matrix starting from August 30, 2026 (or custom start_date)
    and covering the 90-day cycle forward.
    Contributions and brightness levels are tied directly to how many boxes
    were checked on that day (routine blocks + tasks + gym exercises).
    Git commits are excluded from checked boxes.
    100% completion (e.g. 3/3, 8/8) produces Level 4: The Brightest Purple.
    """
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    if weeks is not None:
        days = weeks * 7

    today_dt = datetime.strptime(end_date, "%Y-%m-%d") if end_date else datetime.now()
    today_str = today_dt.strftime("%Y-%m-%d")

    # Start date: defaults to August 30, 2026
    start_date_str = start_date or "2026-08-30"
    start_dt = datetime.strptime(start_date_str, "%Y-%m-%d")

    # Align start to Sunday of inception week (Sunday=0, Monday=1... Saturday=6)
    start_sunday_offset = (start_dt.weekday() + 1) % 7
    aligned_start_dt = start_dt - timedelta(days=start_sunday_offset)

    # 90-day forward window from start date aligned to the end of the final week (Saturday)
    raw_end_dt = aligned_start_dt + timedelta(days=days)
    end_sunday_offset = (raw_end_dt.weekday() + 1) % 7
    final_end_dt = raw_end_dt + timedelta(days=(6 - end_sunday_offset))

    aligned_start_str = aligned_start_dt.strftime("%Y-%m-%d")
    final_end_date_str = final_end_dt.strftime("%Y-%m-%d")

    cursor = conn.cursor()

    # 1. Fetch tasks in range
    cursor.execute(
        """
        SELECT id, date, title, category, completed FROM tasks
        WHERE date >= ? AND date <= ?
        """,
        (aligned_start_str, final_end_date_str),
    )
    task_rows = cursor.fetchall()
    daily_tasks: Dict[str, List[Dict[str, Any]]] = {}
    for r in task_rows:
        d = r["date"]
        daily_tasks.setdefault(d, []).append({
            "id": r["id"],
            "title": r["title"],
            "category": r["category"],
            "completed": bool(r["completed"]),
        })

    # 2. Fetch daily logs (routine blocks & reflection)
    cursor.execute(
        """
        SELECT date, completed_blocks, completed_exercises, reflection_worked, reflection_slipped, reflection_tomorrow
        FROM daily_logs
        WHERE date >= ? AND date <= ?
        """,
        (aligned_start_str, final_end_date_str),
    )
    log_rows = cursor.fetchall()
    daily_logs_map: Dict[str, Dict[str, Any]] = {}
    for r in log_rows:
        daily_logs_map[r["date"]] = {
            "completed_blocks": r["completed_blocks"] or "",
            "completed_exercises": r["completed_exercises"] or "",
            "has_reflection": bool(
                (r["reflection_worked"] or "").strip()
                or (r["reflection_slipped"] or "").strip()
                or (r["reflection_tomorrow"] or "").strip()
            ),
        }

    # 3. Fetch workouts in range
    cursor.execute(
        """
        SELECT date, workout_type, details, intensity FROM workouts
        WHERE date >= ? AND date <= ?
        """,
        (aligned_start_str, final_end_date_str),
    )
    workout_rows = cursor.fetchall()
    daily_workouts: Dict[str, List[str]] = {}
    for r in workout_rows:
        d = r["date"]
        daily_workouts.setdefault(d, []).append(
            f"Workout: {r['workout_type'].capitalize()} - {r['details']} (Intensity {r['intensity']}/10)"
        )

    # Build weekly columns
    weeks_list = []
    total_contributions = 0
    month_labels = []
    last_month_name = None

    current_iter_dt = aligned_start_dt
    week_index = 0

    while current_iter_dt <= final_end_dt:
        week_days = []
        for row_idx in range(7):
            cur_str = current_iter_dt.strftime("%Y-%m-%d")

            # Check if this cell is before aligned start
            if current_iter_dt < aligned_start_dt:
                week_days.append(None)
                current_iter_dt += timedelta(days=1)
                continue

            # Record month header label if month changes
            month_name = current_iter_dt.strftime("%b")
            if row_idx == 0 and month_name != last_month_name:
                month_labels.append({
                    "name": month_name,
                    "week_index": week_index,
                })
                last_month_name = month_name

            # Calculate boxes for this day
            activities: List[str] = []

            # A. Schedule routine blocks
            sched = today_service.get_schedule_for_date(cur_str)
            sched_blocks = sched.get("blocks", [])
            total_routine_blocks = len(sched_blocks)

            dl = daily_logs_map.get(cur_str, {})
            completed_blocks_str = dl.get("completed_blocks", "")
            checked_routine_blocks = 0
            if completed_blocks_str:
                completed_indices = set([b.strip() for b in completed_blocks_str.split(",") if b.strip()])
                checked_routine_blocks = len(completed_indices)
                for idx_str in sorted(completed_indices, key=lambda x: int(x) if x.isdigit() else 99):
                    if idx_str.isdigit() and int(idx_str) < len(sched_blocks):
                        activities.append(f"✓ Routine: {sched_blocks[int(idx_str)]['focus']}")

            # B. Gym routine exercises (Tue / Thu)
            gym_routine = today_service.get_gym_routine_for_date(cur_str)
            gym_exercises = gym_routine.get("exercises", []) if gym_routine else []
            total_gym_exercises = len(gym_exercises)
            checked_gym_exercises = 0
            completed_exercises_str = dl.get("completed_exercises", "")
            if completed_exercises_str and gym_routine:
                completed_ex_indices = set([e.strip() for e in completed_exercises_str.split(",") if e.strip()])
                checked_gym_exercises = len(completed_ex_indices)
                for e_idx in sorted(completed_ex_indices, key=lambda x: int(x) if x.isdigit() else 99):
                    if e_idx.isdigit() and int(e_idx) < len(gym_exercises):
                        activities.append(f"✓ Lift: {gym_exercises[int(e_idx)]['name']}")

            # C. Custom Tasks
            tasks_list = daily_tasks.get(cur_str, [])
            total_tasks = len(tasks_list)
            checked_tasks = 0
            for t in tasks_list:
                if t["completed"]:
                    checked_tasks += 1
                    activities.append(f"✓ Task: {t['title']}")

            # D. Supplementary activities (Reflection & Logged Workouts)
            if dl.get("has_reflection", False):
                activities.append("✓ Evening reflection audit completed")

            # Total boxes and checked boxes (Excludes Git Commits)
            total_boxes = total_routine_blocks + total_gym_exercises + total_tasks
            checked_boxes = checked_routine_blocks + checked_gym_exercises + checked_tasks

            if dl.get("has_reflection", False) and total_boxes > 0:
                checked_boxes = min(checked_boxes, total_boxes)

            if current_iter_dt <= today_dt:
                total_contributions += checked_boxes

            # Map to Purple Brightness Levels:
            # - Level 0: 0 checked
            # - Level 4: 100% of boxes checked for the day (e.g. 3/3, 8/8) -> Brightest Purple!
            # - Level 3: >= 75% completed
            # - Level 2: >= 40% completed
            # - Level 1: > 0 checked
            if total_boxes == 0:
                if checked_boxes == 0:
                    level = 0
                elif checked_boxes <= 2:
                    level = 1
                elif checked_boxes <= 4:
                    level = 2
                elif checked_boxes <= 6:
                    level = 3
                else:
                    level = 4
            else:
                if checked_boxes == 0:
                    level = 0
                elif checked_boxes >= total_boxes:
                    level = 4  # Brightest Purple on 100% completion!
                else:
                    ratio = checked_boxes / total_boxes
                    if ratio >= 0.75:
                        level = 3
                    elif ratio >= 0.40:
                        level = 2
                    else:
                        level = 1

            is_future = (current_iter_dt > today_dt)
            is_today = (cur_str == today_str)

            week_days.append({
                "date": cur_str,
                "count": checked_boxes,
                "total_boxes": total_boxes,
                "level": level,
                "day_name": current_iter_dt.strftime("%A"),
                "display_date": current_iter_dt.strftime("%b %d, %Y"),
                "is_today": is_today,
                "is_future": is_future,
                "activities": activities,
            })

            current_iter_dt += timedelta(days=1)

        weeks_list.append({"week_index": week_index, "days": week_days})
        week_index += 1

    # Calculate current streak backwards from today
    current_streak = 0
    check_dt = today_dt

    # Check if today has activity
    today_has_activity = False
    for week in reversed(weeks_list):
        for day in reversed(week["days"]):
            if day and day["date"] == today_str:
                if day["count"] > 0:
                    today_has_activity = True
                break
        if today_has_activity:
            break

    if not today_has_activity:
        check_dt = today_dt - timedelta(days=1)

    while True:
        check_str = check_dt.strftime("%Y-%m-%d")
        found = False
        day_active = False
        for week in reversed(weeks_list):
            for day in week["days"]:
                if day and day["date"] == check_str:
                    found = True
                    if day["count"] > 0:
                        day_active = True
                        current_streak += 1
                    break
            if found:
                break
        if not found or not day_active:
            break
        check_dt -= timedelta(days=1)

    if close_conn:
        conn.close()

    return {
        "weeks": weeks_list,
        "total_contributions": total_contributions,
        "current_streak": current_streak,
        "months": month_labels,
        "end_date": today_str,
        "inception_date": aligned_start_str,
        "start_date": aligned_start_str,
    }


def get_upcoming_days(
    days_count: int = 7,
    start_date: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> List[Dict[str, Any]]:
    """
    Returns an upcoming forecast of the next `days_count` days starting from tomorrow.
    Resolves Schedule A/B/C, key cutoffs, gym protocols, and pre-scheduled tasks.
    """
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    base_dt = datetime.strptime(start_date, "%Y-%m-%d") if start_date else datetime.now()
    upcoming = []

    for i in range(1, days_count + 1):
        target_dt = base_dt + timedelta(days=i)
        date_str = target_dt.strftime("%Y-%m-%d")
        day_name = target_dt.strftime("%A")

        # Resolve pre-calibrated schedule
        sched = today_service.get_schedule_for_date(date_str)
        sched_name = sched.get("name", f"{day_name} Routine")
        sched_key = sched.get("key", "").replace("C_", "")
        sched_desc = sched.get("description", "")

        # Key highlight & cutoff directly matching routine
        key_highlight = "Standard Routine"
        cutoff_info = ""
        blocks = sched.get("blocks", [])
        if "Schedule A" in sched_name or "Boxing" in sched_name:
            key_highlight = "Boxing Day • Cutoff 17:20"
            cutoff_info = "Cutoff 17:20 (Transit & Sparring)"
        elif "Schedule B" in sched_name or "TUM Sprint" in sched_name or "Gym" in sched_name:
            key_highlight = "TUM Deep Work (2h) + Lift (50m)"
            cutoff_info = "16:15 – 18:15 TUM Deep Work"
        elif "Saturday" in sched_name or "Run" in sched_name:
            key_highlight = "5k Zone 2 Run + 2h TUM Exam Work"
            cutoff_info = "09:30 Run • 11:00 Exam • 13:00 Free"
        elif "Sunday" in sched_name or "Reset" in sched_name:
            key_highlight = "Complete CNS Reset (Zero Workouts)"
            cutoff_info = "18:00 Weekly Prep • 22:30 Lights Out"

        # Embedded gym routine for Tuesday / Thursday
        gym_routine = today_service.get_gym_routine_for_date(date_str)

        # Scheduled tasks
        scheduled_tasks = today_service.get_today_tasks(date_str, conn=conn)

        upcoming.append({
            "date": date_str,
            "day_name": day_name,
            "display_date": target_dt.strftime("%a, %b %d"),
            "is_tomorrow": (i == 1),
            "days_away": i,
            "schedule_key": sched_key,
            "schedule_name": sched_name,
            "schedule_desc": sched_desc,
            "key_highlight": key_highlight,
            "cutoff_info": cutoff_info,
            "blocks": blocks,
            "gym_routine": gym_routine,
            "task_count": len(scheduled_tasks),
            "tasks": scheduled_tasks,
        })

    if close_conn:
        conn.close()

    return upcoming


def get_dashboard_summary(conn: Optional[sqlite3.Connection] = None) -> Dict[str, Any]:
    """
    Gathers all executive home page metrics: Heatmap, 7-day forecast,
    TUM progress, Body targets, and Active Projects next actions.
    """
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    today_str = datetime.now().strftime("%Y-%m-%d")
    heatmap = get_heatmap_data(conn=conn)
    upcoming = get_upcoming_days(days_count=7, conn=conn)
    tum_overview = tum_service.get_tum_overview(conn=conn)
    metro = tum_service.get_metro_roadmap()
    body_summary = body_service.get_weekly_workout_summary(conn=conn)
    body_history = body_service.get_body_metrics_history(limit=7, conn=conn)
    projects = project_service.get_all_projects(conn=conn)

    # Today's execution metrics
    today_tasks = today_service.get_today_tasks(today_str, conn=conn)
    today_sched = today_service.get_schedule_for_date(today_str)
    today_log = today_service.get_daily_log(today_str, conn=conn)
    today_gym = today_service.get_gym_routine_for_date(today_str)

    total_today_tasks = len(today_tasks)
    completed_today_tasks = sum(1 for t in today_tasks if t.get("completed"))

    sched_blocks = today_sched.get("blocks", [])
    total_routine_blocks = len(sched_blocks)
    completed_blocks_set = set([b.strip() for b in (today_log.get("completed_blocks") or "").split(",") if b.strip()])
    completed_routine_blocks = len(completed_blocks_set)

    gym_exercises = today_gym.get("exercises", []) if today_gym else []
    total_gym_ex = len(gym_exercises)
    completed_ex_set = set([e.strip() for e in (today_log.get("completed_exercises") or "").split(",") if e.strip()])
    completed_gym_ex = len(completed_ex_set)

    total_today_boxes = total_routine_blocks + total_gym_ex + total_today_tasks
    checked_today_boxes = completed_routine_blocks + completed_gym_ex + completed_today_tasks
    today_pct = Math_round_pct = round((checked_today_boxes / total_today_boxes) * 100) if total_today_boxes > 0 else 0

    # Latest weight
    latest_weight = 68.0
    if body_history:
        latest_weight = body_history[-1]["weight_kg"]

    # Active station in TUM Metro
    active_station = None
    stations = metro.get("stations", [])
    for st in stations:
        if st.get("status") == "active":
            active_station = st
            break
    if not active_station and stations:
        active_station = stations[0]

    # German current level
    german_ladder = tum_overview.get("language", [])
    current_german = "A2 (In Progress)"
    for g in german_ladder:
        if g.get("status") == "in_progress":
            current_german = f"{g.get('level')} (Active)"
            break

    # Matura average percentage
    matura_list = tum_overview.get("matura", [])
    avg_mock = 0.0
    if matura_list:
        total_m = sum(m.get("current_mock_percentage", 0.0) for m in matura_list)
        avg_mock = round(total_m / len(matura_list), 1)

    # Homework & Exams
    from app.services import homework_service
    upcoming_homework = homework_service.get_upcoming_homework(conn=conn, limit=5)
    upcoming_exams = homework_service.get_upcoming_exams(conn=conn, limit=5)

    summary = {
        "heatmap": heatmap,
        "upcoming": upcoming,
        "today_velocity": {
            "total_boxes": total_today_boxes,
            "checked_boxes": checked_today_boxes,
            "percentage": today_pct,
            "schedule_name": today_sched.get("name", "Daily Routine"),
            "schedule_key": today_sched.get("key", "Standard"),
            "has_gym": bool(today_gym),
            "pending_tasks_count": total_today_tasks - completed_today_tasks,
        },
        "metrics": {
            "total_contributions": heatmap.get("total_contributions", 0),
            "current_streak": heatmap.get("current_streak", 0),
            "overall_gpa": tum_overview.get("overall_gpa", 0.0),
            "target_gpa": 5.0,
            "avg_matura_mock": avg_mock,
            "german_stage": current_german,
            "active_station": {
                "id": active_station.get("id") if active_station else "sep-2026",
                "name": active_station.get("name") if active_station else "Pure Syntax",
                "month": active_station.get("month_label") if active_station else "SEP '26",
                "phase": active_station.get("phase") if active_station else "Phase 1",
                "next_action": active_station.get("next_action") if active_station else "",
            },
            "latest_weight": latest_weight,
            "target_weight": 80.0,
            "weekly_workouts": {
                "boxing": {
                    "count": body_summary.get("boxing_count", 0),
                    "target": 3,
                },
                "gym": {
                    "count": body_summary.get("gym_count", 0),
                    "target": 4,
                },
                "running": {
                    "count": body_summary.get("running_count", 0),
                    "target": 2,
                },
            },
        },
        "tum": tum_overview,
        "body": {
            "summary": body_summary,
            "history": body_history,
        },
        "projects": [
            {
                "id": p["id"],
                "name": p["name"],
                "description": p.get("description", ""),
                "status": p["status"],
                "current_milestone": p["current_milestone"],
                "next_action": p["next_action"],
                "deadline": p["deadline"],
                "local_path": p.get("local_path", ""),
                "github_url": p.get("github_url", ""),
                "git": p.get("git", {}),
            }
            for p in projects
        ],
        "radar": {
            "homework": upcoming_homework,
            "exams": upcoming_exams,
        },
    }

    if close_conn:
        conn.close()

    return summary
