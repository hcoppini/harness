"""Service for tracking active projects, milestones, next actions, and launching local workspaces."""

import os
import subprocess
import sqlite3
from typing import List, Dict, Any, Optional
from app.db import get_connection

SEED_PROJECTS = [
    {
        "name": "SIGG 2025/2026 (GPW Contest)",
        "description": "Annual inter-school trading competition on Warsaw Stock Exchange. Goal: GPW Trading Floor Finals.",
        "status": "active",
        "local_path": r"c:\Users\heito\Desktop\polish_stocks_day_trade-main",
        "github_url": "",
        "current_milestone": "Stage 1 Prep (WIG20, mWIG40, sWIG80 momentum scanner)",
        "next_action": "Run backtester on historical GPW data and refine risk/reward filters",
        "deadline": "2025-10-13 (Test Game) / 2025-11-17 (Stage 1 Start)",
        "notes": "Rules: Max 1 order / 10s. No bots during live execution. Top 12 to finals. Educational module bonus = +2 PLN per point.",
    },
    {
        "name": "Code Independence & Matura CS",
        "description": "Break AI dependency. Develop raw algorithmic problem solving for Matura Rozszerzona & software engineering.",
        "status": "active",
        "local_path": r"c:\Users\heito\Desktop\harness",
        "github_url": "",
        "current_milestone": "Algorithmic thinking & raw data structures (Python / C++)",
        "next_action": "Deconstruct and solve 2 HackerRank exercises unassisted; write algorithm in plain English first",
        "deadline": "Daily Repetition",
        "notes": "Crucial: Understand every line. If AI writes code, rewrite it from scratch with comments explaining memory & complexity.",
    },
    {
        "name": "Harness — Personal Life Hub",
        "description": "Personal desktop execution hub. 5 layers connecting daily action to TUM Heilbronn.",
        "status": "active",
        "local_path": r"c:\Users\heito\Desktop\harness",
        "github_url": "",
        "current_milestone": "V1 Desktop Hub Build & Testing",
        "next_action": "Package standalone Harness.exe and add to Windows Startup",
        "deadline": "2026-08-29",
        "notes": "Philosophy: Turn intention into execution without productivity bloat.",
    },
    {
        "name": "Financial Agency / Polish SME Outreach",
        "description": "Web dev and automation for Polish small businesses to hit 2,000 PLN/month financial independence.",
        "status": "active",
        "local_path": r"c:\Users\heito\Desktop\grodt_v1",
        "github_url": "",
        "current_milestone": "Outreach pipeline revamp",
        "next_action": "Audit scraped business list and refine high-converting offer script",
        "deadline": "2,000 PLN / month target",
        "notes": "Persistence over perfection. Focus on 10 high-signal calls instead of burning out on 1,000 cold leads.",
    },
]


def seed_projects_if_empty(conn: sqlite3.Connection) -> None:
    """Seeds default projects into the database if table is empty."""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as cnt FROM projects")
    if cursor.fetchone()["cnt"] == 0:
        for p in SEED_PROJECTS:
            cursor.execute(
                """
                INSERT INTO projects (name, description, status, local_path, github_url, current_milestone, next_action, deadline, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    p["name"],
                    p["description"],
                    p["status"],
                    p["local_path"],
                    p["github_url"],
                    p["current_milestone"],
                    p["next_action"],
                    p["deadline"],
                    p["notes"],
                ),
            )
        conn.commit()


def get_all_projects(conn: Optional[sqlite3.Connection] = None, include_git: bool = True) -> List[Dict[str, Any]]:
    """Returns all projects, optionally enriched with live git repository status."""
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    seed_projects_if_empty(conn)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM projects ORDER BY status ASC, id ASC")
    rows = cursor.fetchall()

    from app.services import github_service

    projects = []
    for r in rows:
        local_path = r["local_path"] or ""
        git_info = {}
        if include_git and local_path:
            try:
                git_info = github_service.get_repo_git_status(local_path)
            except Exception:
                pass

        projects.append({
            "id": r["id"],
            "name": r["name"],
            "description": r["description"] or "",
            "status": r["status"],
            "local_path": local_path,
            "github_url": r["github_url"] or "",
            "current_milestone": r["current_milestone"] or "",
            "next_action": r["next_action"] or "",
            "deadline": r["deadline"] or "",
            "notes": r["notes"] or "",
            "git": git_info,
        })

    if close_conn:
        conn.close()

    return projects


def update_project(
    project_id: int,
    status: Optional[str] = None,
    current_milestone: Optional[str] = None,
    next_action: Optional[str] = None,
    deadline: Optional[str] = None,
    notes: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> bool:
    """Updates fields for a specific project."""
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE projects
        SET status = COALESCE(?, status),
            current_milestone = COALESCE(?, current_milestone),
            next_action = COALESCE(?, next_action),
            deadline = COALESCE(?, deadline),
            notes = COALESCE(?, notes)
        WHERE id = ?
        """,
        (status, current_milestone, next_action, deadline, notes, project_id),
    )
    conn.commit()
    updated = cursor.rowcount > 0

    if close_conn:
        conn.close()

    return updated


def add_project(
    name: str,
    description: str,
    local_path: str = "",
    github_url: str = "",
    current_milestone: str = "",
    next_action: str = "",
    deadline: str = "",
    notes: str = "",
    conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, Any]:
    """Adds a new project to the registry."""
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO projects (name, description, status, local_path, github_url, current_milestone, next_action, deadline, notes)
        VALUES (?, ?, 'active', ?, ?, ?, ?, ?, ?)
        """,
        (name.strip(), description.strip(), local_path, github_url, current_milestone, next_action, deadline, notes),
    )
    new_id = cursor.lastrowid
    conn.commit()

    if close_conn:
        conn.close()

    return {
        "id": new_id,
        "name": name,
        "description": description,
        "status": "active",
        "local_path": local_path,
        "github_url": github_url,
        "current_milestone": current_milestone,
        "next_action": next_action,
        "deadline": deadline,
        "notes": notes,
    }


def validate_launch_path(path_str: str) -> bool:
    """Validates that a local folder exists and is a valid directory."""
    if not path_str or not isinstance(path_str, str):
        return False
    return os.path.exists(path_str) and os.path.isdir(path_str)


def open_local_path(path_str: str) -> bool:
    """Opens a file path or directory in Windows File Explorer."""
    if not validate_launch_path(path_str):
        return False
    try:
        os.startfile(path_str)
        return True
    except Exception:
        try:
            subprocess.run(["explorer", os.path.normpath(path_str)], check=False)
            return True
        except Exception:
            return False


def open_in_vscode(path_str: str) -> bool:
    """Launches VS Code in the specified directory."""
    if not validate_launch_path(path_str):
        return False
    try:
        subprocess.Popen(["code", os.path.normpath(path_str)], shell=True)
        return True
    except Exception:
        return False


def open_terminal(path_str: str) -> bool:
    """Opens PowerShell or Windows Terminal in the specified directory."""
    if not validate_launch_path(path_str):
        return False
    norm_path = os.path.normpath(path_str)
    # Attempt to open Windows Terminal if available, otherwise launch PowerShell
    try:
        subprocess.Popen(["wt", "-d", norm_path], shell=True)
        return True
    except Exception:
        pass

    try:
        subprocess.Popen(["start", "powershell", "-NoExit", "-Command", f"Set-Location -LiteralPath '{norm_path}'"], shell=True)
        return True
    except Exception:
        return False

