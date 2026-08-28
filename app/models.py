"""Typed models and dataclasses for Harness entities."""

from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any


@dataclass
class Task:
    id: Optional[int]
    title: str
    category: str  # school, study, code, fitness, chore, personal
    is_tum: bool
    completed: bool
    date: str  # YYYY-MM-DD
    rollover_count: int
    created_at: Optional[str] = None
    completed_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DailyLog:
    date: str
    scratchpad: str
    wake_time: str
    sleep_time: str
    reflection_worked: str
    reflection_slipped: str
    reflection_tomorrow: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TumGrade:
    id: Optional[int]
    subject: str
    semester: int
    target_grade: float
    actual_grade: Optional[float]
    percentage: Optional[float]
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Project:
    id: Optional[int]
    name: str
    description: str
    status: str  # active, paused, completed
    local_path: Optional[str]
    github_url: Optional[str]
    current_milestone: str
    next_action: str
    deadline: Optional[str]
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BodyMetric:
    id: Optional[int]
    date: str
    weight_kg: float
    calories_met: bool
    protein_met: bool
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class KnowledgeItem:
    id: Optional[int]
    title: str
    category: str  # algorithm, mental_model, book, note
    content: str
    tags: str = ""
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
