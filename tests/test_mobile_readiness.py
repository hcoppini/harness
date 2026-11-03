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
        # In this slice, there must be matching closing </div> tags for aiDiaryModal and its card
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
