import json
import re
import shutil
import subprocess
from pathlib import Path

def test_html_tag_balancing():
    """Verify that both root index.html and ui/index.html have perfectly balanced tags."""
    for filename in ["index.html", "ui/index.html"]:
        path = Path(__file__).resolve().parent.parent / filename
        assert path.exists(), f"{filename} does not exist"
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()

        tags = re.findall(r"<(/?)([a-zA-Z0-9\-]+)([^>]*)>", text)
        stack = []
        self_closing = {
            "br", "hr", "img", "input", "link", "meta",
            "circle", "line", "path", "polyline", "rect", "defs", "use", "source"
        }

        for is_closing, name, attrs in tags:
            name = name.lower()
            if name in self_closing or attrs.endswith("/"):
                continue
            if not is_closing:
                stack.append(name)
            else:
                if stack and stack[-1] == name:
                    stack.pop()

        assert len(stack) == 0, f"{filename} has unclosed tags: {stack}"

def test_mobile_bottom_nav_not_nested_in_modal():
    """Verify that mobileBottomNav is outside of aiDiaryModal and all other modal overlays."""
    for filename in ["index.html", "ui/index.html"]:
        path = Path(__file__).resolve().parent.parent / filename
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        ai_modal_idx = content.find('id="aiDiaryModal"')
        bottom_nav_idx = content.find('id="mobileBottomNav"')
        assert ai_modal_idx != -1
        assert bottom_nav_idx != -1

        # Check closing tag of aiDiaryModal comes before bottom_nav
        slice_after_ai = content[ai_modal_idx:bottom_nav_idx]
        assert slice_after_ai.count("</div>") >= 2

def test_css_mobile_rules_and_calendar():
    """Verify that mobile rules in css/app.css and ui/css/app.css have proper grid track limits."""
    for filename in ["css/app.css", "ui/css/app.css"]:
        path = Path(__file__).resolve().parent.parent / filename
        with open(path, "r", encoding="utf-8") as f:
            css = f.read()

        # Mini calendar grid must use repeat(7, minmax(0, 1fr))
        assert "repeat(7, minmax(0, 1fr))" in css

        # Mobile bottom nav must have high z-index
        assert "z-index: 1000" in css

def test_mobile_metro_hud_present_and_responsive():
    """Verify that Mobile Metro HUD is present and replaces the 4,800px track on mobile."""
    for filename in ["index.html", "ui/index.html"]:
        path = Path(__file__).resolve().parent.parent / filename
        with open(path, "r", encoding="utf-8") as f:
            html = f.read()
        assert 'id="mobileMetroHud"' in html
        assert 'class="mobile-metro-hud"' in html

    for filename in ["css/app.css", "ui/css/app.css"]:
        path = Path(__file__).resolve().parent.parent / filename
        with open(path, "r", encoding="utf-8") as f:
            css = f.read()
        # Desktop hides mobile HUD
        assert ".mobile-metro-hud" in css
        # Mobile hides viewport, cards section, and toolbar
        assert ".metro-viewport,\n  .metro-cards-section,\n  .metro-toolbar" in css or ".metro-viewport" in css
        assert "display: none !important;" in css

def test_today_mobile_segmented_bar():
    """Verify that Daily Execution has a Segmented Tab Switcher for scroll-free navigation."""
    for filename in ["index.html", "ui/index.html"]:
        path = Path(__file__).resolve().parent.parent / filename
        with open(path, "r", encoding="utf-8") as f:
            html = f.read()
        assert 'id="todayMobileSegmentedBar"' in html
        assert 'data-segment="routine"' in html
        assert 'data-segment="timetable"' in html
        assert 'data-segment="gym"' in html
        assert 'data-segment="diary"' in html
        assert 'today-segment-target="routine"' in html
        assert 'today-segment-target="gym"' in html
        assert 'today-segment-target="diary"' in html
        assert 'today-segment-target="timetable"' in html

    for filename in ["css/app.css", "ui/css/app.css"]:
        path = Path(__file__).resolve().parent.parent / filename
        with open(path, "r", encoding="utf-8") as f:
            css = f.read()
        assert ".today-mobile-segmented-bar" in css
        assert '[today-segment-target="routine"]' in css
        assert '[today-segment-target="timetable"]' in css

def test_mobile_cockpit_clutter_free():
    """Verify that the 365-day heatmap and 7-day schedule forecast are hidden on mobile."""
    for filename in ["index.html", "ui/index.html"]:
        path = Path(__file__).resolve().parent.parent / filename
        with open(path, "r", encoding="utf-8") as f:
            html = f.read()
        assert 'id="dashForecastCard"' in html

    for filename in ["css/app.css", "ui/css/app.css"]:
        path = Path(__file__).resolve().parent.parent / filename
        with open(path, "r", encoding="utf-8") as f:
            css = f.read()
        assert ".heatmap-card,\n  #dashForecastCard" in css or ".heatmap-card" in css

def test_service_worker_v6_and_controllerchange():
    """Verify Service Worker version v6.0 and controllerchange auto-reload."""
    for filename in ["sw.js", "ui/sw.js"]:
        path = Path(__file__).resolve().parent.parent / filename
        with open(path, "r", encoding="utf-8") as f:
            sw = f.read()
        assert "harness-executive-v6.0" in sw
        assert "?v=6.0" in sw

    for filename in ["index.html", "ui/index.html"]:
        path = Path(__file__).resolve().parent.parent / filename
        with open(path, "r", encoding="utf-8") as f:
            html = f.read()
        assert "controllerchange" in html
        assert "forceHardReload" in html
        assert "v6.0" in html


def test_daily_exclusive_checkboxes_and_obsidian_ui_parity():
    """Verify checkboxes live exclusively in Daily, no duplicate mobile segmented bar, and root == ui parity."""
    root = Path(__file__).resolve().parent.parent

    for filename in ["index.html", "ui/index.html"]:
        html = (root / filename).read_text(encoding="utf-8")
        assert html.count('id="todayMobileSegmentedBar"') == 1
        assert 'id="tumComparisonHero"' in html
        assert 'id="stationInspectorPanel"' in html
        assert 'id="metroPhaseFilters"' in html
        assert 'id="btnHeaderSettings"' in html
        assert 'id="headerSettingsPopover"' in html

        # Extract #view-tum section and ensure zero checkboxes appear inside TUM '28 view
        tum_start = html.index('id="view-tum"')
        tum_end = html.index('id="view-projects"')
        tum_slice = html[tum_start:tum_end]
        assert 'type="checkbox"' not in tum_slice
        assert 'check-dot' not in tum_slice
        assert 'id="gcalendarModal" class="modal-overlay"' in html

    for filename in ["js/study.js", "ui/js/study.js"]:
        study_js = (root / filename).read_text(encoding="utf-8")
        assert "Clear" in study_js and "Reopen" in study_js
        assert "check-dot" not in study_js

    mirrored_paths = [
        "index.html",
        "css/app.css",
        "js/api_bridge.js",
        "js/app.js",
        "js/command_palette.js",
        "js/dashboard.js",
        "js/focus_timer.js",
        "js/metro.js",
        "js/study.js",
        "js/today.js",
        "js/tum.js",
    ]
    for rel in mirrored_paths:
        assert (root / rel).read_bytes() == (root / "ui" / rel).read_bytes(), f"Mismatch between {rel} and ui/{rel}"


def test_metro_timeline_maps_dates_between_station_anchors():
    """Verify Today beacon and exam ticks interpolate piecewise-linearly between station anchor dates."""
    node_bin = shutil.which("node")
    assert node_bin, "Node.js is required to evaluate js/metro.js timeline math"

    root = Path(__file__).resolve().parent.parent
    probe_script = r"""
const fs = require("fs");
const vm = require("vm");
const code = fs.readFileSync("js/metro.js", "utf8");
const roadmap = JSON.parse(fs.readFileSync("data/metro_roadmap.json", "utf8"));

function runAt(y, m, d, h = 12, exams = []) {
  const RealDate = Date;
  class FixedDate extends RealDate {
    constructor(...args) {
      if (args.length === 0) super(y, m - 1, d, h, 0, 0);
      else super(...args);
    }
    static now() { return new RealDate(y, m - 1, d, h, 0, 0).getTime(); }
  }
  const elements = {
    metroCanvasWrap: { style: {}, innerHTML: "", querySelectorAll: () => [] },
    metroCardsGrid: { innerHTML: "" },
    metroTestTooltip: { style: {}, id: "metroTestTooltip" },
  };
  const sandbox = {
    Date: FixedDate,
    Math, Number, String, Boolean, Array, Object, Set, Map, JSON, RegExp, Error,
    encodeURIComponent, decodeURIComponent, console,
    window: {},
    document: {
      documentElement: { getAttribute: () => "dark" },
      getElementById: (id) => elements[id] || null,
      querySelector: () => null,
      querySelectorAll: () => [],
      createElement: () => ({ style: {} }),
      body: { appendChild: () => {} },
    },
  };
  sandbox.window = sandbox;
  vm.runInNewContext(code, sandbox);
  sandbox.MetroMap.data = JSON.parse(JSON.stringify(roadmap));
  sandbox.MetroMap.upcomingExams = exams;
  sandbox.MetroMap.render();
  const svg = elements.metroCanvasWrap.innerHTML;
  const tests = [...svg.matchAll(/<g class="metro-test-tick"[^>]*data-date="([^"]+)"[^>]*>[\s\S]*?<circle cx="([^"]+)"/g)]
    .map((m) => [m[1], Number(m[2])]);
  return { beaconX: sandbox.MetroMap.currentBeaconX, tests, svg };
}

const novRun = runAt(2026, 11, 15, 22, [
  { id: 1, subject: "Fizyka", title: "Test", exam_date: "2026-11-18", completed: false },
  { id: 2, subject: "Geografia", title: "Spr", exam_date: "2026-12-05", completed: false },
]);
console.log(JSON.stringify({
  nov15: novRun.beaconX,
  nov15Tests: novRun.tests,
  nov15HasPct: novRun.svg.includes("OF \u201926\u2013\u201928"),
  sep01: runAt(2026, 9, 1, 12).beaconX,
  sep16: runAt(2026, 9, 16, 12).beaconX,
  oct15: runAt(2026, 10, 15, 12).beaconX,
  aug27: runAt(2027, 8, 1, 12).beaconX,
  jul28: runAt(2028, 7, 15, 12).beaconX,
}));
"""
    proc = subprocess.run(
        [node_bin, "-e", probe_script],
        cwd=str(root),
        capture_output=True,
        text=True,
        check=True,
    )
    out = json.loads(proc.stdout.strip())

    def station_x(idx: int) -> float:
        return 120.0 + idx * 220.0

    # Nov 15, 2026 must sit nearly midway between NOV '26 (idx 3) and DEC '26 (idx 4), NOT before NOV '26
    assert station_x(3) < out["nov15"] < station_x(4)
    assert abs(out["nov15"] - (station_x(3) + 0.5 * 220.0)) < 15.0
    assert out["nov15HasPct"] is True

    # Exam ticks map onto their true station-anchored months too
    exam_map = dict(out["nov15Tests"])
    assert out["nov15"] < exam_map["2026-11-18"] < station_x(4)
    assert station_x(4) < exam_map["2026-12-05"] < station_x(5)

    # Monotonic progression across non-uniform station spans
    assert station_x(0) <= out["sep01"] < station_x(1)
    assert station_x(1) <= out["sep16"] < station_x(2)
    assert station_x(2) < out["oct15"] < station_x(3)
    assert station_x(11) < out["aug27"] < station_x(12)  # jul-aug-2027 2-month span
    assert station_x(22) < out["jul28"] < station_x(22) + 120.0  # jul-2028 -> TUM terminal


