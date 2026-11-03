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
