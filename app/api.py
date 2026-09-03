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


class HarnessAPI:
    """Methods exposed directly to the frontend window.pywebview.api."""

    def __init__(self):
        # Ensure database and tables are ready
        init_db()

    # --- Layer 0: DASHBOARD ---
    def get_dashboard(self) -> Dict[str, Any]:
        """Returns heatmap matrix, upcoming 7-day forecast, and executive KPI summary."""
        return dashboard_service.get_dashboard_summary()

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
        return homework_service.add_homework(subject, title, due_date, priority, notes, source)

    def toggle_homework(self, hw_id: int) -> Dict[str, Any]:
        from app.services import homework_service
        return homework_service.toggle_homework(hw_id)

    def delete_homework(self, hw_id: int) -> bool:
        from app.services import homework_service
        return homework_service.delete_homework(hw_id)

    def get_upcoming_exams(self) -> List[Dict[str, Any]]:
        from app.services import homework_service
        return homework_service.get_upcoming_exams()

    def add_exam(self, subject: str, title: str, exam_date: str, scope: str = "") -> Dict[str, Any]:
        from app.services import homework_service
        return homework_service.add_exam(subject, title, exam_date, scope)

    def toggle_exam(self, exam_id: int, result_percentage: Optional[float] = None) -> bool:
        from app.services import homework_service
        return homework_service.toggle_exam(exam_id, result_percentage)

    def delete_exam(self, exam_id: int) -> bool:
        from app.services import homework_service
        return homework_service.delete_exam(exam_id)

    def import_school_data(self, json_str: str) -> bool:
        from app.services import homework_service
        return homework_service.import_school_data_json(json_str)


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
        return today_service.add_task(title, category, is_tum, date_str)

    def toggle_task(self, task_id: int) -> Dict[str, Any]:
        return today_service.toggle_task(task_id)

    def delete_task(self, task_id: int) -> bool:
        return today_service.delete_task(task_id)

    def rollover_tasks(self, target_date_str: Optional[str] = None) -> int:
        return today_service.rollover_tasks(target_date_str)

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
        return today_service.update_daily_log(
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

    # --- Layer 2: TUM ---
    def get_tum_overview(self) -> Dict[str, Any]:
        return tum_service.get_tum_overview()

    def update_grade(
        self,
        grade_id: int,
        actual_grade: Optional[float],
        percentage: Optional[float] = None,
        notes: Optional[str] = None,
    ) -> bool:
        return tum_service.update_grade(grade_id, actual_grade, percentage, notes)

    def update_matura(self, matura_id: int, current_mock_percentage: float, notes: Optional[str] = None) -> bool:
        return tum_service.update_matura(matura_id, current_mock_percentage, notes)

    def update_language_status(self, level: str, status: str) -> bool:
        return tum_service.update_language_status(level, status)

    def get_metro_roadmap(self) -> Dict[str, Any]:
        return tum_service.get_metro_roadmap()

    def update_station_status(self, station_id: str, status: str) -> bool:
        return tum_service.update_station_status(station_id, status)

    def toggle_station_deliverable(self, station_id: str, deliverable_key: str) -> Dict[str, Any]:
        return tum_service.toggle_station_deliverable(station_id, deliverable_key)

    def get_all_configs(self) -> Dict[str, Any]:
        return tum_service.get_all_configs()

    def import_config(self, config_type: str, json_content: str) -> bool:
        return tum_service.import_config(config_type, json_content)

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
        return project_service.add_project(
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
        return project_service.update_project(
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

    def delete_project(self, project_id: int) -> bool:
        return project_service.delete_project(project_id)

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
        return body_service.log_body_metric(weight_kg, calories_met, protein_met, notes, date_str)

    def log_workout(
        self,
        workout_type: str,
        details: str,
        intensity: int = 7,
        date_str: Optional[str] = None,
    ) -> Dict[str, Any]:
        return body_service.log_workout(workout_type, details, intensity, date_str)

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
        return knowledge_service.save_knowledge_item(title, category, content, tags, item_id)

    def delete_knowledge_item(self, item_id: int) -> bool:
        return knowledge_service.delete_knowledge_item(item_id)
