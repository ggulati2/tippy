"""Starts the server and opens Tippy in a fullscreen window.

On a Mac that is the Mac's own web view (pywebview), so Chrome is not needed; elsewhere, or when pywebview is
missing, it is a Chrome or Edge window in kiosk mode.
Used by start.command (macOS), start.sh (Linux) and start.bat (Windows).
When the parent chooses "Exit" the server stops and the window closes.
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

# A Windows app built without a console window has no stdout or stderr at all (they are None), and uvicorn's
# logging then crashes when it asks whether the output is a terminal. Give it a bin to write to.
for _name in ("stdout", "stderr"):
    if getattr(sys, _name) is None:
        setattr(sys, _name, open(os.devnull, "w"))

import uvicorn  # noqa: E402

from backend.config import FROZEN, HOME_DIR, HOST, PORT  # noqa: E402

# The browser window's own profile lives with the family's data (a user folder in the packaged app).
BROWSER_PROFILE = HOME_DIR / "data" / "browser-profile"

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
    # TIPPY_BROWSER=/path/to/browser chooses a browser (for example Brave or Edge, or a stand-in in tests).
    if os.environ.get("TIPPY_BROWSER") and os.path.exists(os.environ["TIPPY_BROWSER"]):
        return os.environ["TIPPY_BROWSER"]
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
            urllib.request.urlopen(URL, timeout=1)  # nosec B310 - URL is built from the fixed local host and port, never from input
            return True
        except Exception:
            time.sleep(0.2)
    return False


def already_running() -> bool:
    """True if Tippy's server already answers (for example the parent double-clicked twice)."""
    try:
        urllib.request.urlopen(URL, timeout=1)  # nosec B310 - URL is built from the fixed local host and port, never from input
        return True
    except Exception:
        return False


def native_window():
    """The pywebview module on a Mac, or None when the browser window is used instead.

    Mac only for now: Windows and Linux web views have not been checked by hand yet (downloads, printing, voice).
    """
    if sys.platform != "darwin" or os.environ.get("TIPPY_NO_BROWSER"):
        return None
    try:
        import webview
    except ImportError:
        return None
    webview.settings["ALLOW_DOWNLOADS"] = True   # backups and the class list are saved with a Save dialog
    return webview


def open_native_window(webview) -> None:
    """Shows Tippy fullscreen in the Mac's own web view. Blocks until the window is closed."""
    webview.create_window("Tippy", URL, fullscreen=True, background_color="#BFE9FF")   # Tippy's sky, no white flash
    # Private mode (the default) starts with an empty web view each time: Tippy keeps nothing there, and no old
    # copy of a screen can be shown after an update.
    webview.start()


def main() -> None:
    webview = native_window()
    if already_running():
        print("Tippy is already running. Opening it again.")
        if webview:
            open_native_window(webview)
            return
        browser = find_browser()
        if browser:
            subprocess.Popen([browser, f"--user-data-dir={BROWSER_PROFILE}", "--kiosk", f"--app={URL}"])
        else:
            import webbrowser
            webbrowser.open(URL)
        return
    from backend.app import app  # imported here so a bad .env shows a clear error

    config = uvicorn.Config(app, host=HOST, port=PORT, log_level="warning")
    server = uvicorn.Server(config)
    app.state.request_shutdown = lambda: setattr(server, "should_exit", True)

    if webview:
        # The Mac needs the window on the main thread, so the server runs next to it. "Exit" in the parent area
        # closes the window; closing the window (or Cmd+Q) stops the server.
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()
        if not wait_until_ready():
            print(f"The server did not start. See {HOME_DIR / 'logs' / 'tippy.log'}")
            return
        app.state.request_shutdown = lambda: [w.destroy() for w in webview.windows]
        print(f"Tippy is running at {URL}  (close it from the parent area, or close the window)")
        open_native_window(webview)
        server.should_exit = True
        thread.join(timeout=5)
        return

    browser_process = None

    def open_browser() -> None:
        nonlocal browser_process
        if not wait_until_ready():
            print(f"The server did not start. See {HOME_DIR / 'logs' / 'tippy.log'}")
            return
        if os.environ.get("TIPPY_NO_BROWSER"):   # for tests and headless machines: run the server only
            return
        browser = find_browser()
        if browser is None:
            print("Chrome or Edge not found. Opening your normal browser instead.")
            import webbrowser
            webbrowser.open(URL)
            return
        # Own profile folder = own browser instance, so we can close it on exit.
        browser_process = subprocess.Popen([
            browser, f"--user-data-dir={BROWSER_PROFILE}", "--kiosk", f"--app={URL}",
            "--no-first-run", "--no-default-browser-check", "--disable-translate",
            "--autoplay-policy=no-user-gesture-required",   # Tippy's recorded voice may speak before the first click
        ])
        if FROZEN:
            # The packaged app has no Terminal window: when the browser window is closed, Tippy quits.
            started = time.time()

            def quit_with_browser() -> None:
                browser_process.wait()
                if time.time() - started > 10:   # not a browser that handed over to another one and left at once
                    server.should_exit = True
            threading.Thread(target=quit_with_browser, daemon=True).start()

    threading.Thread(target=open_browser, daemon=True).start()
    print(f"Tippy is running at {URL}  (close it from the parent area, or press Ctrl+C here)")
    try:
        server.run()
    finally:
        if browser_process and browser_process.poll() is None:
            browser_process.terminate()


if __name__ == "__main__":
    main()
