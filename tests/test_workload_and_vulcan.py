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
    test_date = "2026-09-16"  # Wednesday (Schedule A_WED with SGH Library + Boxing)
    vulcan_service.sync_vulcan_data(client_date=test_date, conn=test_db)

    # Base schedule
    base_sched = today_service.get_schedule_for_date("2026-09-16", conn=test_db)
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


def test_vulcan_grades_sync_and_ledger_update(test_db):
    test_date = "2026-09-14"
    res = vulcan_service.sync_vulcan_data(client_date=test_date, conn=test_db)
    assert res["status"] == "synced"
    assert res["grades_synced"] >= 2

    # Verify tum_grade_entries table is populated
    cursor = test_db.cursor()
    cursor.execute("SELECT * FROM tum_grade_entries ORDER BY id ASC")
    entries = [dict(r) for r in cursor.fetchall()]
    assert len(entries) >= 2

    math_entry = next((e for e in entries if e["subject"] == "Matematyka"), None)
    assert math_entry is not None
    assert math_entry["raw_input"] == "5+"
    assert math_entry["numeric_value"] == 5.5

    # Verify tum_grades actual_grade running average was automatically updated
    cursor.execute("SELECT * FROM tum_grades WHERE subject = 'Matematyka' AND semester = 1")
    math_grade = dict(cursor.fetchone())
    assert math_grade["actual_grade"] == 5.5

    cursor.execute("SELECT * FROM tum_grades WHERE subject = 'Informatyka' AND semester = 1")
    cs_grade = dict(cursor.fetchone())
    assert cs_grade["actual_grade"] == 6.0


def test_vulcan_daily_3pm_sync_trigger(test_db, monkeypatch):
    from unittest.mock import MagicMock
    from datetime import datetime

    # 1. Simulate 2:30 PM (before 3:00 PM) -> Should NOT trigger
    fake_2pm = datetime(2026, 9, 14, 14, 30, 0)
    mock_dt = MagicMock()
    mock_dt.now.return_value = fake_2pm
    mock_dt.fromisoformat = datetime.fromisoformat
    mock_dt.strptime = datetime.strptime
    monkeypatch.setattr(vulcan_service, "datetime", mock_dt)

    res_early = vulcan_service.check_and_run_daily_3pm_sync(conn=test_db)
    assert res_early is None

    # 2. Simulate 3:05 PM (after 3:00 PM, first time today) -> Should trigger
    fake_3pm = datetime(2026, 9, 14, 15, 5, 0)
    mock_dt.now.return_value = fake_3pm

    res_due = vulcan_service.check_and_run_daily_3pm_sync(conn=test_db)
    assert res_due is not None
    assert res_due["status"] == "synced"

    cfg = vulcan_service.get_vulcan_config()
    assert cfg["last_daily_sync_date"] == "2026-09-14"

    # 3. Simulate 4:00 PM on same day -> Already ran today, should return None
    fake_4pm = datetime(2026, 9, 14, 16, 0, 0)
    mock_dt.now.return_value = fake_4pm

    res_already_ran = vulcan_service.check_and_run_daily_3pm_sync(conn=test_db)
    assert res_already_ran is None

    # 4. Force trigger -> Should run even if already ran today
    res_forced = vulcan_service.check_and_run_daily_3pm_sync(conn=test_db, force=True)
    assert res_forced is not None
    assert res_forced["status"] == "synced"


def test_vulcan_live_mode_offline_never_injects_demo_exams(test_db, monkeypatch):
    """Verifies that accounts with registered devices never fall back to fake demo data when offline."""
    cfg = {
        "enabled": True,
        "demo_mode": False,
        "registered_device": {"device_id": "test-device"},
    }
    monkeypatch.setattr(vulcan_service, "get_vulcan_config", lambda: cfg)
    # Simulate network failure
    monkeypatch.setattr(vulcan_service, "_fetch_live_vulcan_payload", lambda c, d: None)

    res = vulcan_service.sync_vulcan_data(client_date="2026-09-19", conn=test_db)
    assert res["status"] == "offline"
    assert res["mode"] == "live_offline"

    # Confirm no fake exams were added
    cursor = test_db.cursor()
    cursor.execute("SELECT COUNT(*) AS cnt FROM school_exams WHERE title LIKE '%Trygonometria%'")
    assert cursor.fetchone()["cnt"] == 0


def test_enqueue_homework_prep(test_db):
    """Verifies 1-click enqueuing of urgent homework into the Kill List."""
    from app.services import homework_service
    hw = homework_service.add_homework(
        subject="Fizyka",
        title="Prezentacja: Termodynamika",
        due_date="2026-09-20",
        priority=2,
        conn=test_db,
    )
    test_date = "2026-09-19"
    item = kill_list_controller.enqueue_homework_prep(hw["id"], date_str=test_date, conn=test_db)
    assert item["category"] == "Homework"
    assert "Termodynamika" in item["title"]
    assert item["date"] == test_date


def test_multi_obligation_adaptive_kill_list(test_db):
    """Verifies that high academic load (multiple exams + urgent homework) dynamically allocates up to 2 school slots + 1 TUM anchor."""
    from app.services import homework_service
    test_date = "2026-09-19"

    # Add 2 exams due within 3 days
    homework_service.add_exam("Informatyka", "Sprawdzian: C++ i Algorytmy", "2026-09-21", conn=test_db)
    homework_service.add_exam("Matematyka", "Kartkówka: Ciągi", "2026-09-22", conn=test_db)
    # Add 1 urgent homework due tomorrow
    homework_service.add_homework("Fizyka", "Zadania z optyki", "2026-09-20", priority=2, conn=test_db)

    res = kill_list_controller.auto_populate_kill_list(test_date, conn=test_db)
    items = res["items"]
    assert len(items) == 3

    categories = [i["category"] for i in items]
    # School defense should take 2 slots (Homework + Exam Prep)
    assert "Homework" in categories
    assert "Exam Prep" in categories
    # Third slot MUST be a TUM anchor (Math R, Algorithms, or German)
    assert any(c in ["Math R", "Algorithms", "German"] for c in categories)


def test_exam_day_afternoon_sgh_never_assigns_prep_for_today_exam(test_db):
    """Verifies that when an exam is scheduled for today (taken in morning school hours),
    the afternoon SGH Deep Work block does NOT assign prep for that exam."""
    from app.services import homework_service
    test_date = "2026-09-23"  # Wednesday (Schedule A_WED with SGH Library)

    # CS exam occurred today (morning)
    homework_service.add_exam("Informatyka", "Sprawdzian: Podstawy programowania", "2026-09-23", conn=test_db)
    # Next exam is in 5 days
    homework_service.add_exam("Fizyka", "Sprawdzian: Termodynamika", "2026-09-28", conn=test_db)

    sched = today_service.get_schedule_for_date(test_date, conn=test_db)
    deep_block = next((b for b in sched["blocks"] if b.get("type") == "deep_work"), None)
    assert deep_block is not None

    # Afternoon deep work must NEVER prepare for today's CS exam
    assert "Informatyka" not in deep_block["focus"]
    assert "Podstawy programowania" not in deep_block["activity"]
    # It targets either future exams or standard TUM deep work
    assert "Informatyka" not in deep_block.get("activity", "")


def test_acute_defense_single_nearest_exam_dominance(test_db):
    """
    Verifies that when multiple exams loom (e.g. Chemia in 1d, Fizyka in 3d),
    the acute defense block allocates 100% capacity to the single nearest exam (Chemia),
    pausing TUM roadmap deliverables, and synchronizes phase durations.
    """
    from app.services import homework_service
    test_date = "2026-09-30"  # Wednesday (Schedule A_WED)

    # Exam 1: Chemia in 1 day
    homework_service.add_exam("Chemia", "Kartkówka: Alkany", "2026-10-01", scope="Alkany, izomeria", conn=test_db)
    # Exam 2: Fizyka in 3 days
    homework_service.add_exam("Fizyka", "Sprawdzian: Termodynamika", "2026-10-03", scope="Praca gazu", conn=test_db)

    sched = today_service.get_schedule_for_date(test_date, conn=test_db)
    deep_block = next((b for b in sched["blocks"] if b.get("type") == "deep_work"), None)
    assert deep_block is not None

    # Single nearest exam dominance
    assert "Chemia" in deep_block["focus"]
    assert "Fizyka" not in deep_block["focus"]
    assert deep_block["is_school_dedicated"] is True
    assert deep_block["is_tum_roadmap"] is False
    assert deep_block["deliverable"] is None

    # Parity & sync checks
    assert "plan_phases" in deep_block
    phases = deep_block["plan_phases"]
    assert len(phases) == 3
    total_phase_min = sum(p["duration_min"] for p in phases)
    assert total_phase_min == deep_block["net_minutes"]
    assert deep_block["commute_cutoff"] == "16:15"

    # Descriptions must reference their exact duration minutes
    for p in phases:
        assert f"{p['duration_min']}m" in p["description"]


def test_medium_horizon_balanced_foundation(test_db):
    """
    Verifies that when an exam is 3-5 days away (e.g. 4 days),
    the session synthesizes a 50/50 Balanced Foundation: ~50m exam foundation
    (scope + formulas) and ~60m active TUM deliverable sprint.
    """
    from app.services import homework_service
    test_date = "2026-09-25"  # Friday (Schedule A_FRI)

    # Exam 4 days out
    homework_service.add_exam("Chemia", "Sprawdzian: Węglowodory", "2026-09-29", conn=test_db)

    sched = today_service.get_schedule_for_date(test_date, conn=test_db)
    deep_block = next((b for b in sched["blocks"] if b.get("type") == "deep_work"), None)
    assert deep_block is not None

    assert deep_block["is_school_dedicated"] is False
    assert deep_block["is_tum_roadmap"] is True
    assert deep_block["deliverable"] is not None

    phases = deep_block["plan_phases"]
    assert len(phases) == 3
    assert phases[0]["type"] == "school_defense"
    assert phases[1]["type"] == "school_defense"
    assert phases[2]["type"] == "tum_deliverable"
    assert sum(p["duration_min"] for p in phases) == deep_block["net_minutes"]


def test_pure_cruise_3_pillar_pipeline(test_db):
    """
    Verifies that when no exams or urgent homework loom,
    Monday Boxing day caps cognitive work at the realistic 60m window (55m net),
    while phases cleanly sum to net_minutes and bind the active TUM deliverable.
    """
    test_date = "2026-11-04"  # Wednesday (Boxing + 60m deep work), clear academic horizon

    sched = today_service.get_schedule_for_date(test_date, conn=test_db)
    deep_block = next((b for b in sched["blocks"] if b.get("type") == "deep_work"), None)
    assert deep_block is not None

    assert deep_block["is_school_dedicated"] is False
    assert deep_block["is_tum_roadmap"] is True
    assert deep_block["deliverable"] is not None

    phases = deep_block["plan_phases"]
    assert len(phases) == 3
    assert deep_block["net_minutes"] == 55
    assert sum(p["duration_min"] for p in phases) == deep_block["net_minutes"]


def test_homework_service_positional_string_guard(test_db):
    """Verifies that homework_service methods accept date strings or connection objects interchangeably without crashing."""
    future_date = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d")
    far_future_date = (datetime.now() + timedelta(days=20)).strftime("%Y-%m-%d")
    homework_service.add_homework("Fizyka", "Zadania 1-5", future_date, conn=test_db)
    homework_service.add_exam("Matematyka", "Kartkówka", future_date, conn=test_db)

    # Calling with test_db
    hw = homework_service.get_upcoming_homework(test_db, today_str="2026-11-01")
    assert len(hw) >= 1
    assert any(h["subject"] == "Fizyka" for h in hw)

    exams = homework_service.get_upcoming_exams(test_db, today_str="2026-11-01")
    assert len(exams) >= 1
    assert any(e["subject"] == "Matematyka" for e in exams)

    # Prune expired passing Connection as first positional argument
    pruned1 = homework_service.prune_expired_homework(test_db)
    assert pruned1 == 0

    # Prune expired passing date_str as first arg and conn as second
    pruned2 = homework_service.prune_expired_homework(far_future_date, test_db)
    assert pruned2 >= 1


def test_grade_replacement_and_deduplication(test_db):
    """Verifies that updating absence 'nb' with a grade replaces rather than duplicates."""
    cfg = {
        "enabled": True,
        "demo_mode": False,
        "registered_device": {"device_id": "test"},
    }

    cursor = test_db.cursor()
    cursor.execute(
        """
        INSERT INTO tum_grade_entries 
        (subject, semester, raw_input, numeric_value, weight, category, description, date, counts_in_average)
        VALUES ('Biologia / Chemia', 1, 'nb', NULL, 0.0, 'Kartkówka', 'Genetyka molekularna', '2026-10-14', 0)
        """
    )
    test_db.commit()

    # Incoming live payload where absence became a real grade with comment
    updated_payload = {
        "exams": [],
        "homework": [],
        "grades": [
            {
                "subject": "Biologia",
                "semester": 1,
                "raw_input": "1 (33%)",
                "numeric_value": 1.0,
                "weight": 1.0,
                "category": "Kartkówka",
                "description": "Genetyka molekularna (33%)",
                "date": "2026-10-14",
            }
        ],
    }

    import app.services.vulcan_service as vs
    old_fetch = vs._fetch_live_vulcan_payload
    old_cfg = vs.get_vulcan_config
    vs.get_vulcan_config = lambda: cfg
    vs._fetch_live_vulcan_payload = lambda c, d: updated_payload

    try:
        res = vs.sync_vulcan_data(client_date="2026-10-14", conn=test_db)
        assert res["status"] == "synced"
        assert res["total_grades_active"] >= 1

        # Verify only 1 entry exists for 2026-10-14, updated with 1 (33%)
        cursor.execute("SELECT * FROM tum_grade_entries WHERE date = '2026-10-14'")
        entries = cursor.fetchall()
        assert len(entries) == 1
        assert entries[0]["raw_input"] == "1 (33%)"
        assert entries[0]["numeric_value"] == 1.0

        # Verify running average updated in tum_grades
        cursor.execute("SELECT actual_grade FROM tum_grades WHERE subject = 'Biologia / Chemia' AND semester = 1")
        row = cursor.fetchone()
        assert row is not None
        assert row["actual_grade"] == 1.0
    finally:
        vs._fetch_live_vulcan_payload = old_fetch
        vs.get_vulcan_config = old_cfg


def test_three_day_defense_threshold_and_weekend_tum_linkage(test_db):
    """
    Verifies the reality-grounded 3-day Defense threshold:
    - Exams 4+ days out + daily homework + nb/historical low grades never lock DEFENSE.
    - Exams <= 3 days out trigger DEFENSE/SURGE.
    - Clean Horizon Saturdays inject TUM Deep Work with is_tum_roadmap=True + Physical linkage on training blocks.
    """
    from app.services import today_service

    # Use a fixed Saturday Clean Horizon date: 2026-11-14
    base_date = "2026-11-14"
    exam_4d = "2026-11-18"
    exam_3d = "2026-11-17"
    hw_1d = "2026-11-15"

    cursor = test_db.cursor()
    # Seed historical 'nb' and low grade + normal homework (all should NOT lock DEFENSE)
    cursor.execute(
        """
        INSERT INTO tum_grade_entries
        (subject, semester, raw_input, numeric_value, weight, category, description, date, counts_in_average)
        VALUES ('Fizyka', 1, 'nb', NULL, 0.0, 'Sprawdzian', 'Kinematyka', '2026-10-10', 0)
        """
    )
    cursor.execute(
        """
        INSERT INTO tum_grade_entries
        (subject, semester, raw_input, numeric_value, weight, category, description, date, counts_in_average)
        VALUES ('Biologia', 1, '2.0', 2.0, 1.0, 'Kartkówka', 'Komórka', '2026-10-12', 1)
        """
    )
    homework_service.add_homework("Angielski", "Short workbook exercises p. 14", hw_1d, conn=test_db)
    homework_service.add_exam("Matematyka", "Wielomiany Sprawdzian", exam_4d, conn=test_db)
    test_db.commit()

    workload_4d = workload_governor.get_workload_analysis(target_date_str=base_date, conn=test_db)
    assert workload_4d["mode"] in ("CRUISE", "BALANCED")
    assert workload_4d["immediate_count"] == 0

    # Verify Clean Horizon Saturday binds TUM Deep Work + Physical deliverable on training block
    schedule_pack = today_service.get_schedule_for_date(base_date, conn=test_db)
    blocks = schedule_pack["blocks"]
    tum_blocks = [b for b in blocks if b.get("is_tum_roadmap")]
    assert len(tum_blocks) >= 1
    assert tum_blocks[0].get("deliverable") is not None
    assert "TUM Deep Work" in tum_blocks[0].get("focus", "")
    assert "TUM Roadmap" in tum_blocks[0].get("activity", "")

    training_blocks = [b for b in blocks if b.get("type") == "training"]
    assert len(training_blocks) >= 1
    assert training_blocks[0].get("physical_deliverable") is not None

    # Now add a test strictly 3 days away -> MUST trigger DEFENSE or SURGE
    homework_service.add_exam("Informatyka", "Algorytmy Kartkówka", exam_3d, conn=test_db)
    test_db.commit()

    workload_3d = workload_governor.get_workload_analysis(target_date_str=base_date, conn=test_db)
    assert workload_3d["mode"] in ("DEFENSE", "SURGE")
    assert workload_3d["immediate_count"] == 1


def test_three_tests_this_week_never_cruise_mode(test_db):
    """3+ tests within the 7-day rolling week or ISO-suffixed dates must never leave mode in CRUISE."""
    base_date = "2026-11-15"

    # 3 non-Tier-1 tests later this week (+4d, +6d, +7d) -> outside 3d window, all within 7d
    homework_service.add_exam("Historia", "Sprawdzian I", "2026-11-19", conn=test_db)
    homework_service.add_exam("Biologia", "Kartkówka Genetyka", "2026-11-21", conn=test_db)
    homework_service.add_exam("Geografia", "Sprawdzian Polska", "2026-11-22", conn=test_db)
    test_db.commit()

    analysis = workload_governor.get_workload_analysis(target_date_str=base_date, conn=test_db)
    assert analysis["week_exams_count"] == 3
    assert analysis["cruise_unlocked"] is False
    assert analysis["mode"] != "CRUISE"
    assert analysis["mode"] in ("BALANCED", "DEFENSE", "SURGE")

    # ISO time suffix + trailing space on an exam +2d out must parse and activate acute DEFENSE/SURGE
    test_db.execute(
        "INSERT INTO school_exams (subject, title, exam_date, scope, completed) VALUES ('Fizyka', 'Elektrostatyka', '2026-11-17T00:00:00 ', '', 0)"
    )
    test_db.commit()
    analysis_iso = workload_governor.get_workload_analysis(target_date_str=base_date, conn=test_db)
    assert analysis_iso["immediate_count"] == 1
    assert analysis_iso["mode"] in ("DEFENSE", "SURGE")


def test_same_day_duplicate_score_different_assessments_not_collapsed(test_db):
    """Two different assessments with the same score on the same day must stay distinct (e.g. Math 1 Sprawdzian + 1 Kartkowka + 2 = 1.33)."""
    import app.services.vulcan_service as vs

    cfg = {"enabled": True, "demo_mode": False, "registered_device": {"device_id": "test"}}
    payload = {
        "exams": [],
        "homework": [],
        "grades": [
            {
                "subject": "Matematyka",
                "semester": 1,
                "raw_input": "1",
                "numeric_value": 1.0,
                "weight": 1.0,
                "category": "Sprawdzian",
                "description": "geometria płaska - okręgi i koła",
                "date": "2026-10-26",
            },
            {
                "subject": "Matematyka",
                "semester": 1,
                "raw_input": "1",
                "numeric_value": 1.0,
                "weight": 1.0,
                "category": "Kartkówka",
                "description": "okrąg wpisany, opisany",
                "date": "2026-10-26",
            },
            {
                "subject": "Matematyka",
                "semester": 1,
                "raw_input": "2",
                "numeric_value": 2.0,
                "weight": 1.0,
                "category": "Kartkówka",
                "description": "tożsamości",
                "date": "2026-11-02",
            },
        ],
    }

    old_fetch = vs._fetch_live_vulcan_payload
    old_cfg = vs.get_vulcan_config
    vs.get_vulcan_config = lambda: cfg
    vs._fetch_live_vulcan_payload = lambda c, d: payload
    try:
        vs.sync_vulcan_data(client_date="2026-11-16", conn=test_db)
        rows = test_db.execute(
            "SELECT raw_input, category, description FROM tum_grade_entries WHERE subject = 'Matematyka' AND semester = 1 ORDER BY date ASC, id ASC"
        ).fetchall()
        assert len(rows) == 3
        grade_row = test_db.execute(
            "SELECT actual_grade FROM tum_grades WHERE subject = 'Matematyka' AND semester = 1"
        ).fetchone()
        assert grade_row is not None
        assert grade_row["actual_grade"] == 1.33
    finally:
        vs._fetch_live_vulcan_payload = old_fetch
        vs.get_vulcan_config = old_cfg


def test_exam_week_study_brief_four_tests_allocation(test_db):
    """
    With 4 tests scheduled across a week on a Tuesday (1.5h / 85m net ceiling),
    Harness must rank all 4 tests, allocate tonight's 85m budget across at most 2 targets
    showing exact topics/scopes, park later tests, and bind them into plan_phases.
    """
    tue_date = "2026-11-19"
    # Vulnerable low GPA in Fizyka & Informatyka
    test_db.execute(
        "INSERT INTO tum_grade_entries (subject, semester, raw_input, numeric_value, weight, category, description, date, counts_in_average) VALUES ('Fizyka', 1, '1', 1.0, 1.0, 'Bieżące', 'termodynamika', '2026-10-05', 1)"
    )
    test_db.execute(
        "INSERT INTO tum_grade_entries (subject, semester, raw_input, numeric_value, weight, category, description, date, counts_in_average) VALUES ('Informatyka', 1, '3', 3.0, 1.0, 'Bieżące', 'C++', '2026-09-23', 1)"
    )
    homework_service.add_exam("Język polski", "Poprawa - Rozprawka", "2026-11-20", scope="Wstęp, teza, argument, przykład, kontekst", conn=test_db)
    homework_service.add_exam("Fizyka", "Sprawdzian: Elektrostatyka", "2026-11-21", scope="Prawo Coulomba, pole elektryczne", conn=test_db)
    homework_service.add_exam("Język niemiecki", "Kartkówka: Pogoda", "2026-11-22", scope="Słownictwo pogoda", conn=test_db)
    homework_service.add_exam("Informatyka", "Sprawdzian: NWD/NWW", "2026-11-25", scope="Funkcje i algorytmy NWD, NWW", conn=test_db)
    test_db.commit()

    sched = today_service.get_schedule_for_date(tue_date, conn=test_db)
    brief = sched["workload"].get("exam_week_plan")
    assert brief is not None
    assert brief["total_week_tests"] == 4
    assert brief["budget_minutes"] == 85  # Tue Schedule B: 90m window -> 85m net
    targets = brief["targets"]
    assert len(targets) == 4

    now_items = [t for t in targets if t["role"] in ("NOW", "HEAD_START")]
    parked_items = [t for t in targets if t["role"] == "PARKED"]
    assert 1 <= len(now_items) <= 2
    assert len(parked_items) == 4 - len(now_items)
    assert now_items[0]["subject"] == "Język polski"
    assert sum(t["allocated_minutes"] for t in targets) == 85

    deep_block = next(b for b in sched["blocks"] if b.get("type") == "deep_work")
    assert deep_block["net_minutes"] == 85
    assert deep_block["is_school_dedicated"] is True
    assert sum(p["duration_min"] for p in deep_block["plan_phases"]) == 85


def test_break_sprint_and_low_energy_modes(test_db):
    """Verifies BREAK (vacation/holiday programming sprint) and SURGE_RECOVERY (Low Energy 30m floor)."""
    orig_mode = workload_governor.get_operating_mode()
    try:
        workload_governor.set_operating_mode("BREAK")
        sched_break = today_service.get_schedule_for_date("2026-11-17", conn=test_db)  # Tuesday
        assert sched_break["workload"]["mode"] == "BREAK"
        assert not any("Liceum" in b.get("focus", "") for b in sched_break["blocks"])
        assert any("Gym" in b.get("focus", "") for b in sched_break["blocks"])
        deep_break = next(b for b in sched_break["blocks"] if b.get("type") == "deep_work")
        assert deep_break["net_minutes"] >= 120
        assert sum(p["duration_min"] for p in deep_break["plan_phases"]) == deep_break["net_minutes"]

        workload_governor.set_operating_mode("SURGE_RECOVERY")
        sched_low = today_service.get_schedule_for_date("2026-11-17", conn=test_db)
        assert sched_low["workload"]["mode"] == "SURGE_RECOVERY"
        deep_low = next(b for b in sched_low["blocks"] if b.get("type") == "deep_work")
        assert deep_low["net_minutes"] <= 35
    finally:
        workload_governor.set_operating_mode(orig_mode)





