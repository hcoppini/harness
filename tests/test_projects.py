"""Unit tests for Projects layer: project seeding, updates, and milestone tracking."""

import sqlite3
import pytest
from app.db import init_db
from app.services import project_service


@pytest.fixture
def test_db(tmp_path):
    db_file = tmp_path / "test_projects.db"
    init_db(db_file)
    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


def test_projects_seeding(test_db):
    projects = project_service.get_all_projects(conn=test_db)
    assert len(projects) >= 4
    names = [p["name"] for p in projects]
    assert any("SIGG" in name for name in names)
    assert any("Code Independence" in name for name in names)
    assert any("Harness" in name for name in names)


def test_update_project_milestone_and_next_action(test_db):
    projects = project_service.get_all_projects(conn=test_db)
    sigg_proj = [p for p in projects if "SIGG" in p["name"]][0]

    updated = project_service.update_project(
        project_id=sigg_proj["id"],
        current_milestone="Stage 1 Live Execution",
        next_action="Review top 5 momentum stocks in mWIG40",
        notes="Educational bonus completed with max points",
        conn=test_db,
    )
    assert updated is True

    updated_projects = project_service.get_all_projects(conn=test_db)
    sigg_updated = [p for p in updated_projects if p["id"] == sigg_proj["id"]][0]
    assert sigg_updated["current_milestone"] == "Stage 1 Live Execution"
    assert sigg_updated["next_action"] == "Review top 5 momentum stocks in mWIG40"
