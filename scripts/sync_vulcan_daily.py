"""
Headless daily 3:00 PM Vulcan synchronizer for Harness.
Syncs homeworks, exams, and grades into the SQLite Grade Ledger,
then replicates deltas to Supabase.
"""

import os
import sys
from pathlib import Path
from datetime import datetime

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.services import vulcan_service, sync_service

def main():
    log_dir = ROOT_DIR / "data"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "vulcan_sync.log"

    timestamp = datetime.now().isoformat()
    try:
        res = vulcan_service.sync_vulcan_data(force_refresh=True)
        try:
            sync_service.sync_all()
        except Exception:
            pass

        log_entry = f"[{timestamp}] 3PM Vulcan Sync SUCCESS: {res}\n"
    except Exception as e:
        log_entry = f"[{timestamp}] 3PM Vulcan Sync ERROR: {e}\n"

    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(log_entry)
    except Exception:
        pass

    print(log_entry.strip())

if __name__ == "__main__":
    main()
