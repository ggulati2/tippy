"""Starts the server and opens Tippy in a fullscreen browser window.

Used by start.command (macOS), start.sh (Linux) and start.bat (Windows).
When the parent chooses "Exit" the server stops and the browser window closes.
"""
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import uvicorn  # noqa: E402

from backend.config import HOST, PORT  # noqa: E402

URL = f"http://{HOST}:{PORT}/"

# Browsers that can open a kiosk (fullscreen, no address bar) window.
BROWSER_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "google-chrome", "chromium", "chromium-browser", "microsoft-edge",
]


def find_browser() -> str | None:
    for candidate in BROWSER_CANDIDATES:
        if os.path.isabs(candidate) and os.path.exists(candidate):
            return candidate
        if not os.path.isabs(candidate) and shutil.which(candidate):
            return shutil.which(candidate)
    return None


def wait_until_ready(timeout: float = 15) -> bool:
    end = time.time() + timeout
    while time.time() < end:
        try:
            urllib.request.urlopen(URL, timeout=1)
            return True
        except Exception:
            time.sleep(0.2)
    return False


def already_running() -> bool:
    """True if Tippy's server already answers (for example the parent double-clicked twice)."""
    try:
        urllib.request.urlopen(URL, timeout=1)
        return True
    except Exception:
        return False


def main() -> None:
    if already_running():
        print("Tippy is already running. Opening it again.")
        browser = find_browser()
        if browser:
            subprocess.Popen([browser, f"--user-data-dir={ROOT / 'data' / 'browser-profile'}", "--kiosk", f"--app={URL}"])
        else:
            import webbrowser
            webbrowser.open(URL)
        return
    from backend.app import app  # imported here so a bad .env shows a clear error

    config = uvicorn.Config(app, host=HOST, port=PORT, log_level="warning")
    server = uvicorn.Server(config)
    app.state.request_shutdown = lambda: setattr(server, "should_exit", True)

    browser_process = None

    def open_browser() -> None:
        nonlocal browser_process
        if not wait_until_ready():
            print("The server did not start. See logs/tippy.log")
            return
        browser = find_browser()
        if browser is None:
            print("Chrome or Edge not found. Opening your normal browser instead.")
            import webbrowser
            webbrowser.open(URL)
            return
        # Own profile folder = own browser instance, so we can close it on exit.
        profile = ROOT / "data" / "browser-profile"
        browser_process = subprocess.Popen([
            browser, f"--user-data-dir={profile}", "--kiosk", f"--app={URL}",
            "--no-first-run", "--no-default-browser-check", "--disable-translate",
        ])

    threading.Thread(target=open_browser, daemon=True).start()
    print(f"Tippy is running at {URL}  (close it from the parent area, or press Ctrl+C here)")
    try:
        server.run()
    finally:
        if browser_process and browser_process.poll() is None:
            browser_process.terminate()


if __name__ == "__main__":
    main()
