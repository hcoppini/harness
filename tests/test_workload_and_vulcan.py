"""
Tests for Harness 3.0 Vulcan UONET+ Ingestion and Adaptive Workload Governor.
"""

import sqlite3
from datetime import datetime, timedelta
import pytest

from app.db import init_db
from app.services import vulcan_service, today_service, homework_service
from engine import workload_governor, kill_list_controller


@pytest.fixture
def test_db(tmp_path, monkeypatch):
    temp_config = tmp_path / "temp_vulcan_config.json"
    monkeypatch.setattr(vulcan_service, "CONFIG_FILE", temp_config)
    db_path = tmp_path / "test_harness.db"
    init_db(db_path)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()



def test_vulcan_sync_demo_mode(test_db):
    test_date = "2026-09-14"
    res = vulcan_service.sync_vulcan_data(client_date=test_date, conn=test_db)
    assert res["status"] == "synced"
    assert res["exams_synced"] >= 4
    assert res["homework_synced"] >= 2

    # Check that school_exams table is populated
    exams = homework_service.get_upcoming_exams(conn=test_db)
    assert len(exams) >= 4
    subjects = [e["subject"] for e in exams]
    assert "Matematyka R" in subjects
    assert "Fizyka" in subjects


def test_workload_governor_cruise_vs_surge(test_db):
    test_date = "2026-09-14"

    # Initially empty exams -> CRUISE mode
    analysis_empty = workload_governor.get_workload_analysis(test_date, conn=test_db)
    assert analysis_empty["mode"] == "CRUISE"
    assert analysis_empty["total_exams"] == 0

    # Sync 4 upcoming tests -> SURGE mode
    vulcan_service.sync_vulcan_data(client_date=test_date, conn=test_db)
    analysis_surge = workload_governor.get_workload_analysis(test_date, conn=test_db)
    assert analysis_surge["mode"] == "SURGE"
    assert analysis_surge["total_exams"] >= 4
    assert "Surge Protocol" in analysis_surge["mode_label"]


def test_adaptive_schedule_synthesis(test_db):
    test_date = "2026-09-14"  # Monday (Schedule A_MON with SGH Library)
    vulcan_service.sync_vulcan_data(client_date=test_date, conn=test_db)

    # Base schedule
    base_sched = today_service.get_schedule_for_date("2026-09-14", conn=test_db)
    assert "workload" in base_sched
    assert base_sched["workload"]["mode"] == "SURGE"

    # Deep work block should be adapted for the upcoming exam
    deep_block = next((b for b in base_sched["blocks"] if b.get("type") == "deep_work"), None)
    assert deep_block is not None
    assert deep_block.get("is_surge") is True
    assert "Matematyka R" in deep_block["activity"] or "Prep" in deep_block["focus"]

    # Boxing block (17:20) and sleep block must remain completely protected
    boxing_block = next((b for b in base_sched["blocks"] if b.get("type") == "training"), None)
    assert boxing_block is not None
    assert "17:20" in boxing_block["time"]


def test_recommended_kill_items(test_db):
    test_date = "2026-09-14"
    vulcan_service.sync_vulcan_data(client_date=test_date, conn=test_db)

    recs = workload_governor.get_recommended_kill_items(test_date, conn=test_db)
    assert len(recs) >= 2

    # Should recommend nearest exam prep
    types = [r["type"] for r in recs]
    assert "exam_prep" in types
    assert "metro_deliverable" in types

    # 1-click enqueue test prep item into kill list
    exam_rec = next(r for r in recs if r["type"] == "exam_prep")
    kill_item = kill_list_controller.enqueue_exam_prep(exam_rec["exam_id"], date_str=test_date, conn=test_db)
    assert kill_item["category"] == "Exam Prep"
    assert "Prep" in kill_item["title"]


def test_extract_eduvulcan_token():
    import base64
    import json

    payload = {
        "name": "Jan Smagieł",
        "uid": "test-uid-123",
        "tenant": "warszawa",
        "unituid": "test-unit-456",
    }
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    fake_jwt = f"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.{payload_b64}.signature123"

    # 1. Raw JWT string
    data1 = vulcan_service.extract_token_data(fake_jwt)
    assert data1["token"] == fake_jwt
    assert data1["tenant"] == "warszawa"
    assert data1["student_name"] == "Jan Smagieł"

    # 2. JSON wrapper from https://eduvulcan.pl/api/ap
    json_input = json.dumps({"Tokens": [fake_jwt], "Alias": "jsmagiel", "Success": True})
    data2 = vulcan_service.extract_token_data(json_input)
    assert data2["token"] == fake_jwt
    assert data2["tenant"] == "warszawa"

    # 3. HTML hidden input snippet
    html_input = f'<input type="hidden" id="rawToken" value=\'{json_input}\'>'
    data3 = vulcan_service.extract_token_data(html_input)
    assert data3["token"] == fake_jwt
    assert data3["tenant"] == "warszawa"


def test_keypair_and_request_signing():
    cert, fp, pk = vulcan_service.generate_client_keypair()
    assert len(cert) > 100
    assert len(fp) in (32, 40)
    assert len(pk) > 100


    url = "https://lekcjaplus.vulcan.net.pl/warszawa/api/mobile/exam/byPupil?pupilId=123"
    headers = vulcan_service.build_signed_headers(
        url=url,
        body_str=None,
        fingerprint=fp,
        private_key=pk,
        pupil_id=123,
    )
    assert "Signature" in headers
    assert f'keyId="{fp}"' in headers["Signature"]
    assert headers["vHint"] == "123"
    assert headers["vOS"] == "Android"


def test_manual_exam_addition(test_db):
    test_date = "2026-09-15"
    exam = vulcan_service.add_manual_exam(
        subject="Fizyka",
        title="Sprawdzian: Elektrostatyka",
        exam_date=test_date,
        scope="Prawo Coulomba, pole elektryczne",
        weight=3,
        conn=test_db,
    )
    assert exam["id"] is not None
    assert exam["subject"] == "Fizyka"
    assert exam["title"] == "Sprawdzian: Elektrostatyka"

    exams = homework_service.get_upcoming_exams(conn=test_db)
    found = next((e for e in exams if e["title"] == "Sprawdzian: Elektrostatyka"), None)
    assert found is not None
    assert found["subject"] == "Fizyka"


def test_vulcan_status_and_disconnect(test_db, tmp_path, monkeypatch):
    # Point config to temporary path
    temp_config = tmp_path / "temp_vulcan_config.json"
    monkeypatch.setattr(vulcan_service, "CONFIG_FILE", temp_config)

    status = vulcan_service.get_vulcan_status()
    assert status["mode"] == "demo_tm1"
    assert status["is_connected"] is False

    # Simulate connection
    cfg = vulcan_service.get_vulcan_config()
    cfg["demo_mode"] = False
    cfg["student_name"] = "Jan Smagieł"
    cfg["student_symbol"] = "warszawa"
    cfg["registered_device"] = {"fingerprint": "12345"}
    vulcan_service.save_vulcan_config(cfg)

    status2 = vulcan_service.get_vulcan_status()
    assert status2["mode"] == "live"
    assert status2["is_connected"] is True
    assert status2["student_name"] == "Jan Smagieł"

    # Disconnect
    vulcan_service.disconnect_vulcan()
    status3 = vulcan_service.get_vulcan_status()
    assert status3["mode"] == "demo_tm1"
    assert status3["is_connected"] is False

