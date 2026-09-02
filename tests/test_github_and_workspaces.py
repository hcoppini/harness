"""Unit tests for GitHub & Dev Workspaces service."""

import os
import subprocess
import pytest
from app.services import github_service, project_service


def test_git_status_on_valid_repo(tmp_path):
    # Initialize a temporary git repo
    repo_dir = tmp_path / "dummy_repo"
    repo_dir.mkdir()
    subprocess.run(["git", "init"], cwd=str(repo_dir), check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=str(repo_dir), check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=str(repo_dir), check=True, capture_output=True)

    # Initial status (no commits yet)
    status_empty = github_service.get_repo_git_status(str(repo_dir))
    assert status_empty["is_git"] is True
    assert status_empty["commit_count"] == 0

    # Create a commit
    test_file = repo_dir / "README.md"
    test_file.write_text("# Test Repo\n")
    subprocess.run(["git", "add", "README.md"], cwd=str(repo_dir), check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "feat: initial commit"], cwd=str(repo_dir), check=True, capture_output=True)

    # Test status after commit
    status = github_service.get_repo_git_status(str(repo_dir))
    assert status["is_git"] is True
    assert status["branch"] in ["master", "main"]
    assert status["commit_count"] == 1
    assert "initial commit" in status["last_commit"]
    assert status["uncommitted_changes"] == 0


def test_git_status_on_non_git_directory(tmp_path):
    non_git = tmp_path / "not_a_repo"
    non_git.mkdir()
    status = github_service.get_repo_git_status(str(non_git))
    assert status["is_git"] is False
    assert status["branch"] == ""
    assert status["commit_count"] == 0


def test_git_status_on_nonexistent_directory():
    status = github_service.get_repo_git_status("C:\\non_existent_folder_xyz_123")
    assert status["is_git"] is False
    assert status["branch"] == ""


def test_daily_commits_aggregation(tmp_path):
    repo_dir = tmp_path / "commit_repo"
    repo_dir.mkdir()
    subprocess.run(["git", "init"], cwd=str(repo_dir), check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=str(repo_dir), check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=str(repo_dir), check=True, capture_output=True)

    test_file = repo_dir / "code.py"
    test_file.write_text("print('hello')\n")
    subprocess.run(["git", "add", "."], cwd=str(repo_dir), check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "feat: add code.py"], cwd=str(repo_dir), check=True, capture_output=True)

    daily_map = github_service.get_daily_commits_map([str(repo_dir)])
    assert len(daily_map) >= 1
    total_commits = sum(item["count"] for item in daily_map.values())
    assert total_commits >= 1


def test_ide_launch_path_validation():
    assert project_service.validate_launch_path("") is False
    assert project_service.validate_launch_path("C:\\non_existent_folder_xyz_999") is False
