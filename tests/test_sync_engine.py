"""
Unit tests for Harness Cross-Device Cloud Sync Engine.
Tests two-way delta sync, offline resilience, and JSON configuration.
"""

import json
import sqlite3
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from app.services import sync_service
from app.api import HarnessAPI


@pytest.fixture
def temp_sync_env(tmp_path, monkeypatch):
    """Sets up an isolated SQLite DB and sync config directory."""
    test_data_dir = tmp_path / "data"
    test_data_dir.mkdir()

    monkeypatch.setattr(sync_service, "DATA_DIR", test_data_dir)
    monkeypatch.setattr(sync_service, "CONFIG_FILE", test_data_dir / "sync_config.json")

    # In-memory or temporary SQLite db
    db_path = test_data_dir / "harness.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Create tables needed for sync
    cursor.execute("""
        CREATE TABLE tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            category TEXT DEFAULT 'personal',
            is_tum INTEGER DEFAULT 0,
            completed INTEGER DEFAULT 0,
            date TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE daily_logs (
            date TEXT PRIMARY KEY,
            scratchpad TEXT DEFAULT '',
            wake_time TEXT,
            sleep_time TEXT,
            reflection_worked TEXT,
            reflection_slipped TEXT,
            reflection_tomorrow TEXT,
            completed_blocks TEXT DEFAULT '',
            completed_exercises TEXT DEFAULT ''
        )
    """)
    conn.commit()

    # Mock get_connection in sync_service
    monkeypatch.setattr(sync_service, "get_connection", lambda: sqlite3.connect(str(db_path)))

    yield conn, test_data_dir
    conn.close()


def test_sync_config_lifecycle(temp_sync_env):
    conn, data_dir = temp_sync_env

    # 1. Default config
    cfg = sync_service.get_sync_config()
    assert "supabase_url" in cfg
    assert cfg["supabase_key"] == ""
    assert cfg["auto_sync"] is True

    # 2. Update config
    cfg["supabase_key"] = "test_key_abc_123"
    cfg["auto_sync"] = False
    sync_service.save_sync_config(cfg)

    # 3. Read back
    cfg_loaded = sync_service.get_sync_config()
    assert cfg_loaded["supabase_key"] == "test_key_abc_123"
    assert cfg_loaded["auto_sync"] is False


def test_sync_unconfigured_behavior(temp_sync_env):
    conn, data_dir = temp_sync_env
    # Key is empty by default
    res = sync_service.sync_all()
    assert res["status"] == "unconfigured"
    assert res["synced_count"] == 0


def test_sync_tasks_two_way(temp_sync_env):
    conn, data_dir = temp_sync_env

    # Set dummy API key
    sync_service.save_sync_config({
        "supabase_url": "https://test.supabase.co",
        "supabase_key": "dummy_secret_key",
        "auto_sync": True,
        "last_synced_at": None,
    })

    # Insert local task
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO tasks (id, title, category, is_tum, completed, date) VALUES (1, 'Local task', 'Code', 1, 0, '2026-09-07')"
    )
    conn.commit()

    # Mock Supabase returning a remote task (id=2) and updating local task 1 to completed
    remote_tasks_payload = [
        {"id": 1, "title": "Local task", "category": "Code", "is_tum": True, "completed": True, "date": "2026-09-07"},
        {"id": 2, "title": "Remote laptop task", "category": "Academic", "is_tum": True, "completed": False, "date": "2026-09-07"},
    ]

    with patch.object(sync_service, "_make_supabase_request", return_value=remote_tasks_payload):
        count = sync_service.sync_tasks(conn)
        assert count >= 1

    # Verify task 1 is now completed in local DB
    cursor.execute("SELECT completed FROM tasks WHERE id = 1")
    assert cursor.fetchone()[0] == 1

    # Verify task 2 was inserted into local DB
    cursor.execute("SELECT title, is_tum FROM tasks WHERE id = 2")
    row = cursor.fetchone()
    assert row is not None
    assert row[0] == "Remote laptop task"
    assert row[1] == 1


def test_sync_daily_logs_merging(temp_sync_env):
    conn, data_dir = temp_sync_env

    # Insert local daily log with some completed blocks
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO daily_logs (date, scratchpad, completed_blocks, completed_exercises)
        VALUES ('2026-09-07', 'Local note', '06:00-06:30,07:00-08:00', 'ex1')
        """
    )
    conn.commit()

    # Remote payload with additional completed block and exercise
    remote_logs = [
        {
            "date": "2026-09-07",
            "scratchpad": "Local note with laptop update",
            "completed_blocks": "06:00-06:30,13:30-15:30",
            "completed_exercises": "ex1,ex2",
        }
    ]

    with patch.object(sync_service, "_make_supabase_request", return_value=remote_logs):
        count = sync_service.sync_daily_logs(conn)
        assert count >= 1

    cursor.execute("SELECT completed_blocks, completed_exercises, scratchpad FROM daily_logs WHERE date = '2026-09-07'")
    row = cursor.fetchone()
    blocks = row[0].split(",")
    exercises = row[1].split(",")

    # Verify union merge
    assert "06:00-06:30" in blocks
    assert "07:00-08:00" in blocks
    assert "13:30-15:30" in blocks
    assert "ex1" in exercises
    assert "ex2" in exercises
    assert "laptop update" in row[2]


def test_sync_metro_roadmap(temp_sync_env):
    conn, data_dir = temp_sync_env

    metro_file = data_dir / "metro_roadmap.json"
    metro_data = {
        "stations": [
            {
                "id": "st_01",
                "name": "B.Sc. Curriculum Architecture",
                "status": "in_progress",
                "deliverables": {"d1": "Course Matrix", "d2": "Credit Calc"},
                "completed_deliverables": ["d1"],
            }
        ]
    }
    with open(metro_file, "w", encoding="utf-8") as f:
        json.dump(metro_data, f)

    remote_stations = [
        {
            "id": "st_01",
            "completed_deliverables": ["d1", "d2"],
        }
    ]

    with patch.object(sync_service, "_make_supabase_request", return_value=remote_stations):
        count = sync_service.sync_metro_roadmap()
        assert count >= 1

    with open(metro_file, "r", encoding="utf-8") as f:
        updated = json.load(f)

    st = updated["stations"][0]
    assert "d1" in st["completed_deliverables"]
    assert "d2" in st["completed_deliverables"]
    assert st["status"] == "completed"


def test_offline_resilience(temp_sync_env):
    conn, data_dir = temp_sync_env

    sync_service.save_sync_config({
        "supabase_url": "https://test.supabase.co",
        "supabase_key": "dummy_secret_key",
        "auto_sync": True,
        "last_synced_at": None,
    })

    # Simulate network failure (e.g. urllib returning None / raising)
    with patch.object(sync_service, "_make_supabase_request", return_value=None):
        res = sync_service.sync_all()
        # Should gracefully finish without exceptions
        assert res["status"] == "synced"
        assert res["synced_count"] == 0


def test_harness_api_sync_methods(temp_sync_env):
    conn, data_dir = temp_sync_env
    api = HarnessAPI()

    # 1. Status when unconfigured
    st = api.get_sync_status()
    assert st["status"] == "unconfigured"
    assert st["has_key"] is False

    # 2. Configure via API
    ok = api.configure_sync("https://custom.supabase.co", "custom_key_xyz", True)
    assert ok is True

    st_after = api.get_sync_status()
    assert st_after["has_key"] is True
    assert st_after["supabase_url"] == "https://custom.supabase.co"

    # 3. Sync now via API
    with patch.object(sync_service, "_make_supabase_request", return_value=[]):
        res = api.sync_now()
        assert res["status"] == "synced"


def test_sync_kill_list_items(temp_sync_env):
    conn, data_dir = temp_sync_env
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS kill_list_items (
            id TEXT PRIMARY KEY,
            date TEXT NOT NULL,
            category TEXT NOT NULL,
            title TEXT NOT NULL,
            action_type TEXT NOT NULL,
            target_path TEXT NOT NULL,
            target_spec TEXT NOT NULL,
            station_deliverable_id TEXT,
            completed INTEGER DEFAULT 0
        )
    """)
    cursor.execute(
        "INSERT INTO kill_list_items (id, date, category, title, action_type, target_path, target_spec, completed) VALUES ('k1', '2026-09-10', 'Math R', 'Diagnostic 1-5', 'pdf', 'https://cke.gov.pl', 'Zadania 1-5', 0)"
    )
    conn.commit()

    remote_items = [
        {"id": "k1", "date": "2026-09-10", "category": "Math R", "title": "Diagnostic 1-5", "action_type": "pdf", "target_path": "https://cke.gov.pl", "target_spec": "Zadania 1-5", "completed": True},
        {"id": "k2", "date": "2026-09-10", "category": "German", "title": "20 Anki Words", "action_type": "url", "target_path": "https://dw.com", "target_spec": "A2", "completed": False},
    ]

    with patch.object(sync_service, "_make_supabase_request", return_value=remote_items):
        count = sync_service.sync_kill_list_items(conn)
        assert count >= 1

    cursor.execute("SELECT completed FROM kill_list_items WHERE id = 'k1'")
    assert cursor.fetchone()[0] == 1
    cursor.execute("SELECT title FROM kill_list_items WHERE id = 'k2'")
    assert cursor.fetchone()[0] == "20 Anki Words"


def test_sync_env_variable_resolution(temp_sync_env, monkeypatch):
    conn, data_dir = temp_sync_env
    monkeypatch.setenv("SUPABASE_URL", "https://env-project.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "env_secret_key_123")

    cfg = sync_service.get_sync_config()
    assert cfg["supabase_url"] == "https://env-project.supabase.co"
    assert cfg["supabase_key"] == "env_secret_key_123"

