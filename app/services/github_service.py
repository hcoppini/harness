"""Service for extracting local Git and GitHub repository commit metrics and workspace statuses."""

import os
import sys
import subprocess
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

# Prevent console flashing/tab opening on Windows
CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0

# Cache for local git queries to ensure snappy UI responsiveness
_GIT_CACHE: Dict[str, Any] = {}
_GIT_CACHE_TIMESTAMP: Optional[datetime] = None
CACHE_TTL_SECONDS = 30


def get_repo_git_status(local_path: str) -> Dict[str, Any]:
    """Inspects a local folder and extracts branch, commit count, last commit, and uncommitted status."""
    result = {
        "is_git": False,
        "path": local_path,
        "branch": "",
        "commit_count": 0,
        "last_commit": "",
        "last_commit_hash": "",
        "last_commit_date": "",
        "uncommitted_changes": 0,
        "recent_commits": [],
    }

    if not local_path or not os.path.exists(local_path) or not os.path.isdir(local_path):
        return result

    # Check for .git directory or file (worktree/submodule)
    git_dir = os.path.join(local_path, ".git")
    if not os.path.exists(git_dir):
        return result

    result["is_git"] = True

    # 1. Get branch
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=local_path,
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
            creationflags=CREATE_NO_WINDOW,
        )
        if proc.returncode == 0:
            result["branch"] = proc.stdout.strip()
    except Exception:
        pass

    # 2. Get total commit count
    try:
        proc = subprocess.run(
            ["git", "rev-list", "--count", "HEAD"],
            cwd=local_path,
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
            creationflags=CREATE_NO_WINDOW,
        )
        if proc.returncode == 0 and proc.stdout.strip().isdigit():
            result["commit_count"] = int(proc.stdout.strip())
    except Exception:
        pass

    # 3. Get uncommitted changes count
    try:
        proc = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=local_path,
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
            creationflags=CREATE_NO_WINDOW,
        )
        if proc.returncode == 0:
            lines = [l for l in proc.stdout.strip().split("\n") if l.strip()]
            result["uncommitted_changes"] = len(lines)
    except Exception:
        pass

    # 4. Get last commit details & recent commits
    if result["commit_count"] > 0:
        try:
            proc = subprocess.run(
                ["git", "log", "-5", "--format=%h|%an|%ad|%s", "--date=short"],
                cwd=local_path,
                capture_output=True,
                text=True,
                timeout=3,
                check=False,
                creationflags=CREATE_NO_WINDOW,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                commits = []
                for line in proc.stdout.strip().split("\n"):
                    parts = line.split("|", 3)
                    if len(parts) == 4:
                        commits.append({
                            "hash": parts[0],
                            "author": parts[1],
                            "date": parts[2],
                            "message": parts[3],
                        })
                result["recent_commits"] = commits
                if commits:
                    result["last_commit"] = f"{commits[0]['hash']} - {commits[0]['message']}"
                    result["last_commit_hash"] = commits[0]["hash"]
                    result["last_commit_date"] = commits[0]["date"]
        except Exception:
            pass

    return result


def get_daily_commits_map(
    repo_paths: Optional[List[str]] = None,
    days_back: int = 365,
) -> Dict[str, Dict[str, Any]]:
    """
    Scans specified git repositories and aggregates commits grouped by date (YYYY-MM-DD).
    Returns a dictionary: { "2026-08-30": { "count": 5, "commits": [...] } }
    """
    if repo_paths is None:
        # Default to standard project locations
        desktop = Path.home() / "Desktop"
        candidate_dirs = [
            str(desktop / "harness"),
            str(desktop / "Chekr"),
            str(desktop / "grodt_v1"),
            str(desktop / "polish_stocks_day_trade-main"),
            str(desktop / "SIGG-main"),
        ]
        repo_paths = [d for d in candidate_dirs if os.path.exists(d)]

    daily_map: Dict[str, Dict[str, Any]] = {}

    for path_str in repo_paths:
        if not path_str or not os.path.exists(path_str):
            continue

        repo_name = os.path.basename(path_str.rstrip("\\/"))

        try:
            proc = subprocess.run(
                ["git", "log", "--format=%h|%ad|%s", "--date=short"],
                cwd=path_str,
                capture_output=True,
                text=True,
                timeout=4,
                check=False,
                creationflags=CREATE_NO_WINDOW,
            )
            if proc.returncode != 0 or not proc.stdout.strip():
                continue

            for line in proc.stdout.strip().split("\n"):
                parts = line.split("|", 2)
                if len(parts) == 3:
                    commit_hash, date_str, msg = parts[0], parts[1], parts[2]
                    daily_map.setdefault(date_str, {"count": 0, "commits": []})
                    daily_map[date_str]["count"] += 1
                    daily_map[date_str]["commits"].append({
                        "repo": repo_name,
                        "hash": commit_hash,
                        "message": msg,
                        "date": date_str,
                    })
        except Exception:
            continue

    return daily_map


def get_all_active_repos_summary(repo_paths: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Gathers live git status for all provided repository paths."""
    if repo_paths is None:
        desktop = Path.home() / "Desktop"
        candidate_dirs = [
            str(desktop / "harness"),
            str(desktop / "Chekr"),
            str(desktop / "grodt_v1"),
            str(desktop / "polish_stocks_day_trade-main"),
            str(desktop / "SIGG-main"),
            str(desktop / "Ginder"),
        ]
        repo_paths = [d for d in candidate_dirs if os.path.exists(d)]

    summaries = []
    for path_str in repo_paths:
        status = get_repo_git_status(path_str)
        repo_name = os.path.basename(path_str.rstrip("\\/"))
        summaries.append({
            "name": repo_name,
            "path": path_str,
            "is_git": status["is_git"],
            "branch": status["branch"],
            "commit_count": status["commit_count"],
            "uncommitted_changes": status["uncommitted_changes"],
            "last_commit": status["last_commit"],
            "last_commit_date": status["last_commit_date"],
            "recent_commits": status["recent_commits"],
        })

    return summaries
