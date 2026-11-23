import json
import shutil
import sqlite3
import subprocess
from pathlib import Path

import pytest

from app.db import init_db
from app.services import dashboard_service


REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def test_db(tmp_path):
    db_path = tmp_path / "test_heatmap_exams.db"
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


def _flatten_days(heatmap):
    days = {}
    for w in heatmap["weeks"]:
        for d in w["days"]:
            if d is not None:
                days[d["date"]] = d
    return days


def test_heatmap_exams_and_homework_today_and_date_normalization(test_db):
    cursor = test_db.cursor()
    # Today exam with ISO time suffix, future exam with trailing space, completed exam
    cursor.execute(
        "INSERT INTO school_exams (id, subject, title, exam_date, scope, completed) VALUES (1, 'Matematyka R', 'Kartkowka Logarytmy', '2026-11-15T00:00:00', '', 0)"
    )
    cursor.execute(
        "INSERT INTO school_exams (id, subject, title, exam_date, scope, completed) VALUES (2, 'Polski', 'Rozprawka', '2026-11-17  ', '', 0)"
    )
    cursor.execute(
        "INSERT INTO school_exams (id, subject, title, exam_date, scope, completed) VALUES (3, 'Fizyka', 'Done Exam', '2026-11-19', '', 1)"
    )
    # Today & future homework
    cursor.execute(
        "INSERT INTO homework_items (id, subject, title, due_date, completed, source, priority) VALUES (10, 'Angielski', 'Essay draft', '2026-11-15T12:00:00', 0, 'vulcan', 1)"
    )
    cursor.execute(
        "INSERT INTO homework_items (id, subject, title, due_date, completed, source, priority) VALUES (11, 'Fizyka', 'Zadania 1-5', '2026-11-16 ', 0, 'vulcan', 1)"
    )
    test_db.commit()

    heatmap = dashboard_service.get_heatmap_data(conn=test_db, end_date="2026-11-15")
    days = _flatten_days(heatmap)

    # Today must surface exam/homework indicators & activity labels cleanly
    today_cell = days["2026-11-15"]
    assert today_cell["is_today"] is True
    assert today_cell["has_exam"] is True
    assert today_cell["exam_count"] == 1
    assert any("[UPCOMING TEST] Matematyka R: Kartkowka Logarytmy" in a for a in today_cell["activities"])
    assert today_cell["has_homework"] is True
    assert today_cell["homework_count"] == 1
    assert any("[HOMEWORK DUE] Angielski: Essay draft" in a for a in today_cell["activities"])

    # Future exam with whitespace date must appear
    future_exam_cell = days["2026-11-17"]
    assert future_exam_cell["is_future"] is True
    assert future_exam_cell["has_exam"] is True
    assert future_exam_cell["exam_count"] == 1
    assert any("[UPCOMING TEST] Polski: Rozprawka" in a for a in future_exam_cell["activities"])

    # Completed exam must NOT appear
    done_cell = days["2026-11-19"]
    assert done_cell["has_exam"] is False
    assert done_cell["exam_count"] == 0

    # Future homework with trailing space must appear
    hw_cell = days["2026-11-16"]
    assert hw_cell["has_homework"] is True
    assert hw_cell["homework_count"] == 1
    assert any("[HOMEWORK DUE] Fizyka: Zadania 1-5" in a for a in hw_cell["activities"])


def test_css_supports_today_exam_and_homework_dots():
    for rel in ["css/app.css"]:
        css = (REPO_ROOT / rel).read_text(encoding="utf-8")
        assert ".heatmap-cell.cell-today.has-exam::after" in css
        assert ".heatmap-cell.cell-today.has-homework::before" in css


def test_js_api_bridge_heatmap_exam_homework_overlay(tmp_path):
    if not shutil.which("node"):
        pytest.skip("Node.js not available in test environment")

    bridge_path = REPO_ROOT / "js" / "api_bridge.js"
    test_script = tmp_path / "verify_bridge.js"
    test_script.write_text(
        """
const assert = require("assert");
const fs = require("fs");
const vm = require("vm");

const bridgePath = process.argv[2];
const bridgeCode = fs.readFileSync(bridgePath, "utf8");

function makeMockDashboardResponse() {
  const mkDay = (date, extras = {}) => ({
    date,
    count: extras.count || 0,
    level: extras.level || 0,
    total_boxes: 14,
    is_future: date > "2026-11-15",
    is_today: date === "2026-11-15",
    has_exam: Boolean(extras.has_exam),
    exam_count: extras.exam_count || 0,
    exams: extras.exams || [],
    has_homework: Boolean(extras.has_homework),
    homework_count: extras.homework_count || 0,
    homework: extras.homework || [],
    activities: extras.activities || [],
  });

  // Stale Nov-1 server DB: only 12-04 exam, 11-28 stale deleted exam, 11-20 homework
  return {
    metrics: { total_contributions: 10 },
    today_velocity: { checked_boxes: 0, total_boxes: 14, percentage: 0, checked_tasks: 0, kill_list_completed: 0 },
    academic_balance: {
      mode: "CRUISE",
      badge_class: "optimal",
      nearest_exam: { id: 1009, subject: "Niemiecki", title: "Old Exam", exam_date: "2026-12-04", days_left: 19 },
      total_exams_count: 1,
      urgent_homework_count: 1,
      description: "Stale server description",
    },
    heatmap: {
      total_contributions: 10,
      weeks: [
        {
          days: [
            mkDay("2026-11-15"),
            mkDay("2026-11-16"),
            mkDay("2026-11-17"),
            mkDay("2026-11-19"),
            mkDay("2026-11-20", { has_homework: true, homework_count: 1, homework: [{ id: 41, subject: "Historia", title: "Old HW", due_date: "2026-11-20" }], activities: ["[HOMEWORK DUE] Historia: Old HW"] }),
            mkDay("2026-11-25"),
            mkDay("2026-11-28", { has_exam: true, exam_count: 1, exams: [{ id: 1008, subject: "Stale", title: "Deleted Exam", exam_date: "2026-11-28" }], activities: ["[UPCOMING TEST] Stale: Deleted Exam"] }),
            mkDay("2026-12-04", { has_exam: true, exam_count: 1, exams: [{ id: 1009, subject: "Niemiecki", title: "Exam Dec", exam_date: "2026-12-04" }], activities: ["[UPCOMING TEST] Niemiecki: Exam Dec"] }),
          ],
        },
      ],
    },
    radar: {
      exams: [{ id: 1009, subject: "Niemiecki", title: "Exam Dec", exam_date: "2026-12-04", days_left: 19 }],
      homework: [{ id: 41, subject: "Historia", title: "Old HW", due_date: "2026-11-20", days_left: 5 }],
    },
    upcoming: [],
  };
}

const supabaseExams = [
  { id: 1013, subject: "Historia", title: "Sprawdzian I", exam_date: "2026-11-17", scope: "", completed: false },
  { id: 1010, subject: "Matematyka R", title: "Sprawdzian Funkcje", exam_date: "2026-11-19", scope: "", completed: false },
  { id: 1015, subject: "Biologia", title: "Genetyka", exam_date: "2026-11-20", scope: "", completed: false },
  { id: 1016, subject: "Chemia", title: "Sole", exam_date: "2026-11-20", scope: "", completed: false },
  { id: 999, subject: "Fizyka", title: "Completed Exam", exam_date: "2026-11-25", scope: "", completed: true },
  { id: 1009, subject: "Niemiecki", title: "Exam Dec", exam_date: "2026-12-04", scope: "", completed: false },
];

const supabaseHomework = [
  { id: 59, subject: "Fizyka", title: "Zadania CKE", due_date: "2026-11-16", completed: false, source: "vulcan", priority: 1 },
  { id: 41, subject: "Historia", title: "Old HW", due_date: "2026-11-20", completed: false, source: "vulcan", priority: 1 },
];

function buildHarness(initialStorage = {}) {
  const storageMap = new Map(Object.entries(initialStorage));
  let dashboardLoadCount = 0;

  const localStorage = {
    getItem: (k) => (storageMap.has(k) ? storageMap.get(k) : null),
    setItem: (k, v) => storageMap.set(k, String(v)),
    removeItem: (k) => storageMap.delete(k),
  };

  const timers = [];
  const customSetTimeout = (fn, ms) => {
    const id = setTimeout(fn, Math.min(ms, 20));
    timers.push(id);
    return id;
  };

  const jsonResp = (data, status = 200) => ({
    ok: status >= 200 && status < 300,
    status,
    json: async () => data,
    text: async () => JSON.stringify(data),
  });

  const fetchMock = async (url, opts = {}) => {
    const u = String(url);
    if (u.includes("/api/rpc/get_dashboard")) {
      return jsonResp({ status: "ok", result: makeMockDashboardResponse() });
    }
    if (u.includes("/api/rpc/get_upcoming_exams")) {
      return jsonResp({
        status: "ok",
        result: [{ id: 1009, subject: "Niemiecki", title: "Exam Dec", exam_date: "2026-12-04", completed: false }],
      });
    }
    if (u.includes("/api/rpc/get_upcoming_homework")) {
      return jsonResp({
        status: "ok",
        result: [{ id: 41, subject: "Historia", title: "Old HW", due_date: "2026-11-20", completed: false }],
      });
    }
    if (u.includes("/api/rpc/")) {
      return jsonResp({ status: "ok", result: {} });
    }
    if (u.includes("test.supabase.co/rest/v1/school_exams")) {
      return jsonResp(supabaseExams);
    }
    if (u.includes("test.supabase.co/rest/v1/homework_items")) {
      return jsonResp(supabaseHomework);
    }
    if (u.includes("test.supabase.co/rest/v1/")) {
      return jsonResp([]);
    }
    return jsonResp({}, 404);
  };

  const sandbox = {
    console,
    Date,
    Math,
    JSON,
    Map,
    Set,
    Array,
    Object,
    String,
    Number,
    Boolean,
    Promise,
    encodeURIComponent,
    decodeURIComponent,
    clearTimeout,
    setTimeout: customSetTimeout,
    AbortController,
    Event: function (t) { this.type = t; },
    localStorage,
    fetch: fetchMock,
    document: { readyState: "complete", visibilityState: "visible", addEventListener: () => {} },
    window: {
      location: { origin: "https://harness.vercel.app" },
      dispatchEvent: () => {},
      Dashboard: {
        load: async () => { dashboardLoadCount += 1; },
      },
    },
  };
  sandbox.window.window = sandbox.window;
  sandbox.window.localStorage = localStorage;

  vm.runInNewContext(bridgeCode, sandbox);
  return {
    api: sandbox.window.pywebview.api,
    storageMap,
    getDashboardLoadCount: () => dashboardLoadCount,
    cleanup: () => timers.forEach((t) => clearTimeout(t)),
  };
}

function indexHeatmap(dash) {
  const m = {};
  for (const w of dash.heatmap.weeks) {
    for (const d of w.days) {
      if (d) m[d.date] = d;
    }
  }
  return m;
}

(async () => {
  // Case 1: Cold browser start (empty EXAMS/HOMEWORK) overlays Supabase tests onto stale server heatmap
  const cfgJson = JSON.stringify({ supabase_url: "https://test.supabase.co", supabase_key: "test-key", auto_sync: true });
  const h1 = buildHarness({ harness_sync_config_v3: cfgJson });
  try {
    const dash = await h1.api.get_dashboard("2026-11-15");
    const byDate = indexHeatmap(dash);

    assert.strictEqual(byDate["2026-11-17"].has_exam, true, "11-17 exam missing from heatmap");
    assert.strictEqual(byDate["2026-11-17"].exam_count, 1);
    assert(byDate["2026-11-17"].activities.some((a) => a.includes("[UPCOMING TEST] Historia: Sprawdzian I")));

    assert.strictEqual(byDate["2026-11-19"].has_exam, true, "11-19 exam missing from heatmap");
    assert.strictEqual(byDate["2026-11-20"].has_exam, true, "11-20 exams missing from heatmap");
    assert.strictEqual(byDate["2026-11-20"].exam_count, 2);
    assert.strictEqual(byDate["2026-12-04"].has_exam, true, "12-04 exam should stay visible");

    // Completed exam 999 (11-25) and stale server-deleted 1008 (11-28) must NOT appear
    assert.strictEqual(byDate["2026-11-25"].has_exam, false, "completed exam should not show");
    assert.strictEqual(byDate["2026-11-28"].has_exam, false, "stale deleted exam should be cleared after authoritative Supabase sync");
    assert(!byDate["2026-11-28"].activities.some((a) => a.includes("Deleted Exam")));

    // Homework overlay
    assert.strictEqual(byDate["2026-11-16"].has_homework, true, "11-16 homework missing");
    assert.strictEqual(byDate["2026-11-20"].has_homework, true, "11-20 homework missing");

    // Radar and academic_balance reconciled with Supabase (never stays stale CRUISE!)
    assert.strictEqual(dash.radar.exams[0].exam_date, "2026-11-17");
    assert.strictEqual(dash.radar.exams[0].days_left, 2);
    assert.strictEqual(dash.radar.homework[0].due_date, "2026-11-16");
    assert.strictEqual(dash.academic_balance.total_exams_count, 5);
    assert.strictEqual(dash.academic_balance.nearest_exam.exam_date, "2026-11-17");
    assert.notStrictEqual(dash.academic_balance.mode, "CRUISE", "mode must recompute away from stale CRUISE when Supabase exams exist");
    assert.strictEqual(dash.academic_balance.mode, "SURGE");

    // Auto-hydration timer invokes Dashboard.load() even without Dashboard.refresh
    await new Promise((r) => setTimeout(r, 80));
    assert(h1.getDashboardLoadCount() >= 1, "auto-hydration must trigger Dashboard.load()");
  } finally {
    h1.cleanup();
  }

  // Case 2: Returning browser with stale localStorage EXAMS ([id 1009]) + get_upcoming_exams(2)
  const h2 = buildHarness({
    harness_sync_config_v3: cfgJson,
    harness_exams_v3: JSON.stringify([{ id: 1009, subject: "Niemiecki", title: "Exam Dec", exam_date: "2026-12-04", completed: false }]),
  });
  try {
    const dash2 = await h2.api.get_dashboard("2026-11-15");
    const byDate2 = indexHeatmap(dash2);
    assert.strictEqual(byDate2["2026-11-17"].has_exam, true, "stale cached EXAMS must still refresh from Supabase on session start");

    // Calling get_upcoming_exams(2) must NOT overwrite full EXAMS store with a 2-item subset
    const top2 = await h2.api.get_upcoming_exams(2);
    assert.strictEqual(top2.length, 2);
    const dash3 = await h2.api.get_dashboard("2026-11-15");
    const byDate3 = indexHeatmap(dash3);
    assert.strictEqual(byDate3["2026-12-04"].has_exam, true, "get_upcoming_exams(2) must not truncate later heatmap exams");
  } finally {
    h2.cleanup();
  }

  // Case 3: 3 non-Tier-1 tests 4-7 days out via Supabase overlay must still lock CRUISE mode
  const h3 = buildHarness({ harness_sync_config_v3: cfgJson });
  supabaseExams.splice(0, supabaseExams.length,
    { id: 2001, subject: "Historia", title: "Test 1", exam_date: "2026-11-19", scope: "", completed: false },
    { id: 2002, subject: "Biologia", title: "Test 2", exam_date: "2026-11-21", scope: "", completed: false },
    { id: 2003, subject: "Geografia", title: "Test 3", exam_date: "2026-11-22", scope: "", completed: false }
  );
  try {
    const dash4 = await h3.api.get_dashboard("2026-11-15");
    assert.notStrictEqual(dash4.academic_balance.mode, "CRUISE", "3 tests this week must never show CRUISE");
    assert.strictEqual(dash4.academic_balance.week_exams_count, 3);
  } finally {
    h3.cleanup();
  }

  // Case 4: Same-day exam and same-day homework (2026-11-15) must be excluded from upcoming lists & radar
  const h4 = buildHarness({ harness_sync_config_v3: cfgJson });
  supabaseExams.splice(0, supabaseExams.length,
    { id: 3001, subject: "Fizyka", title: "Already Written Today", exam_date: "2026-11-15", scope: "", completed: false },
    { id: 3002, subject: "Matematyka", title: "Future Test", exam_date: "2026-11-18", scope: "", completed: false }
  );
  supabaseHomework.splice(0, supabaseHomework.length,
    { id: 3010, subject: "Polski", title: "Rozprawka Today", due_date: "2026-11-15", completed: false, source: "vulcan", priority: 2 },
    { id: 3011, subject: "Angielski", title: "Future HW", due_date: "2026-11-17", completed: false, source: "vulcan", priority: 1 }
  );
  try {
    const dash5 = await h4.api.get_dashboard("2026-11-15");
    assert.strictEqual(dash5.radar.exams.length, 1);
    assert.strictEqual(dash5.radar.exams[0].exam_date, "2026-11-18");
    assert.strictEqual(dash5.academic_balance.nearest_exam.exam_date, "2026-11-18");
    assert.strictEqual(dash5.academic_balance.total_exams_count, 1);
    assert.strictEqual(dash5.radar.homework.length, 1);
    assert.strictEqual(dash5.radar.homework[0].due_date, "2026-11-17");

    const upExams = await h4.api.get_upcoming_exams(15, "2026-11-15");
    assert.strictEqual(upExams.length, 1);
    assert.strictEqual(upExams[0].exam_date, "2026-11-18");

    const upHw = await h4.api.get_upcoming_homework("2026-11-15");
    assert.strictEqual(upHw.length, 1);
    assert.strictEqual(upHw[0].due_date, "2026-11-17");
  } finally {
    h4.cleanup();
  }

  console.log("JS_BRIDGE_HEATMAP_TESTS_PASSED");
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
""",
        encoding="utf-8",
    )

    proc = subprocess.run(
        ["node", str(test_script), str(bridge_path)],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert proc.returncode == 0, f"Node test failed:\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
    assert "JS_BRIDGE_HEATMAP_TESTS_PASSED" in proc.stdout
