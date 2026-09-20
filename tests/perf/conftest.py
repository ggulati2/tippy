"""Fixtures for the browser performance tests (tests/perf).

These use Playwright with the Chrome that is installed on the computer (no download), in REAL time,
unlike the functional browser tests in tests/browser which use a fast fake clock.
Install once:  pip install -r requirements-perf.txt    Run:  python -m pytest -m perf -v
"""
import json
import os
from pathlib import Path

import pytest

from tests.browser.conftest import call, server  # noqa: F401  (the fixture starts a fresh Tippy on a free port)

playwright_sync = pytest.importorskip("playwright.sync_api", reason="pip install -r requirements-perf.txt")

REPORT: dict = {}     # every test adds its numbers here; written to disk at the end of the session


@pytest.fixture()
def page(server):  # noqa: F811
    """A Chrome page on a fresh, set-up Tippy with every world unlocked. Events collected in the page are in window.__perf."""
    token = call(server, "/api/parent/verify", {"pin": "2468"})["token"]
    call(server, "/api/parent/unlock", {"world": "all"}, token)
    call(server, "/api/parent/settings", {"daily_limit_minutes": 0, "session_minutes": 0}, token)
    with playwright_sync.sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True,
                                    args=["--js-flags=--expose-gc", "--enable-precise-memory-info", "--no-sandbox",
                                          "--autoplay-policy=document-user-activation-required"])   # like a normal Chrome: sound needs a click first
        context = browser.new_context(viewport={"width": 1280, "height": 720})
        page = context.new_page()
        page.tippy_url = server.url
        page.add_init_script("""
            window.__perf = { longtasks: [], events: [], frames: [], keyLatencies: [] };
            try { new PerformanceObserver((l) => l.getEntries().forEach((e) => window.__perf.longtasks.push(e.duration)))
                    .observe({ type: "longtask", buffered: true }); } catch (e) {}
            try { new PerformanceObserver((l) => l.getEntries().forEach((e) => window.__perf.events.push([e.name, e.duration])))
                    .observe({ type: "event", durationThreshold: 16, buffered: true }); } catch (e) {}
            // The time from a key press until the next frame is drawn (the page reacts inside the key handler).
            document.addEventListener("keydown", (e) => { const t0 = e.timeStamp;
                requestAnimationFrame(() => window.__perf.keyLatencies.push(performance.now() - t0)); }, true);
        """)
        yield page
        browser.close()


def pytest_sessionfinish(session, exitstatus):
    path = os.environ.get("PERF_REPORT")
    if path and REPORT:
        Path(path).write_text(json.dumps(REPORT, indent=1))
