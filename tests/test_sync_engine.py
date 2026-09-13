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
            date TEXT NOT NULL,
            rollover_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP
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
            completed_exercises TEXT DEFAULT '',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE body_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            weight_kg REAL NOT NULL,
            calories_met INTEGER DEFAULT 0,
            protein_met INTEGER DEFAULT 0,
            notes TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE workouts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            workout_type TEXT NOT NULL,
            details TEXT DEFAULT '',
            intensity INTEGER DEFAULT 7,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            local_path TEXT DEFAULT '',
            github_url TEXT DEFAULT '',
            current_milestone TEXT DEFAULT '',
            next_action TEXT DEFAULT '',
            deadline TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE kill_list_items (
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
    cursor.execute("""
        CREATE TABLE station_deliverable_progress (
            deliverable_id TEXT PRIMARY KEY,
            station_id TEXT NOT NULL,
            stream TEXT NOT NULL,
            title TEXT NOT NULL,
            total_required INTEGER DEFAULT 1,
            completed_count INTEGER DEFAULT 0,
            unit_label TEXT DEFAULT 'reps',
            is_completed INTEGER DEFAULT 0
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
    monkeypatch.setenv("HARNESS_WEB_URL", "https://harness-web.vercel.app")

    cfg = sync_service.get_sync_config()
    assert cfg["supabase_url"] == "https://env-project.supabase.co"
    assert cfg["supabase_key"] == "env_secret_key_123"
    assert cfg["web_url"] == "https://harness-web.vercel.app"


def test_sync_body_metrics(temp_sync_env):
    conn, data_dir = temp_sync_env
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO body_metrics (id, date, weight_kg, calories_met, protein_met, notes) VALUES (1, '2026-09-10', 69.5, 1, 1, 'Local log')"
    )
    conn.commit()

    remote_metrics = [
        {"id": 1, "date": "2026-09-10", "weight_kg": 69.8, "calories_met": True, "protein_met": True, "notes": "Updated remote"},
        {"id": 2, "date": "2026-09-11", "weight_kg": 70.0, "calories_met": False, "protein_met": True, "notes": "Morning weigh-in"},
    ]

    with patch.object(sync_service, "_make_supabase_request", return_value=remote_metrics):
        count = sync_service.sync_body_metrics(conn)
        assert count >= 1

    cursor.execute("SELECT weight_kg, notes FROM body_metrics WHERE id = 1")
    row1 = cursor.fetchone()
    assert row1[0] == 69.8
    assert row1[1] == "Updated remote"

    cursor.execute("SELECT weight_kg FROM body_metrics WHERE id = 2")
    row2 = cursor.fetchone()
    assert row2 is not None
    assert row2[0] == 70.0


def test_sync_workouts(temp_sync_env):
    conn, data_dir = temp_sync_env
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO workouts (id, date, workout_type, details, intensity) VALUES (1, '2026-09-10', 'Boxing', 'Pad work', 8)"
    )
    conn.commit()

    remote_workouts = [
        {"id": 1, "date": "2026-09-10", "workout_type": "Boxing", "details": "Pad work & Sparring", "intensity": 9},
        {"id": 2, "date": "2026-09-11", "workout_type": "Gym", "details": "Trap Bar Deadlift", "intensity": 8},
    ]

    with patch.object(sync_service, "_make_supabase_request", return_value=remote_workouts):
        count = sync_service.sync_workouts(conn)
        assert count >= 1

    cursor.execute("SELECT details, intensity FROM workouts WHERE id = 1")
    row1 = cursor.fetchone()
    assert row1[0] == "Pad work & Sparring"
    assert row1[1] == 9

    cursor.execute("SELECT workout_type FROM workouts WHERE id = 2")
    row2 = cursor.fetchone()
    assert row2 is not None
    assert row2[0] == "Gym"


def test_sync_projects(temp_sync_env):
    conn, data_dir = temp_sync_env
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO projects (id, name, description, current_milestone, next_action, status) VALUES (1, 'Harness', 'Personal OS', 'V2', 'Fix sync', 'active')"
    )
    conn.commit()

    remote_projects = [
        {"id": 1, "name": "Harness", "description": "Personal OS", "current_milestone": "V3.5", "next_action": "Verify web cross sync", "status": "active"},
        {"id": 2, "name": "SIGG Scanner", "description": "GPW stock scanner", "current_milestone": "Phase 1", "next_action": "Backtest", "status": "active"},
    ]

    with patch.object(sync_service, "_make_supabase_request", return_value=remote_projects):
        count = sync_service.sync_projects(conn)
        assert count >= 1

    cursor.execute("SELECT current_milestone, next_action FROM projects WHERE id = 1")
    row1 = cursor.fetchone()
    assert row1[0] == "V3.5"
    assert row1[1] == "Verify web cross sync"

    cursor.execute("SELECT name FROM projects WHERE id = 2")
    row2 = cursor.fetchone()
    assert row2 is not None
    assert row2[0] == "SIGG Scanner"


def test_sync_daily_logs_reflections_and_times(temp_sync_env):
    conn, data_dir = temp_sync_env
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO daily_logs (date, scratchpad, wake_time, sleep_time, reflection_worked, reflection_slipped, reflection_tomorrow)
        VALUES ('2026-09-12', 'Notes', '06:30', '', 'Did Math', '', 'Do CS')
        """
    )
    conn.commit()

    remote_logs = [
        {
            "date": "2026-09-12",
            "scratchpad": "Notes updated remotely",
            "wake_time": "06:30",
            "sleep_time": "22:15",
            "reflection_worked": "Did Math & German",
            "reflection_slipped": "Phone past 21:00",
            "reflection_tomorrow": "Do CS early",
            "completed_blocks": "06:30-07:30",
            "completed_exercises": "",
        }
    ]

    with patch.object(sync_service, "_make_supabase_request", return_value=remote_logs):
        count = sync_service.sync_daily_logs(conn)
        assert count >= 1

    cursor.execute("SELECT sleep_time, reflection_worked, reflection_slipped, reflection_tomorrow FROM daily_logs WHERE date = '2026-09-12'")
    row = cursor.fetchone()
    assert row[0] == "22:15"
    assert row[1] == "Did Math & German"
    assert row[2] == "Phone past 21:00"
    assert row[3] == "Do CS early"


def test_direct_web_sync_exchange(temp_sync_env):
    conn, data_dir = temp_sync_env
    cfg = {
        "web_url": "https://harness-web.vercel.app",
        "supabase_key": "",
        "auto_sync": True,
        "last_synced_at": None,
    }

    mock_server_response = {
        "status": "synced",
        "synced_count": 2,
        "timestamp": "2026-09-12T22:35:00",
        "data": {
            "tasks": [
                {"id": 99, "title": "Web Task", "category": "Academic", "is_tum": 1, "completed": 0, "date": "2026-09-12"}
            ],
            "body_metrics": [
                {"id": 99, "date": "2026-09-12", "weight_kg": 72.5, "calories_met": 1, "protein_met": 1, "notes": "Web log"}
            ],
            "daily_logs": [],
            "kill_list_items": [],
            "station_deliverable_progress": [],
            "workouts": [],
            "projects": [],
        }
    }

    with patch.object(sync_service, "_post_json", return_value=mock_server_response):
        res = sync_service.sync_with_web_server(conn, cfg)
        assert res["status"] == "synced"
        assert res["synced_count"] >= 2

    cursor = conn.cursor()
    cursor.execute("SELECT title FROM tasks WHERE id = 99")
    task_row = cursor.fetchone()
    assert task_row is not None
    assert task_row[0] == "Web Task"

    cursor.execute("SELECT weight_kg FROM body_metrics WHERE id = 99")
    body_row = cursor.fetchone()
    assert body_row is not None
    assert body_row[0] == 72.5


