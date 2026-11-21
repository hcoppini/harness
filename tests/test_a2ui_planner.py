"""Tests for Harness A2UI Protocol (Outings, Dynamic Schedule Rearrangement, Ollama/Cloud adapter, and UI renderer)."""

import json
import shutil
import sqlite3
import subprocess
from pathlib import Path

import pytest

from app.db import init_db
from app.services import a2ui_planner_service, homework_service, today_service
from engine import workload_governor


@pytest.fixture
def a2ui_env(tmp_path, monkeypatch):
    db_file = tmp_path / "test_a2ui.db"
    init_db(db_file)
    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row

    tw_file = tmp_path / "travel_windows.json"
    tw_file.write_text(
        json.dumps(
            {
                "windows": [
                    {
                        "id": "us_2026",
                        "name": "US Deployment",
                        "destination": "United States",
                        "type": "travel",
                        "confirmed": True,
                        "start_date": "2026-10-04",
                        "end_date": "2026-10-18",
                        "description": "Confirmed US trip.",
                    }
                ]
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    op_file = tmp_path / "operating_mode.json"

    monkeypatch.setattr(workload_governor, "TRAVEL_WINDOWS_FILE", tw_file)
    monkeypatch.setattr(workload_governor, "OPERATING_MODE_FILE", op_file)
    monkeypatch.setattr(a2ui_planner_service, "TRAVEL_WINDOWS_FILE", tw_file)

    yield conn, tw_file
    conn.close()


def test_announce_december_trip_produces_valid_a2ui_envelope_and_schedule_diff(a2ui_env, monkeypatch):
    """Announcing 'trip on December 23-27' emits strict A2UI v1.0 envelope with catalog-bound components and exam conflict check."""
    conn, _ = a2ui_env
    # Force deterministic offline fallback (simulating Ollama asleep & no cloud key)
    monkeypatch.setattr(a2ui_planner_service, "_call_ollama_json", lambda *a, **k: None)
    monkeypatch.setattr(a2ui_planner_service, "_call_free_cloud_json", lambda *a, **k: None)

    homework_service.add_exam("Matematyka", "Sprawdzian: Funkcje", "2026-12-24", scope="Funkcje kwadratowe", conn=conn)
    conn.commit()

    res = a2ui_planner_service.process_plan_message(
        "I have a family trip on December 23-27 to Krakow",
        stance="coach",
        date_str="2026-11-19",
        conn=conn,
    )

    assert "agent_to_renderer" in res
    env = res["agent_to_renderer"]
    assert env["surfaceId"].startswith("outing_")
    messages = env["messages"]
    msg_keys = [next(iter(m.keys())) for m in messages]
    assert "createSurface" in msg_keys
    assert "updateDataModel" in msg_keys
    assert "updateComponents" in msg_keys

    data_model = next(m["updateDataModel"]["data"] for m in messages if "updateDataModel" in m)
    outing = data_model["outing"]
    assert outing["start_date"] == "2026-12-23"
    assert outing["end_date"] == "2026-12-27"
    assert outing["mode"] == "travel"
    assert "krakow" in outing["destination"].lower()
    assert len(data_model["schedule_diff"]) == 5
    assert len(data_model["affected_exams"]) == 1
    assert data_model["affected_exams"][0]["subject"] == "Matematyka"

    components = next(m["updateComponents"]["components"] for m in messages if "updateComponents" in m)
    allowed = set(a2ui_planner_service.A2UI_CATALOG.keys())
    assert len(components) >= 4
    for comp in components:
        assert comp["@catalogId"] in allowed


def test_ollama_structured_json_provider_and_apply_outing_mutates_workload(a2ui_env, monkeypatch):
    """When Ollama returns structured outing JSON, applying the A2UI action persists to travel_windows.json and switches workload mode live."""
    conn, tw_file = a2ui_env

    def fake_ollama(system_prompt, user_prompt, model_name=None):
        return (
            {
                "intent": "plan_outing",
                "reply": "Logged your Dec 23-27 trip preview. Review the rearranged 5-day travel floor and hit Apply.",
                "outing": {
                    "name": "Winter Family Trip",
                    "destination": "Zakopane",
                    "start_date": "2026-12-23",
                    "end_date": "2026-12-27",
                    "mode": "travel",
                    "description": "Mountain family trip with 30-45m daily maintenance anchor.",
                },
            },
            "ollama:llama3:latest",
        )

    monkeypatch.setattr(a2ui_planner_service, "_call_ollama_json", fake_ollama)

    res = a2ui_planner_service.process_plan_message(
        "trip dec 23 to dec 27 zakopane",
        stance="coach",
        date_str="2026-11-19",
        conn=conn,
    )
    env = res["agent_to_renderer"]
    assert env["provider"] == "ollama:llama3:latest"

    data_model = next(m["updateDataModel"]["data"] for m in env["messages"] if "updateDataModel" in m)
    apply_res = a2ui_planner_service.apply_a2ui_action("apply_outing", data_model, conn=conn)
    assert apply_res["success"] is True
    saved_id = apply_res["outing"]["id"]

    # Verify persisted in travel_windows.json
    saved_data = json.loads(tw_file.read_text(encoding="utf-8"))
    assert any(w["id"] == saved_id and w["confirmed"] is True for w in saved_data["windows"])

    # Verify Workload Governor & Today Schedule immediately adapt on Dec 25!
    analysis = workload_governor.get_workload_analysis("2026-12-25", conn=conn)
    assert analysis["mode"] == "TRAVEL"
    assert analysis["travel_destination"] == "Zakopane"

    sched = today_service.get_schedule_for_date("2026-12-25", conn=conn)
    assert sched["workload"]["is_travel_mode"] is True

    # Delete outing via A2UI action and verify restoration
    del_res = a2ui_planner_service.apply_a2ui_action("delete_outing", {"outing_id": saved_id}, conn=conn)
    assert del_res["success"] is True
    analysis_after = workload_governor.get_workload_analysis("2026-12-25", conn=conn)
    assert analysis_after["mode"] != "TRAVEL"


def test_a2ui_frontend_renderer_maintains_obsidian_aesthetic_and_escapes_xss():
    """Node VM test verifying js/plans_logs.js renders A2UI catalog natively with Harness classes and escapes untrusted strings."""
    node_bin = shutil.which("node")
    assert node_bin, "Node.js is required to test js/plans_logs.js"

    root = Path(__file__).resolve().parent.parent
    js_path = root / "js" / "plans_logs.js"
    assert js_path.exists(), "js/plans_logs.js must exist"

    probe = r"""
const fs = require("fs");
const vm = require("vm");
const elements = {
  a2uiSurfaceMount: { innerHTML: "" },
};
const sandbox = {
  Date, Math, Number, String, Boolean, Array, Object, Set, Map, JSON, RegExp, Error,
  encodeURIComponent, decodeURIComponent, console, setTimeout, clearTimeout,
  localStorage: { getItem: () => null, setItem: () => {} },
  window: {},
  document: {
    getElementById: (id) => elements[id] || null,
    querySelector: () => null,
    querySelectorAll: () => [],
  },
};
sandbox.window = sandbox;
vm.runInNewContext(fs.readFileSync("js/plans_logs.js", "utf8"), sandbox);

const envelope = {
  surfaceId: "outing_test_1",
  provider: "ollama:llama3:latest",
  messages: [
    { createSurface: { title: "Outing Proposal" } },
    {
      updateDataModel: {
        data: {
          outing: {
            name: "<img src=x onerror=alert(1)> Trip",
            destination: "Krakow",
            start_date: "2026-12-23",
            end_date: "2026-12-27",
            mode: "travel",
            description: "Family trip",
          },
          schedule_diff: [
            { date: "2026-12-23", weekday: "Wednesday", before: "School + 60m + Boxing", after: "Travel Floor (45m)", badge: "TRAVEL" },
          ],
          affected_exams: [],
        },
      },
    },
    {
      updateComponents: {
        components: [
          { id: "h1", "@catalogId": "Heading", eyebrow: "A2UI SURFACE", title: "Dec 23-27 Trip", badge: "PROPOSAL" },
          { id: "c1", "@catalogId": "OutingSummaryCard" },
          { id: "d1", "@catalogId": "DateRangeField", label: "Dates", startPath: "@path:/outing/start_date", endPath: "@path:/outing/end_date" },
          { id: "m1", "@catalogId": "ModeSelector", label: "Protocol", valuePath: "@path:/outing/mode", options: [{ value: "travel", label: "Travel" }, { value: "break", label: "Break Sprint" }] },
          { id: "s1", "@catalogId": "ScheduleDiff", title: "Rearranged Plan" },
          { id: "a1", "@catalogId": "ActionBar", actions: [{ label: "Apply to Harness", style: "primary", "@call": "apply_outing" }] },
        ],
      },
    },
  ],
};

sandbox.PlansLogs.applyA2UIEnvelope(envelope);
const html = elements.a2uiSurfaceMount.innerHTML;
console.log(JSON.stringify({
  hasObsidianClasses: html.includes("monotone-card") && html.includes("mono-chip") && html.includes("a2ui-surface"),
  hasDates: html.includes("2026-12-23") && html.includes("2026-12-27"),
  hasDiff: html.includes("Travel Floor (45m)"),
  hasApplyBtn: html.includes("apply_outing"),
  xssEscaped: !html.includes("<img src=x") && html.includes("&lt;img src=x"),
}));
"""
    proc = subprocess.run([node_bin, "-e", probe], cwd=str(root), capture_output=True, text=True, check=True)
    out = json.loads(proc.stdout.strip())
    assert out["hasObsidianClasses"] is True
    assert out["hasDates"] is True
    assert out["hasDiff"] is True
    assert out["hasApplyBtn"] is True
    assert out["xssEscaped"] is True


def test_travel_windows_sqlite_supabase_sync_and_heatmap_tracking(a2ui_env, monkeypatch):
    """Outings persist to SQLite travel_windows, sync via Supabase app_settings, and appear visually on future heatmap cells."""
    from app.services import dashboard_service, sync_service

    conn, _ = a2ui_env

    # 1. Apply outing via A2UI action -> must write to SQLite travel_windows table AND JSON mirror
    res = a2ui_planner_service.apply_a2ui_action(
        "apply_outing",
        {
            "outing": {
                "name": "Krakow Christmas Trip",
                "destination": "Krakow",
                "start_date": "2026-12-23",
                "end_date": "2026-12-27",
                "mode": "travel",
                "description": "Family trip to Krakow",
            }
        },
        conn=conn,
    )
    assert res["success"] is True
    saved_id = res["outing"]["id"]

    row = conn.execute("SELECT * FROM travel_windows WHERE id = ?", (saved_id,)).fetchone()
    assert row is not None
    assert row["destination"] == "Krakow"
    assert row["type"] == "travel"
    assert int(row["confirmed"]) == 1

    # 2. Verify heatmap marks future outing cells with has_outing + outing_type + tooltip activity
    hm = dashboard_service.get_heatmap_data(
        start_date="2026-12-20",
        days=14,
        end_date="2026-11-19",
        conn=conn,
        include_git=False,
    )
    day_by_date = {d["date"]: d for w in hm["weeks"] for d in w["days"] if d}
    dec25 = day_by_date["2026-12-25"]
    assert dec25["is_future"] is True
    assert dec25["has_outing"] is True
    assert dec25["outing_type"] == "travel"
    assert "Krakow" in (dec25.get("outing_name") or "") or any("Krakow" in a for a in dec25["activities"])
    assert any("[TRAVEL" in a for a in dec25["activities"])

    # 3. Verify bidirectional Supabase app_settings sync ('cloud_travel_windows')
    cloud_store = {}

    def fake_supa(endpoint, method="GET", payload=None, headers_extra=None):
        if method == "GET" and endpoint.startswith("app_settings"):
            return [{"key": k, "value": v} for k, v in cloud_store.items()]
        if method == "POST" and endpoint.startswith("app_settings"):
            cloud_store[payload["key"]] = payload["value"]
            return [payload]
        return []

    monkeypatch.setattr(sync_service, "_make_supabase_request", fake_supa)
    monkeypatch.setattr(sync_service, "DATA_DIR", a2ui_env[1].parent)
    synced = sync_service.sync_travel_windows(conn)
    assert synced >= 1
    assert "cloud_travel_windows" in cloud_store
    assert any(w["id"] == saved_id for w in cloud_store["cloud_travel_windows"]["windows"])

    # Simulate fresh device (empty SQLite table) pulling the outing back from Supabase!
    conn.execute("DELETE FROM travel_windows")
    conn.commit()
    a2ui_env[1].write_text(json.dumps({"windows": []}), encoding="utf-8")
    pulled = sync_service.sync_travel_windows(conn)
    assert pulled >= 1
    restored = conn.execute("SELECT * FROM travel_windows WHERE id = ?", (saved_id,)).fetchone()
    assert restored is not None
    assert restored["destination"] == "Krakow"
