"""
Headless Google Calendar Cross-Sync runner for scheduled automation / GitHub Actions.

Environment variables supported:
  GCAL_CLIENT_ID, GCAL_CLIENT_SECRET, GCAL_REFRESH_TOKEN, GCAL_ICAL_URLS, GCAL_CALENDAR_ID
"""

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.db import init_db
from app.services import gcalendar_service


def main() -> int:
    init_db()
    summary = gcalendar_service.sync_all_gcalendar()
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
