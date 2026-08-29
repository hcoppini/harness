"""Desktop application entrypoint for Harness using PyWebView."""

import os
import sys
from pathlib import Path
import webview
from app.api import HarnessAPI

# Determine base directory for UI assets
if getattr(sys, "frozen", False):
    candidates = [
        Path(getattr(sys, "_MEIPASS", "")),
        Path(sys.executable).resolve().parent / "_internal",
        Path(sys.executable).resolve().parent,
    ]
    BASE_DIR = next((p for p in candidates if (p / "ui" / "index.html").exists()), Path(sys.executable).resolve().parent)
else:
    BASE_DIR = Path(__file__).resolve().parent

UI_INDEX = BASE_DIR / "ui" / "index.html"


def main():
    """Initializes the SQLite database and launches the PyWebView native desktop window."""
    try:
        # Direct API bridge
        api = HarnessAPI()

        # Create native Windows desktop window using Chromium WebView2
        window = webview.create_window(
            title="HARNESS // Personal Execution OS",
            url=str(UI_INDEX),
            js_api=api,
            width=1220,
            height=850,
            min_size=(920, 620),
            background_color="#0a0c10",
        )

        # Launch event loop
        webview.start(debug=False)
    except Exception as e:
        import traceback
        log_file = BASE_DIR / "crash.log"
        with open(log_file, "w", encoding="utf-8") as f:
            f.write(traceback.format_exc())
        raise


if __name__ == "__main__":
    main()
