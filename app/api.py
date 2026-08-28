"""Direct Python-to-JavaScript bridge API for PyWebView."""

from typing import Dict, Any, List, Optional
from app.db import init_db
from app.services import (
    today_service,
    tum_service,
    project_service,
    body_service,
    knowledge_service,
)


class HarnessAPI:
    """Methods exposed directly to the frontend window.pywebview.api."""

    def __init__(self):
        # Ensure database and tables are ready
        init_db()

    # --- Layer 1: TODAY ---
    def get_today(self, date_str: Optional[str] = None) -> Dict[str, Any]:
        """Returns today's tasks, daily log (scratchpad/sleep), and rollover status."""
        tasks = today_service.get_today_tasks(date_str)
        log = today_service.get_daily_log(date_str)
        return {
            "tasks": tasks,
            "log": log,
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
    ) -> Dict[str, Any]:
        return today_service.update_daily_log(
            date_str=date_str,
            scratchpad=scratchpad,
            wake_time=wake_time,
            sleep_time=sleep_time,
            reflection_worked=reflection_worked,
            reflection_slipped=reflection_slipped,
            reflection_tomorrow=reflection_tomorrow,
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
        )

    def update_project(
        self,
        project_id: int,
        status: Optional[str] = None,
        current_milestone: Optional[str] = None,
        next_action: Optional[str] = None,
        deadline: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> bool:
        return project_service.update_project(
            project_id=project_id,
            status=status,
            current_milestone=current_milestone,
            next_action=next_action,
            deadline=deadline,
            notes=notes,
        )

    def open_project_folder(self, local_path: str) -> bool:
        return project_service.open_local_path(local_path)

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
