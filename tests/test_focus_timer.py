"""Unit tests for Focus Deep Work timer logging."""

import sqlite3
import pytest
from app.db import init_db
from app.services import today_service


@pytest.fixture
def test_db(tmp_path):
    db_file = tmp_path / "test_focus.db"
    init_db(db_file)
    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


def test_focus_timer_block_logging(test_db):
    today_str = "2026-09-01"

    # Log completion of a 60m focus block
    log = today_service.update_daily_log(
        date_str=today_str,
        completed_blocks="0",
        scratchpad="Finished 60m Math R sprint on trigonometry",
        conn=test_db,
    )
    assert log["date"] == today_str
    assert "0" in log["completed_blocks"]

    # Verify retrieval
    retrieved = today_service.get_daily_log(date_str=today_str, conn=test_db)
    assert retrieved["completed_blocks"] == "0"
    assert "trigonometry" in retrieved["scratchpad"]
