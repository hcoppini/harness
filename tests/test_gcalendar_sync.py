"""
Tests for Harness <-> Google Calendar Cross-Sync Engine & Conflict-Aware Schedule Optimizer.
"""

import json
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.db import init_db
from app.services import gcalendar_service, homework_service, today_service
from engine import workload_governor


@pytest.fixture
def gcal_env(tmp_path, monkeypatch):
    """Creates an isolated SQLite DB and data dir for Google Calendar tests."""
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    db_path = data_dir / "test_harness.db"

    # Copy static schedule & timetable JSONs into isolated data dir
    src_data = Path(__file__).resolve().parent.parent / "data"
    for fname in ("schedules.json", "gym_routines.json", "school_timetable.json", "metro_roadmap.json"):
        src_file = src_data / fname
        if src_file.exists():
            (data_dir / fname).write_text(src_file.read_text(encoding="utf-8"), encoding="utf-8")

    monkeypatch.setenv("HARNESS_DB_PATH", str(db_path))
    monkeypatch.setattr("app.db.DEFAULT_DB_PATH", db_path)
    monkeypatch.setattr("app.db.DATA_DIR", data_dir)
    monkeypatch.setattr(today_service, "DATA_DIR", data_dir)
    monkeypatch.setattr(workload_governor, "DATA_DIR", data_dir)
    monkeypatch.setattr(workload_governor, "OPERATING_MODE_FILE", data_dir / "operating_mode.json")
    monkeypatch.setattr(gcalendar_service, "DATA_DIR", data_dir)
    monkeypatch.setattr(gcalendar_service, "CONFIG_FILE", data_dir / "gcalendar_config.json")

    from app.services import school_service
    monkeypatch.setattr(school_service, "DATA_DIR", data_dir)
    monkeypatch.setattr(school_service, "CACHED_PLAN_FILE", data_dir / "school_timetable.json")

    from engine import kill_list_controller
    monkeypatch.setattr(kill_list_controller, "DATA_DIR", data_dir)

    init_db(db_path)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    yield conn, data_dir, db_path
    conn.close()


def test_gcal_config_lifecycle_and_secret_redaction(gcal_env):
    conn, data_dir, _ = gcal_env

    cfg = gcalendar_service.get_gcalendar_config()
    assert cfg["mode"] == "unconfigured"
    assert cfg["sync_exams"] is True
    assert cfg["sync_plan_blocks"] is True
    assert cfg["sync_school_timetable"] is True
    assert cfg["auto_optimize_schedule"] is True

    # Import OAuth client JSON (installed desktop format)
    client_payload = json.dumps({
        "installed": {
            "client_id": "123456-test.apps.googleusercontent.com",
            "client_secret": "GOCSPX-super-secret-value",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    })
    res = gcalendar_service.import_oauth_credentials(client_payload)
    assert res["success"] is True
    assert res["client_id"] == "123456-test.apps.googleusercontent.com"

    # Status returned to UI must NEVER expose raw client_secret or refresh_token
    status = gcalendar_service.get_gcalendar_status(conn=conn)
    assert status["has_client_id"] is True
    assert status["has_client_secret"] is True
    assert "GOCSPX-super-secret-value" not in json.dumps(status)


def test_warsaw_dst_and_time_window_parsing():
    # Winter (CET +01:00)
    assert gcalendar_service.format_local_iso("2026-11-16", "14:30") == "2026-11-16T14:30:00+01:00"
    # Summer (CEST +02:00)
    assert gcalendar_service.format_local_iso("2026-06-15", "14:30") == "2026-06-15T14:30:00+02:00"

    assert gcalendar_service.parse_time_window("14:30 – 16:30") == (14 * 60 + 30, 16 * 60 + 30)
    assert gcalendar_service.parse_time_window("8:50- 9:35") == (8 * 60 + 50, 9 * 60 + 35)
    assert gcalendar_service.parse_time_window("17:20 – 20:30/21:00") == (17 * 60 + 20, 20 * 60 + 30)
    assert gcalendar_service.parse_time_window("All Day") is None
    assert gcalendar_service.parse_time_window("13:00 onwards") is None


def test_ics_feed_generation_and_parsing(gcal_env):
    conn, _, _ = gcal_env
    target_date = "2026-11-16"  # Monday

    homework_service.add_exam(
        subject="Matematyka",
        title="Sprawdzian: Funkcje",
        exam_date=target_date,
        scope="Funkcje liniowe i kwadratowe",
        conn=conn,
    )
    homework_service.add_homework(
        subject="Fizyka",
        title="Zad. 1-5 str. 42",
        due_date=target_date,
        priority=2,
        conn=conn,
    )

    ics_text = gcalendar_service.generate_ics_feed(days_ahead=3, start_date=target_date, conn=conn)
    assert "BEGIN:VCALENDAR" in ics_text
    assert "END:VCALENDAR" in ics_text
    assert "Sprawdzian: Funkcje" in ics_text
    assert "Zad. 1-5 str. 42" in ics_text
    assert "SGH Library" in ics_text or "Deep Work" in ics_text
    assert "fizyka" in ics_text.lower()

    # Now parse an external Google Calendar ICS payload (with UTC, TZID, all-day, and weekly RRULE)
    external_ics = "\r\n".join([
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "BEGIN:VEVENT",
        "UID:dentist-123@google.com",
        "DTSTART;TZID=Europe/Warsaw:20261117T143000",
        "DTEND;TZID=Europe/Warsaw:20261117T160000",
        "SUMMARY:Dentist Appointment",
        "LOCATION:Warsaw Center",
        "END:VEVENT",
        "BEGIN:VEVENT",
        "UID:tutor-weekly@google.com",
        "DTSTART:20261109T180000Z",
        "DTEND:20261109T190000Z",
        "RRULE:FREQ=WEEKLY;COUNT=4",
        "SUMMARY:German Speaking Session",
        "END:VEVENT",
        "BEGIN:VEVENT",
        "UID:test-from-gcal@google.com",
        "DTSTART;VALUE=DATE:20261119",
        "DTEND;VALUE=DATE:20261120",
        "SUMMARY:[Test] Chemia - Alkany i Alkeny",
        "DESCRIPTION:Rozdzial 3",
        "END:VEVENT",
        "END:VCALENDAR",
    ])
    parsed = gcalendar_service.parse_ics_content(external_ics, start_date="2026-11-16", end_date="2026-11-22")
    summaries = [e["summary"] for e in parsed]
    assert "Dentist Appointment" in summaries
    assert "German Speaking Session" in summaries
    assert "[Test] Chemia - Alkany i Alkeny" in summaries

    dentist = next(e for e in parsed if e["summary"] == "Dentist Appointment")
    assert dentist["date"] == "2026-11-17"
    assert dentist["start_time"] == "14:30"
    assert dentist["end_time"] == "16:00"

    # Weekly recurring event (Nov 9 -> Nov 16 in CET +01:00 => 18:00Z = 19:00 local)
    german_on_nov16 = next(e for e in parsed if e["summary"] == "German Speaking Session" and e["date"] == "2026-11-16")
    assert german_on_nov16["start_time"] == "19:00"
    assert german_on_nov16["end_time"] == "20:00"


def test_conflict_aware_schedule_optimization(gcal_env):
    conn, _, _ = gcal_env
    tue_date = "2026-11-17"  # Tuesday (Schedule B: School 08:00-14:15, Deep Work 14:30-16:30, Gym 17:45-18:45)

    # Insert an external Google Calendar event overlapping SGH Deep Work (14:30-16:00)
    conn.execute(
        """
        INSERT INTO gcal_events (
            event_id, calendar_id, summary, description, location,
            date, start_time, end_time, is_all_day, status, is_harness_managed, source
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 'confirmed', 0, 'gcal_api')
        """,
        ("ext-dentist", "primary", "Orthodontist Checkup", "Clinic", "Mokotow", tue_date, "14:30", "16:00"),
    )
    conn.commit()

    sched = today_service.get_schedule_for_date(tue_date, conn=conn)
    assert "calendar_events" in sched
    assert len(sched["calendar_events"]) == 1
    assert sched["calendar_events"][0]["summary"] == "Orthodontist Checkup"

    opt = sched.get("calendar_optimization", {})
    assert opt.get("conflicts_detected", 0) >= 1
    assert opt.get("blocks_optimized", 0) >= 1

    # Verify Deep Work block index stayed valid, moved out of 14:30-16:00 conflict, and phases sum to net_minutes
    dw_block = next(b for b in sched["blocks"] if b.get("type") == "deep_work")
    assert dw_block.get("gcal_optimized") is True
    assert dw_block.get("original_time") == "14:30 – 16:00"
    assert "Orthodontist Checkup" in dw_block.get("gcal_adjustment_reason", "")

    new_win = gcalendar_service.parse_time_window(dw_block["time"])
    assert new_win is not None
    # Must NOT overlap 14:30-16:00 (870-960)
    assert new_win[1] <= 14 * 60 + 30 or new_win[0] >= 16 * 60
    # Plan phases must exactly sum to net_minutes
    if dw_block.get("plan_phases"):
        assert sum(p["duration_min"] for p in dw_block["plan_phases"]) == dw_block["net_minutes"]


def test_user_override_in_gcal_sync_map_respected(gcal_env):
    conn, _, _ = gcal_env
    mon_date = "2026-11-16"  # Monday (SGH Deep Work is block index 2)

    base_sched = today_service.get_schedule_for_date(mon_date, conn=conn)
    dw_idx = next(i for i, b in enumerate(base_sched["blocks"]) if b.get("type") == "deep_work")

    # Simulate user dragging Deep Work in Google Calendar to 15:00 - 16:40
    conn.execute(
        """
        INSERT INTO gcal_sync_map (
            harness_key, harness_kind, calendar_id, event_id, sync_hash,
            override_date, override_start, override_end, user_deleted
        ) VALUES (?, 'plan_block', 'harness-cal', 'evt-dw-1', 'hash1', ?, '15:00', '16:40', 0)
        """,
        (f"plan:{mon_date}:{dw_idx}", mon_date),
    )
    conn.commit()

    updated_sched = today_service.get_schedule_for_date(mon_date, conn=conn)
    dw_block = updated_sched["blocks"][dw_idx]
    assert dw_block["time"] == "15:00 – 16:40"
    assert dw_block.get("gcal_user_override") is True
    assert sum(p["duration_min"] for p in dw_block["plan_phases"]) == dw_block["net_minutes"]


def test_oauth_two_way_cross_sync_push_pull_and_cleanup(gcal_env, monkeypatch):
    conn, _, _ = gcal_env
    mon_date = "2026-11-16"  # Monday: Matematyka at 12:40-13:25 & 13:30-14:15 in school_timetable.json

    # Add upcoming exam in Harness
    exam = homework_service.add_exam(
        subject="Matematyka",
        title="Sprawdzian: Funkcje",
        exam_date=mon_date,
        scope="Funkcje liniowe",
        conn=conn,
    )

    cfg = gcalendar_service.get_gcalendar_config()
    cfg.update({
        "mode": "oauth",
        "client_id": "cid",
        "client_secret": "csec",
        "refresh_token": "rtok",
        "access_token": "atok",
        "token_expires_at": "2099-01-01T00:00:00",
        "use_dedicated_calendar": True,
        "target_calendar_id": "",
        "sync_horizon_days": 2,
    })
    gcalendar_service.save_gcalendar_config(cfg)

    created_events = []
    patched_events = []
    deleted_event_ids = []
    remote_store = {}

    def fake_api_request(method, path, token, payload=None, params=None):
        # 1. UserInfo
        if "userinfo" in path:
            return {"email": "heitor@example.com"}
        # 2. CalendarList
        if path == "/users/me/calendarList":
            return {"items": [{"id": "primary", "summary": "Primary", "primary": True}]}
        # 3. Create dedicated calendar
        if method == "POST" and path == "/calendars":
            return {"id": "harness-cal-id", "summary": payload["summary"]}
        # 4. List events
        if method == "GET" and "/events" in path:
            if "primary" in path:
                return {
                    "items": [
                        {
                            "id": "ext-meeting-1",
                            "summary": "Family Dinner",
                            "status": "confirmed",
                            "start": {"dateTime": "2026-11-16T15:00:00+01:00"},
                            "end": {"dateTime": "2026-11-16T16:15:00+01:00"},
                        },
                        {
                            "id": "ext-gcal-test-1",
                            "summary": "[Test] Fizyka - Dynamika",
                            "description": "Zasady Newtona",
                            "status": "confirmed",
                            "start": {"date": "2026-11-18"},
                            "end": {"date": "2026-11-19"},
                        },
                    ]
                }
            return {"items": list(remote_store.values())}
        # 5. Insert event
        if method == "POST" and "/events" in path:
            eid = f"gcal-{len(created_events) + 1}"
            evt = dict(payload)
            evt["id"] = eid
            evt["etag"] = '"e1"'
            created_events.append(evt)
            remote_store[eid] = evt
            return evt
        # 6. Patch event
        if method == "PATCH" and "/events/" in path:
            eid = path.split("/events/")[-1]
            patched_events.append((eid, payload))
            remote_store[eid].update(payload)
            return remote_store[eid]
        # 7. Delete event
        if method == "DELETE" and "/events/" in path:
            eid = path.split("/events/")[-1]
            deleted_event_ids.append(eid)
            remote_store.pop(eid, None)
            return {}
        return {}

    monkeypatch.setattr(gcalendar_service, "_gcal_api_request", fake_api_request)

    # First sync: pulls Family Dinner + [Test] Fizyka, optimizes Monday Deep Work around 15:00-16:15, pushes events!
    res1 = gcalendar_service.sync_all_gcalendar(start_date=mon_date, conn=conn)
    assert res1["status"] == "synced"
    assert res1["pulled_events"] >= 2
    assert res1["imported_tests"] == 1
    assert res1["pushed_created"] > 0

    # Verify [Test] Fizyka was imported into school_exams
    exams = homework_service.get_upcoming_exams(today_str=mon_date, conn=conn)
    assert any("Fizyka" in e["subject"] and "Dynamika" in e["title"] for e in exams)

    # Verify Matematyka exam event was matched to Monday's Matematyka lesson time (12:40)
    math_evt = next(
        e for e in created_events
        if e.get("extendedProperties", {}).get("private", {}).get("harness_key") == f"exam:{exam['id']}"
    )
    assert "12:40:00" in math_evt["start"]["dateTime"]

    # Second sync with zero changes -> idempotent (0 creates, 0 patches, 0 duplicate tests)
    res2 = gcalendar_service.sync_all_gcalendar(start_date=mon_date, conn=conn)
    assert res2["pushed_created"] == 0
    assert res2["pushed_updated"] == 0
    assert res2["imported_tests"] == 0

    # Delete the Matematyka exam in Harness -> third sync cleans up its Google Calendar event!
    homework_service.delete_exam(exam["id"], conn=conn)
    res3 = gcalendar_service.sync_all_gcalendar(start_date=mon_date, conn=conn)
    assert res3["pushed_deleted"] >= 1
    assert math_evt["id"] in deleted_event_ids


def test_private_ical_url_pull_rejects_unsafe_schemes(gcal_env):
    conn, _, _ = gcal_env
    assert gcalendar_service.is_safe_calendar_url("https://calendar.google.com/calendar/ical/abc/basic.ics") is True
    assert gcalendar_service.is_safe_calendar_url("file:///etc/passwd") is False
    assert gcalendar_service.is_safe_calendar_url("javascript:alert(1)") is False
    assert gcalendar_service.is_safe_calendar_url("http://127.0.0.1:8080/cal.ics") is False


def test_flask_gcalendar_and_ics_endpoints(gcal_env, monkeypatch):
    import server
    conn, _, _ = gcal_env

    # Ensure isolated DB is used by Flask routes too
    homework_service.add_exam(
        subject="Matematyka",
        title="Sprawdzian: Całki",
        exam_date="2026-11-16",
        scope="Całkowanie przez części",
        conn=conn,
    )

    client = server.app.test_client()

    # 1. Status endpoint never exposes secrets
    cred_res = client.post(
        "/api/gcalendar/credentials",
        json={
            "credentials_json": json.dumps({
                "web": {
                    "client_id": "web-client-123.apps.googleusercontent.com",
                    "client_secret": "SECRET_DO_NOT_LEAK",
                }
            })
        },
    )
    assert cred_res.status_code == 200
    assert cred_res.get_json()["success"] is True

    status_res = client.get("/api/gcalendar/status")
    assert status_res.status_code == 200
    status_body = status_res.get_json()
    assert status_body["has_client_id"] is True
    assert "SECRET_DO_NOT_LEAK" not in json.dumps(status_body)

    # 2. Settings endpoint rejects unsafe SSRF/file URLs and accepts valid HTTPS
    bad_cfg = client.post("/api/gcalendar/settings", json={"private_ical_urls": ["file:///etc/passwd"]})
    assert bad_cfg.status_code == 400

    good_cfg = client.post("/api/gcalendar/settings", json={"sync_horizon_days": 7})
    assert good_cfg.status_code == 200
    assert good_cfg.get_json()["sync_horizon_days"] == 7

    # 3. Live RFC 5545 .ics feed endpoint returns valid calendar containing exam
    tok = status_body["ics_feed_token"]
    ics_res = client.get(f"/api/calendar.ics?days=3&start_date=2026-11-16&token={tok}")
    assert ics_res.status_code == 200
    assert "text/calendar" in ics_res.content_type
    ics_text = ics_res.get_data(as_text=True)
    assert "BEGIN:VCALENDAR" in ics_text
    assert "Sprawdzian: Całki" in ics_text

    # 4. External remote request without valid token is blocked when token exists
    remote_denied = client.get(
        "/api/calendar.ics?token=wrong-token",
        environ_base={"REMOTE_ADDR": "8.8.8.8"},
    )
    assert remote_denied.status_code == 401
