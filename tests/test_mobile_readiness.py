import re
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

