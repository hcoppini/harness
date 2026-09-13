"""Direct Python-to-JavaScript bridge API for PyWebView."""

from typing import Dict, Any, List, Optional
from app.db import init_db
from app.services import (
    dashboard_service,
    today_service,
    tum_service,
    project_service,
    body_service,
    knowledge_service,
    school_service,
)
from engine import kill_list_controller, tum_calculator


class HarnessAPI:
    """Methods exposed directly to the frontend window.pywebview.api."""

    def __init__(self):
        # Ensure database and tables are ready
        init_db()
        self._last_sync_trigger = 0.0

    def _trigger_auto_sync(self):
        """Asynchronously triggers two-way sync if auto_sync is enabled and configured."""
        import time
        import threading
        now = time.time()
        if now - self._last_sync_trigger < 1.0:
            return
        self._last_sync_trigger = now

        def _worker():
            try:
                from app.services import sync_service
                cfg = sync_service.get_sync_config()
                if cfg.get("auto_sync", True) and (cfg.get("web_url") or cfg.get("supabase_key")):
                    sync_service.sync_all()
            except Exception:
                pass

        threading.Thread(target=_worker, daemon=True).start()

    # --- Layer 0: DASHBOARD ---
    def get_dashboard(self, client_date: Optional[str] = None) -> Dict[str, Any]:
        """Returns heatmap matrix, upcoming 7-day forecast, and executive KPI summary."""
        return dashboard_service.get_dashboard_summary(client_date=client_date)

    # --- School, Homework & Quick Links ---
    def get_school_plan(self, date_str: Optional[str] = None, force_refresh: bool = False) -> Dict[str, Any]:
        """Returns today's school schedule from TM1 / staff.edu.pl."""
        if force_refresh:
            school_service.fetch_school_plan(force_refresh=True)
        lessons = school_service.get_lessons_for_date(date_str)
        return {"lessons": lessons, "date": date_str}

    def get_easy_links(self) -> List[Dict[str, Any]]:
        """Returns curated high-signal links."""
        return school_service.get_easy_links()

    def add_easy_link(self, name: str, url: str, category: str = "custom", desc: str = "") -> Dict[str, Any]:
        """Adds a new quick link."""
        return school_service.add_easy_link(name, url, category, desc)

    def update_easy_link(self, index: int, name: str, url: str, category: str = "custom", desc: str = "") -> bool:
        """Updates an existing quick link."""
        return school_service.update_easy_link(index, name, url, category, desc)

    def delete_easy_link(self, index: int) -> bool:
        """Deletes a quick link by index."""
        return school_service.delete_easy_link(index)

    def open_external_url(self, url: str) -> bool:
        """Opens safe HTTP/HTTPS URL in default Windows browser."""
        return school_service.open_external_url(url)

    def get_upcoming_homework(self) -> List[Dict[str, Any]]:
        from app.services import homework_service
        return homework_service.get_upcoming_homework()

    def get_homework_for_date(self, date_str: Optional[str] = None) -> List[Dict[str, Any]]:
        from app.services import homework_service
        return homework_service.get_homework_for_date(date_str)

    def add_homework(
        self,
        subject: str,
        title: str,
        due_date: str,
        priority: int = 1,
        notes: str = "",
        source: str = "manual",
    ) -> Dict[str, Any]:
        from app.services import homework_service
        res = homework_service.add_homework(subject, title, due_date, priority, notes, source)
        self._trigger_auto_sync()
        return res

    def toggle_homework(self, hw_id: int) -> Dict[str, Any]:
        from app.services import homework_service
        res = homework_service.toggle_homework(hw_id)
        self._trigger_auto_sync()
        return res

    def delete_homework(self, hw_id: int) -> bool:
        from app.services import homework_service
        res = homework_service.delete_homework(hw_id)
        self._trigger_auto_sync()
        return res

    def get_upcoming_exams(self) -> List[Dict[str, Any]]:
        from app.services import homework_service
        return homework_service.get_upcoming_exams()

    def add_exam(self, subject: str, title: str, exam_date: str, scope: str = "") -> Dict[str, Any]:
        from app.services import homework_service
        res = homework_service.add_exam(subject, title, exam_date, scope)
        self._trigger_auto_sync()
        return res

    def toggle_exam(self, exam_id: int, result_percentage: Optional[float] = None) -> bool:
        from app.services import homework_service
        res = homework_service.toggle_exam(exam_id, result_percentage)
        self._trigger_auto_sync()
        return res

    def delete_exam(self, exam_id: int) -> bool:
        from app.services import homework_service
        res = homework_service.delete_exam(exam_id)
        self._trigger_auto_sync()
        return res

    def import_school_data(self, json_str: str) -> bool:
        from app.services import homework_service
        res = homework_service.import_school_data_json(json_str)
        self._trigger_auto_sync()
        return res


    # --- Layer 1: TODAY ---
    def get_today(self, date_str: Optional[str] = None) -> Dict[str, Any]:
        """Returns today's tasks, daily log, auto-resolved schedule (A/B/C), and gym routine."""
        tasks = today_service.get_today_tasks(date_str)
        log = today_service.get_daily_log(date_str)
        schedule = today_service.get_schedule_for_date(date_str)
        gym_routine = today_service.get_gym_routine_for_date(date_str)
        return {
            "tasks": tasks,
            "log": log,
            "schedule": schedule,
            "gym_routine": gym_routine,
        }

    def add_task(self, title: str, category: str = "personal", is_tum: bool = False, date_str: Optional[str] = None) -> Dict[str, Any]:
        res = today_service.add_task(title, category, is_tum, date_str)
        self._trigger_auto_sync()
        return res

    def toggle_task(self, task_id: int) -> Dict[str, Any]:
        res = today_service.toggle_task(task_id)
        self._trigger_auto_sync()
        return res

    def delete_task(self, task_id: int) -> bool:
        res = today_service.delete_task(task_id)
        self._trigger_auto_sync()
        return res

    def rollover_tasks(self, target_date_str: Optional[str] = None) -> int:
        res = today_service.rollover_tasks(target_date_str)
        self._trigger_auto_sync()
        return res

    def update_daily_log(
        self,
        date_str: Optional[str] = None,
        scratchpad: Optional[str] = None,
        wake_time: Optional[str] = None,
        sleep_time: Optional[str] = None,
        reflection_worked: Optional[str] = None,
        reflection_slipped: Optional[str] = None,
        reflection_tomorrow: Optional[str] = None,
        completed_blocks: Optional[str] = None,
        completed_exercises: Optional[str] = None,
    ) -> Dict[str, Any]:
        res = today_service.update_daily_log(
            date_str=date_str,
            scratchpad=scratchpad,
            wake_time=wake_time,
            sleep_time=sleep_time,
            reflection_worked=reflection_worked,
            reflection_slipped=reflection_slipped,
            reflection_tomorrow=reflection_tomorrow,
            completed_blocks=completed_blocks,
            completed_exercises=completed_exercises,
        )
        self._trigger_auto_sync()
        return res

    # --- Kill List Drawer & Execution Engine (Harness 2.1) ---
    def get_kill_list(self, date_str: Optional[str] = None) -> Dict[str, Any]:
        """Returns Kill List items for library session, enforcing 3-Item Rule & Evening Lock."""
        return kill_list_controller.get_kill_list(date_str)

    def add_kill_item(
        self,
        category: str,
        title: str,
        action_type: str,
        target_path: str,
        target_spec: str = "",
        station_deliverable_id: Optional[str] = None,
        quantity: int = 1,
        date_str: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Adds an item to the Kill List (max 3 items per session)."""
        res = kill_list_controller.add_kill_item(
            category=category,
            title=title,
            action_type=action_type,
            target_path=target_path,
            target_spec=target_spec,
            station_deliverable_id=station_deliverable_id,
            quantity=quantity,
            date_str=date_str,
        )
        self._trigger_auto_sync()
        return res

    def complete_kill_item(self, item_id: str) -> Dict[str, Any]:
        """Marks kill item done and atomically increments connected station deliverable."""
        res = kill_list_controller.complete_kill_item(item_id)
        self._trigger_auto_sync()
        return res

    def toggle_kill_item(self, item_id: str) -> Dict[str, Any]:
        """Toggles kill item done status and syncs station deliverable counter."""
        res = kill_list_controller.toggle_kill_item(item_id)
        self._trigger_auto_sync()
        return res

    def delete_kill_item(self, item_id: str) -> bool:
        """Deletes a kill item from the daily list."""
        res = kill_list_controller.delete_kill_item(item_id)
        self._trigger_auto_sync()
        return res

    def launch_kill_item(self, action_type: str, target_path: str) -> Dict[str, Any]:
        """Directly triggers native OS / browser launcher for PDF, URL, or VS Code workspace."""
        return kill_list_controller.launch_kill_item(action_type, target_path)

    def update_deliverable_progress(
        self, deliverable_id: str, new_count: Optional[int] = None, delta: Optional[int] = None
    ) -> Dict[str, Any]:
        """Directly sets or adjusts countable progress on a Metro deliverable."""
        res = kill_list_controller.update_deliverable_progress(deliverable_id, new_count=new_count, delta=delta)
        self._trigger_auto_sync()
        return res

    def log_study_reps(self, deliverable_id: str, count: int, notes: str = "") -> Dict[str, Any]:
        """Registers positive study volume (e.g. 20 German words or 3 LeetCode problems)."""
        res = kill_list_controller.log_study_reps(deliverable_id, count=count, notes=notes)
        self._trigger_auto_sync()
        return res

    # --- Layer 2: TUM & Metro ---
    def get_tum_overview(self) -> Dict[str, Any]:
        return tum_service.get_tum_overview()

    def add_grade_entry(
        self,
        subject: str,
        semester: int,
        raw_input: str,
        weight: float = 1.0,
        category: str = "Grade",
        description: str = "",
        date_str: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Logs an individual grade (supports 4+, 17/17, 85%, np, bz), recalculating subject average instantly."""
        res = tum_service.add_grade_entry(
            subject=subject,
            semester=semester,
            raw_input=raw_input,
            weight=weight,
            category=category,
            description=description,
            date_str=date_str,
        )
        self._trigger_auto_sync()
        return res

    def delete_grade_entry(self, entry_id: int) -> bool:
        """Removes a grade entry and updates running average."""
        res = tum_service.delete_grade_entry(entry_id)
        self._trigger_auto_sync()
        return res

    def get_grade_entries(
        self, subject: Optional[str] = None, semester: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Returns all grade entries, optionally filtered."""
        return tum_service.get_grade_entries(subject=subject, semester=semester)

    def calculate_tum_aptitude(
        self, gpa_pl: float, math_pl: float, cs_pl: float, lang_pl: float
    ) -> Dict[str, Any]:
        """Computes TUM Stage 1 Aptitude Assessment (0-100 pts) using Bavarian Formula."""
        return tum_calculator.calculate_tum_aptitude_score(gpa_pl, math_pl, cs_pl, lang_pl)

    def get_station_deliverables(self, station_id: str = "sep-2026") -> List[Dict[str, Any]]:
        """Returns deliverables with counter progress for active station."""
        return kill_list_controller.get_station_deliverables(station_id)

    def get_station_pace_velocity(
        self, station_id: str = "sep-2026", date_str: Optional[str] = None
    ) -> Dict[str, Any]:
        """Station Velocity Indicator (Ghost Beacon) calculating Pace Deficit or Optimal Velocity."""
        return kill_list_controller.get_station_pace_velocity(station_id, date_str)

    def update_grade(
        self,
        grade_id: int,
        actual_grade: Optional[float],
        percentage: Optional[float] = None,
        notes: Optional[str] = None,
    ) -> bool:
        res = tum_service.update_grade(grade_id, actual_grade, percentage, notes)
        self._trigger_auto_sync()
        return res

    def update_matura(self, matura_id: int, current_mock_percentage: float, notes: Optional[str] = None) -> bool:
        res = tum_service.update_matura(matura_id, current_mock_percentage, notes)
        self._trigger_auto_sync()
        return res

    def update_language_status(self, level: str, status: str) -> bool:
        res = tum_service.update_language_status(level, status)
        self._trigger_auto_sync()
        return res

    def get_metro_roadmap(self) -> Dict[str, Any]:
        return tum_service.get_metro_roadmap()

    def update_station_status(self, station_id: str, status: str) -> bool:
        res = tum_service.update_station_status(station_id, status)
        self._trigger_auto_sync()
        return res

    def toggle_station_deliverable(self, station_id: str, deliverable_key: str) -> Dict[str, Any]:
        res = tum_service.toggle_station_deliverable(station_id, deliverable_key)
        self._trigger_auto_sync()
        return res

    def get_all_configs(self) -> Dict[str, Any]:
        return tum_service.get_all_configs()

    def import_config(self, config_type: str, json_content: str) -> bool:
        res = tum_service.import_config(config_type, json_content)
        self._trigger_auto_sync()
        return res

    # --- Layer 3: PROJECTS ---
    def get_projects(self) -> List[Dict[str, Any]]:
        return project_service.get_all_projects()

    def add_project(
        self,
        name: str,
        description: str,
        local_path: str = "",
        github_url: str = "",
        current_milestone: str = "",
        next_action: str = "",
        deadline: str = "",
        notes: str = "",
        status: str = "active",
    ) -> Dict[str, Any]:
        res = project_service.add_project(
            name=name,
            description=description,
            local_path=local_path,
            github_url=github_url,
            current_milestone=current_milestone,
            next_action=next_action,
            deadline=deadline,
            notes=notes,
            status=status,
        )
        self._trigger_auto_sync()
        return res

    def update_project(
        self,
        project_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None,
        current_milestone: Optional[str] = None,
        next_action: Optional[str] = None,
        deadline: Optional[str] = None,
        local_path: Optional[str] = None,
        github_url: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> bool:
        res = project_service.update_project(
            project_id=project_id,
            name=name,
            description=description,
            status=status,
            current_milestone=current_milestone,
            next_action=next_action,
            deadline=deadline,
            local_path=local_path,
            github_url=github_url,
            notes=notes,
        )
        self._trigger_auto_sync()
        return res

    def delete_project(self, project_id: int) -> bool:
        res = project_service.delete_project(project_id)
        self._trigger_auto_sync()
        return res

    def open_project_folder(self, local_path: str) -> bool:
        return project_service.open_local_path(local_path)

    def open_in_vscode(self, local_path: str) -> bool:
        return project_service.open_in_vscode(local_path)

    def open_terminal(self, local_path: str) -> bool:
        return project_service.open_terminal(local_path)

    def get_git_repos_summary(self) -> List[Dict[str, Any]]:
        from app.services import github_service
        return github_service.get_all_active_repos_summary()

    # --- Layer 4: BODY / LIFE ---
    def get_body_summary(self) -> Dict[str, Any]:
        return body_service.get_weekly_workout_summary()

    def get_body_history(self, limit: int = 30) -> List[Dict[str, Any]]:
        return body_service.get_body_metrics_history(limit)

    def log_body_metric(
        self,
        weight_kg: float,
        calories_met: bool = False,
        protein_met: bool = False,
        notes: str = "",
        date_str: Optional[str] = None,
    ) -> Dict[str, Any]:
        res = body_service.log_body_metric(weight_kg, calories_met, protein_met, notes, date_str)
        self._trigger_auto_sync()
        return res

    def log_workout(
        self,
        workout_type: str,
        details: str,
        intensity: int = 7,
        date_str: Optional[str] = None,
    ) -> Dict[str, Any]:
        res = body_service.log_workout(workout_type, details, intensity, date_str)
        self._trigger_auto_sync()
        return res

    # --- Layer 5: KNOWLEDGE ---
    def get_knowledge(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        return knowledge_service.get_all_knowledge(category)

    def save_knowledge_item(
        self,
        title: str,
        category: str,
        content: str,
        tags: str = "",
        item_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        res = knowledge_service.save_knowledge_item(title, category, content, tags, item_id)
        self._trigger_auto_sync()
        return res

    def delete_knowledge_item(self, item_id: int) -> bool:
        res = knowledge_service.delete_knowledge_item(item_id)
        self._trigger_auto_sync()
        return res

    # --- Cross-Device Cloud & Web Sync ---
    def sync_now(self) -> Dict[str, Any]:
        from app.services import sync_service
        return sync_service.sync_all()

    def get_sync_status(self) -> Dict[str, Any]:
        from app.services import sync_service
        cfg = sync_service.get_sync_config()
        has_key = bool(cfg.get("supabase_key"))
        has_web = bool(cfg.get("web_url"))
        local_detected = sync_service.probe_local_server() if not has_web else None
        configured = has_key or has_web or bool(local_detected)
        status = "synced" if cfg.get("last_synced_at") else ("ready" if configured else "unconfigured")
        return {
            "status": status,
            "supabase_url": cfg.get("supabase_url", ""),
            "has_key": has_key,
            "web_url": cfg.get("web_url", ""),
            "has_web_url": has_web,
            "local_detected_url": local_detected or "",
            "last_synced_at": cfg.get("last_synced_at"),
            "auto_sync": cfg.get("auto_sync", True),
        }

    def save_sync_settings(
        self,
        web_url: str = "",
        supabase_key: str = "",
        supabase_url: Optional[str] = None,
        auto_sync: bool = True,
    ) -> Dict[str, Any]:
        """Saves Web URL and Supabase credentials in a single call."""
        from app.services import sync_service
        cfg = sync_service.get_sync_config()
        if web_url is not None:
            clean_web = web_url.strip()
            if clean_web and not clean_web.startswith("http://") and not clean_web.startswith("https://"):
                clean_web = f"http://{clean_web}"
            cfg["web_url"] = clean_web.rstrip("/")
        if supabase_key is not None:
            cfg["supabase_key"] = supabase_key.strip()
        if supabase_url:
            cfg["supabase_url"] = supabase_url.strip().rstrip("/")
        cfg["auto_sync"] = bool(auto_sync)
        sync_service.save_sync_config(cfg)
        return self.get_sync_status()

    def configure_sync(self, supabase_url: str, supabase_key: str, auto_sync: bool = True) -> bool:
        from app.services import sync_service
        cfg = sync_service.get_sync_config()
        cfg["supabase_url"] = supabase_url.strip()
        cfg["supabase_key"] = supabase_key.strip()
        cfg["auto_sync"] = auto_sync
        sync_service.save_sync_config(cfg)
        return True

    def configure_web_sync(self, web_url: str, auto_sync: bool = True) -> bool:
        from app.services import sync_service
        cfg = sync_service.get_sync_config()
        cfg["web_url"] = web_url.strip().rstrip("/")
        cfg["auto_sync"] = auto_sync
        sync_service.save_sync_config(cfg)
        return True

    # --- Harness 3.0: Vulcan UONET+ & Adaptive Workload Governor ---
    def get_workload_analysis(self, target_date: Optional[str] = None) -> Dict[str, Any]:
        from engine import workload_governor
        return workload_governor.get_workload_analysis(target_date)

    def get_recommended_kill_items(self, date_str: Optional[str] = None) -> List[Dict[str, Any]]:
        from engine import workload_governor
        return workload_governor.get_recommended_kill_items(date_str)

    def enqueue_progressive_deliverable(self, deliverable_id: str, date_str: Optional[str] = None) -> Dict[str, Any]:
        from engine import kill_list_controller
        res = kill_list_controller.enqueue_progressive_deliverable(deliverable_id, date_str)
        self._trigger_auto_sync()
        return res

    def enqueue_exam_prep(self, exam_id: int, date_str: Optional[str] = None) -> Dict[str, Any]:
        from engine import kill_list_controller
        res = kill_list_controller.enqueue_exam_prep(exam_id, date_str)
        self._trigger_auto_sync()
        return res

    def sync_vulcan_data(self, client_date: Optional[str] = None, force_refresh: bool = False) -> Dict[str, Any]:
        from app.services import vulcan_service
        res = vulcan_service.sync_vulcan_data(client_date, force_refresh)
        self._trigger_auto_sync()
        return res

    def get_vulcan_config(self) -> Dict[str, Any]:
        from app.services import vulcan_service
        return vulcan_service.get_vulcan_config()

    def save_vulcan_config(self, config: Dict[str, Any]) -> bool:
        from app.services import vulcan_service
        return vulcan_service.save_vulcan_config(config)

    def register_eduvulcan(self, token_input: str) -> Dict[str, Any]:
        from app.services import vulcan_service
        res = vulcan_service.register_eduvulcan_device(token_input)
        self._trigger_auto_sync()
        return res

    def get_vulcan_status(self) -> Dict[str, Any]:
        from app.services import vulcan_service
        return vulcan_service.get_vulcan_status()

    def disconnect_vulcan(self) -> bool:
        from app.services import vulcan_service
        res = vulcan_service.disconnect_vulcan()
        self._trigger_auto_sync()
        return res

    def add_manual_exam(self, subject: str, title: str, exam_date: str, scope: str = "", weight: int = 2) -> Dict[str, Any]:
        from app.services import vulcan_service
        res = vulcan_service.add_manual_exam(subject, title, exam_date, scope, weight)
        self._trigger_auto_sync()
        return res

