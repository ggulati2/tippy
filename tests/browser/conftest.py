"""Helpers for the browser tests: a private Tippy server per test and a headless Chrome to drive it.

Each test gets a brand-new server on a free port with an empty database and its own copy of the
frontend (so nothing in the real project is touched). The test page is index.html with two extra
scripts added: tests/browser/js/common.js and the test script itself.
"""
import html
import json
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
JS_DIR = Path(__file__).resolve().parent / "js"

CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge",
]


def find_chrome() -> str | None:
    """CHROME_PATH wins; otherwise the usual places. None means: skip the browser tests."""
    if os.environ.get("CHROME_PATH"):
        return os.environ["CHROME_PATH"]
    for candidate in CHROME_CANDIDATES:
        if os.path.isabs(candidate) and os.path.exists(candidate):
            return candidate
        if not os.path.isabs(candidate) and shutil.which(candidate):
            return shutil.which(candidate)
    return None


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Server:
    def __init__(self, port: int, frontend: Path, process: subprocess.Popen):
        self.port, self.frontend, self.process = port, frontend, process
        self.url = f"http://127.0.0.1:{port}"


@pytest.fixture()
def server(tmp_path):
    """A fresh Tippy (offline mode, empty database, first-run setup done with PIN 2468)."""
    yield from _start_server(tmp_path, do_setup=True)


@pytest.fixture()
def fresh_server(tmp_path):
    """A brand-new install: nothing set up yet, so the first-run wizard appears."""
    yield from _start_server(tmp_path, do_setup=False)


def _start_server(tmp_path, do_setup: bool):
    if find_chrome() is None:
        pytest.skip("Chrome, Chromium or Edge is needed for the browser tests (or set CHROME_PATH)")
    frontend = tmp_path / "frontend"
    shutil.copytree(ROOT / "frontend", frontend)
    port = free_port()
    env = dict(os.environ, TIPPY_PORT=str(port), TIPPY_FRONTEND_DIR=str(frontend), TIPPY_DB_PATH=str(tmp_path / "tippy.db"),
               TIPPY_HOME=str(tmp_path / "home"), TIPPY_NO_BROWSER="1", LLM_MODE="off", PARENT_PIN="", OPENROUTER_API_KEY="",
               DEV_UNLOCK_ALL="1")   # the browser tests play every feature, the licensed ones too
    # TIPPY_APP_BINARY runs the tests against the packaged app instead of the source code, for example
    #   TIPPY_APP_BINARY=dist/Tippy.app/Contents/MacOS/Tippy python -m pytest -m browser
    binary = os.environ.get("TIPPY_APP_BINARY")
    command = [str(Path(binary).resolve())] if binary else [sys.executable, "-m", "uvicorn", "backend.app:create_app", "--factory",
                                                          "--host", "127.0.0.1", "--port", str(port)]
    process = subprocess.Popen(command, cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    srv = Server(port, frontend, process)
    try:
        deadline = time.time() + 30
        while time.time() < deadline:
            try:
                urllib.request.urlopen(srv.url + "/api/settings", timeout=1)
                break
            except Exception:
                time.sleep(0.2)
        else:
            raise RuntimeError("the test server did not start")
        if do_setup:
            request = urllib.request.Request(srv.url + "/api/setup", method="POST", headers={"Content-Type": "application/json"},
                                             data=json.dumps({"pin": "2468", "language": "en", "daily_limit_minutes": 0}).encode())
            urllib.request.urlopen(request, timeout=5).read()
        yield srv
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()


def _run_until_dumped(command: list[str], timeout: float) -> str:
    """Run Chrome with --dump-dom and return the page as soon as it has been printed.

    Some Chrome setups (a private profile while another Chrome is open) print the page and then
    take a long time to exit, so we stop waiting for the exit as soon as the closing </html> arrives.
    """
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, encoding="utf-8")
    chunks: list[str] = []
    finished = threading.Event()

    def read() -> None:
        for line in process.stdout:
            chunks.append(line)
            if "</html>" in line:
                break
        finished.set()

    threading.Thread(target=read, daemon=True).start()
    finished.wait(timeout)
    process.kill()
    process.wait()
    return "".join(chunks)


def call(srv: Server, path: str, body: dict | None = None, token: str | None = None) -> dict:
    """A small helper for the tests to prepare state through the web API (POST when a body is given)."""
    headers = {"Content-Type": "application/json"}
    if token:
        headers["X-Parent-Token"] = token
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(srv.url + path, data=data, headers=headers, method="POST" if body is not None else "GET")
    return json.loads(urllib.request.urlopen(request, timeout=10).read())


def run_script(srv: Server, script: str, arg: str = "", budget_ms: int = 3_000_000, width: int = 1280, height: int = 720) -> dict:
    """Load the test page in headless Chrome, let the script run (with a fast fake clock) and return its report."""
    # The page's Content-Security-Policy forbids inline scripts, so the test scripts are separate files in the
    # test copy of the frontend and are loaded like Tippy's own scripts.
    index = (srv.frontend / "index.html").read_text(encoding="utf-8")
    (srv.frontend / "_test_common.js").write_text((JS_DIR / "common.js").read_text(encoding="utf-8"), encoding="utf-8")
    (srv.frontend / "_test_script.js").write_text((JS_DIR / script).read_text(encoding="utf-8"), encoding="utf-8")
    scripts = '<script src="_test_common.js"></script><script src="_test_script.js"></script>'
    (srv.frontend / "browser-test.html").write_text(index.replace("</body>", scripts + "</body>"), encoding="utf-8")
    profile = srv.frontend.parent / f"chrome-profile-{script}"
    command = [find_chrome(), "--headless", "--disable-gpu", "--no-sandbox", "--no-first-run", f"--user-data-dir={profile}",
               f"--window-size={width},{height}", f"--virtual-time-budget={budget_ms}", "--dump-dom",
               f"{srv.url}/browser-test.html#{arg}"]
    output = _run_until_dumped(command, timeout=600)
    start = output.rfind('<pre id="botresult">')  # the last one: the page source above may mention it
    if start < 0:
        raise AssertionError("the page did not produce a report (Chrome output was " + str(len(output)) + " characters)")
    end = output.find("</pre>", start)
    return json.loads(html.unescape(output[start + len('<pre id="botresult">'):end]))


def assert_clean(report: dict, ignore_fit: bool = False) -> None:
    """Fail with a readable list of what went wrong."""
    results = report["results"]
    assert any(r["label"] == "finished" for r in results), "the test script did not reach its end: " + json.dumps(results[-3:])
    problems = [f"FAILED: {r['label']} [{r['detail']}]" for r in results
                if not r["ok"] and not (ignore_fit and r["label"].startswith("fit: "))]
    problems += [f"PAGE ERROR: {e}" for e in report["errors"]]
    assert not problems, "\n" + "\n".join(problems)
