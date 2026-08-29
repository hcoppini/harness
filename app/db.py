"""Database connection and initialization module for Harness."""

import os
import sys
import sqlite3
from pathlib import Path
from typing import Optional

# Base directory paths
if getattr(sys, "frozen", False):
    # Running as compiled executable: persist data alongside the executable
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"
DEFAULT_DB_PATH = DATA_DIR / "harness.db"


def get_db_path() -> Path:
    """Returns the path to the SQLite database file."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DEFAULT_DB_PATH


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Returns a SQLite connection configured with WAL mode and row factory."""
    path = db_path or get_db_path()
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    # Enable WAL mode for high concurrency and zero locking issues
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def init_db(db_path: Optional[Path] = None) -> None:
    """Initializes all database tables and ensures JSON data templates are present."""
    # Ensure JSON templates exist if running frozen
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            bundled_data = Path(meipass) / "data"
            if bundled_data.exists():
                import shutil
                DATA_DIR.mkdir(parents=True, exist_ok=True)
                for json_file in bundled_data.glob("*.json"):
                    dest = DATA_DIR / json_file.name
                    if not dest.exists():
                        shutil.copy2(json_file, dest)

    conn = get_connection(db_path)
    cursor = conn.cursor()

    # 1. Daily Tasks & Routine
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT 'personal', -- school, study, code, fitness, chore, personal
            is_tum INTEGER NOT NULL DEFAULT 0,         -- 1 if this is the daily TUM Imperative
            completed INTEGER NOT NULL DEFAULT 0,
            date TEXT NOT NULL,                        -- YYYY-MM-DD
            rollover_count INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP
        );
        """
    )

    # 2. Daily Log & Scratchpad
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS daily_logs (
            date TEXT PRIMARY KEY,                     -- YYYY-MM-DD
            scratchpad TEXT DEFAULT '',
            wake_time TEXT DEFAULT '',
            sleep_time TEXT DEFAULT '',
            reflection_worked TEXT DEFAULT '',
            reflection_slipped TEXT DEFAULT '',
            reflection_tomorrow TEXT DEFAULT '',
            completed_blocks TEXT DEFAULT '',
            completed_exercises TEXT DEFAULT '',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    # Migrations for existing DB instances
    cursor.execute("PRAGMA table_info(daily_logs)")
    dl_cols = [row[1] for row in cursor.fetchall()]
    if "completed_blocks" not in dl_cols:
        cursor.execute("ALTER TABLE daily_logs ADD COLUMN completed_blocks TEXT DEFAULT ''")
    if "completed_exercises" not in dl_cols:
        cursor.execute("ALTER TABLE daily_logs ADD COLUMN completed_exercises TEXT DEFAULT ''")

    # 3. TUM Roadmap & Grades
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS tum_grades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT NOT NULL,
            semester INTEGER NOT NULL,                 -- 1, 2, 3, 4 (Liceum 3 & 4)
            target_grade REAL NOT NULL DEFAULT 5.0,    -- 1 to 6 scale
            actual_grade REAL DEFAULT NULL,
            percentage REAL DEFAULT NULL,
            notes TEXT DEFAULT ''
        );
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS tum_matura (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT NOT NULL UNIQUE,              -- Maths R, CS R, Bilingual English, etc.
            target_percentage REAL NOT NULL,
            current_mock_percentage REAL DEFAULT 0.0,
            notes TEXT DEFAULT ''
        );
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS tum_language (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            level TEXT NOT NULL UNIQUE,                -- A1, A2, B1, B2
            target_date TEXT,
            status TEXT NOT NULL DEFAULT 'pending',   -- pending, in_progress, completed
            milestone_description TEXT NOT NULL
        );
        """
    )

    # 4. Projects Registry
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            status TEXT NOT NULL DEFAULT 'active',     -- active, paused, completed
            local_path TEXT,
            github_url TEXT,
            current_milestone TEXT,
            next_action TEXT,
            deadline TEXT,
            notes TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    # 5. Body & Machine Maintenance
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS body_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL UNIQUE,                 -- YYYY-MM-DD
            weight_kg REAL NOT NULL,
            calories_met INTEGER DEFAULT 0,
            protein_met INTEGER DEFAULT 0,
            notes TEXT DEFAULT ''
        );
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS workouts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,                        -- YYYY-MM-DD
            workout_type TEXT NOT NULL,                -- boxing, gym, running
            details TEXT NOT NULL,
            intensity INTEGER DEFAULT 5,               -- 1 to 10
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    # 6. Knowledge / First-Principles Ledger
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS knowledge_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            category TEXT NOT NULL,                    -- algorithm, mental_model, book, note
            content TEXT NOT NULL,
            tags TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print(f"Database initialized at {get_db_path()}")
