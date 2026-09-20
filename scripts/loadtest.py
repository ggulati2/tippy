"""Load and performance test for Tippy's server:  python scripts/loadtest.py

It starts its own Tippy server (empty database, offline mode, a free port), then measures:
  1. start-up time (process start until the first answer),
  2. how fast the busiest endpoints answer when 20 children hammer them at once,
  3. a realistic play session (what one child's browser sends while playing),
  4. the parent dashboard and the backup on a database with a whole year of play,
  5. memory: how much the server grows after all of that.
The numbers are compared with budgets (BUDGETS below). The report is printed, saved as JSON
(--report FILE) and, in CI, shown in the job summary. Exit code 1 if a budget is broken.

Budgets are deliberately generous: CI machines are slow and noisy. They catch real regressions
(an endpoint that suddenly takes 10 times longer, a memory leak) but not small differences.
"""
import argparse
import json
import os
import random
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
from datetime import date, timedelta
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
PIN = "2468"

# name -> budget. Times in milliseconds, memory in megabytes. "p95" = 95 of 100 requests were faster.
BUDGETS = {
    "startup_seconds": 5.0,
    "hammer_p95_ms": 250.0,          # 20 children at once on the busiest endpoints
    "hammer_error_rate": 0.0,
    "session_p95_ms": 150.0,         # one child playing: every request of a session
    "dashboard_year_ms": 1500.0,     # the parent dashboard after a year of play
    "export_year_ms": 1500.0,
    "memory_growth_mb": 60.0,
}


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def rss_mb(pid: int) -> float:
    """Memory of a process in megabytes (macOS and Linux)."""
    out = subprocess.run(["ps", "-o", "rss=", "-p", str(pid)], capture_output=True, text=True).stdout.strip()   # noqa: S603, S607
    return int(out) / 1024 if out else 0.0


class Server:
    """A private Tippy server for the test."""

    def __init__(self, home: Path):
        self.port = free_port()
        self.url = f"http://127.0.0.1:{self.port}"
        self.home = home
        env = dict(os.environ, TIPPY_PORT=str(self.port), TIPPY_DB_PATH=str(home / "tippy.db"), TIPPY_HOME=str(home),
                   TIPPY_NO_BROWSER="1", LLM_MODE="off", PARENT_PIN="", OPENROUTER_API_KEY="")
        binary = os.environ.get("TIPPY_APP_BINARY")           # test the packaged app instead of the source
        command = [binary] if binary else [sys.executable, "-m", "uvicorn", "backend.app:create_app", "--factory",
                                           "--host", "127.0.0.1", "--port", str(self.port), "--log-level", "warning"]
        self.started = time.perf_counter()
        self.process = subprocess.Popen(command, cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)   # noqa: S603
        self.startup_seconds = self._wait()

    def _wait(self) -> float:
        deadline = time.time() + 60
        while time.time() < deadline:
            try:
                if httpx.get(self.url + "/api/settings", timeout=1).status_code == 200:
                    return time.perf_counter() - self.started
            except httpx.HTTPError:
                time.sleep(0.05)
        raise RuntimeError("the server did not start")

    def stop(self) -> None:
        self.process.terminate()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill()


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(len(ordered) * pct / 100))]


def summarize(times_ms: list[float], errors: int, seconds: float) -> dict:
    return {"requests": len(times_ms) + errors, "errors": errors, "rps": round(len(times_ms) / seconds, 1) if seconds else 0,
            "p50_ms": round(percentile(times_ms, 50), 1), "p95_ms": round(percentile(times_ms, 95), 1),
            "p99_ms": round(percentile(times_ms, 99), 1), "max_ms": round(max(times_ms or [0]), 1)}


# ---------- The requests one child's browser sends ----------

KEYS = list("ASDFJKL")


def keystrokes_body() -> dict:
    return {"events": [{"key": random.choice(KEYS), "correct": random.random() > 0.2, "ms": random.randint(200, 2500)}
                       for _ in range(random.randint(1, 10))], "adaptive": random.random() < 0.5}


ENDPOINTS = {
    "POST /api/keystrokes": lambda c: c.post("/api/keystrokes", json=keystrokes_body()),
    "GET /api/progress": lambda c: c.get("/api/progress"),
    "GET /api/settings": lambda c: c.get("/api/settings"),
    "GET /api/content/words": lambda c: c.get("/api/content/words?count=5&pictured=true&max_len=4"),
    "GET /api/content/sentences": lambda c: c.get("/api/content/sentences?count=4"),
    "POST /api/session/heartbeat": lambda c: c.post("/api/session/heartbeat", json={"seconds": 15}),
}


def hammer(server: Server, name: str, call, workers: int = 20, seconds: float = 4.0) -> dict:
    """`workers` children calling one endpoint as fast as they can for a few seconds."""
    times: list[float] = []
    errors = [0]
    lock = threading.Lock()
    stop = time.time() + seconds

    def work() -> None:
        with httpx.Client(base_url=server.url, timeout=10) as client:
            while time.time() < stop:
                start = time.perf_counter()
                try:
                    ok = call(client).status_code == 200
                except httpx.HTTPError:
                    ok = False
                took = (time.perf_counter() - start) * 1000
                with lock:
                    if ok:
                        times.append(took)
                    else:
                        errors[0] += 1

    threads = [threading.Thread(target=work) for _ in range(workers)]
    began = time.time()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return summarize(times, errors[0], time.time() - began)


def play_session(server: Server, children: int = 5, seconds: float = 6.0) -> dict:
    """Several children each playing normally: a key press every ~0.4 s, sometimes a level and a new word list."""
    times: list[float] = []
    errors = [0]
    lock = threading.Lock()
    stop = time.time() + seconds

    def child() -> None:
        with httpx.Client(base_url=server.url, timeout=10) as client:
            while time.time() < stop:
                pick = random.random()
                call = (ENDPOINTS["POST /api/keystrokes"] if pick < 0.75 else ENDPOINTS["GET /api/content/words"] if pick < 0.85
                        else ENDPOINTS["GET /api/progress"] if pick < 0.95 else ENDPOINTS["POST /api/session/heartbeat"])
                start = time.perf_counter()
                try:
                    ok = call(client).status_code == 200
                except httpx.HTTPError:
                    ok = False
                took = (time.perf_counter() - start) * 1000
                with lock:
                    if ok:
                        times.append(took)
                    else:
                        errors[0] += 1
                time.sleep(random.uniform(0.2, 0.6))

    threads = [threading.Thread(target=child) for _ in range(children)]
    began = time.time()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return summarize(times, errors[0], time.time() - began)


# ---------- A whole year of play ----------

def seed_a_year(server: Server) -> None:
    """Fill the active child's database as if a child had played every day for a year."""
    # With TIPPY_DB_PATH set, the family database and the children's databases sit directly in the home folder.
    family = sqlite3.connect(server.home / "family.db")
    row = family.execute("SELECT value FROM settings WHERE key = 'active_profile'").fetchone()
    first = family.execute("SELECT MIN(id) FROM profiles").fetchone()[0]
    family.close()
    profile = server.home / "profiles" / f"{row[0] if row else first}.db"
    conn = sqlite3.connect(profile)
    today = date.today()
    for n in range(365):
        day = (today - timedelta(days=n)).isoformat()
        conn.execute("INSERT OR REPLACE INTO play_days (day) VALUES (?)", (day,))
        conn.execute("INSERT OR REPLACE INTO play_time (day, seconds) VALUES (?, ?)", (day, random.randint(300, 1800)))
        attempts = random.randint(40, 400)
        conn.execute("INSERT OR REPLACE INTO daily_stats (day, attempts, correct) VALUES (?, ?, ?)", (day, attempts, int(attempts * random.uniform(0.6, 0.95))))
    for key in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789":
        attempts = random.randint(200, 5000)
        conn.execute("INSERT OR REPLACE INTO keystroke_stats (key, attempts, correct, avg_ms) VALUES (?, ?, ?, ?)",
                     (key, attempts, int(attempts * random.uniform(0.6, 0.95)), random.uniform(300, 1500)))
    for world, levels in (("mouse", 4), ("keyboard", 5), ("letters", 5), ("words", 5), ("sentences", 5), ("basics", 6), ("numbers", 6)):
        for level in range(1, levels + 1):
            conn.execute("INSERT OR REPLACE INTO progress (world, level, status, stars) VALUES (?, ?, 'done', 3)", (world, level))
    for n in range(2000):                                    # a large content cache
        conn.execute("INSERT INTO content_cache (type, level, json, created_at) VALUES ('words:en', 16, ?, ?)", (json.dumps({"text": f"w{n}"}), today.isoformat()))
    conn.commit()
    conn.close()


def timed(call) -> tuple[float, int]:
    start = time.perf_counter()
    response = call()
    return (time.perf_counter() - start) * 1000, len(response.content)


def run() -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        server = Server(Path(tmp))
        report: dict = {"startup_seconds": round(server.startup_seconds, 2)}
        try:
            client = httpx.Client(base_url=server.url, timeout=30)
            client.post("/api/setup", json={"pin": PIN, "language": "en", "daily_limit_minutes": 0}).raise_for_status()
            token = client.post("/api/parent/verify", json={"pin": PIN}).json()["token"]
            headers = {"X-Parent-Token": token}
            for path in ("mouse", "keyboard", "letters"):
                client.post("/api/progress/complete", json={"world": path, "level": 1, "stars": 3})
            memory_before = rss_mb(server.process.pid)

            report["hammer"] = {name: hammer(server, name, call) for name, call in ENDPOINTS.items()}
            report["session"] = play_session(server)

            seed_a_year(server)
            report["dashboard_year_ms"], _ = (round(v, 1) for v in timed(lambda: client.get("/api/parent/dashboard", headers=headers)))
            report["export_year_ms"], size = timed(lambda: client.get("/api/parent/export", headers=headers))
            report["export_year_ms"] = round(report["export_year_ms"], 1)
            report["export_kilobytes"] = round(size / 1024)
            report["progress_year_ms"] = round(timed(lambda: client.get("/api/progress"))[0], 1)

            report["memory_mb_before"] = round(memory_before, 1)
            report["memory_mb_after"] = round(rss_mb(server.process.pid), 1)
            report["memory_growth_mb"] = round(report["memory_mb_after"] - report["memory_mb_before"], 1)
        finally:
            server.stop()
    return report


def check(report: dict) -> list[str]:
    """Compare the report with the budgets. Returns a list of broken ones."""
    broken = []

    # A slow machine can multiply every budget: TIPPY_BUDGET_FACTOR=2 allows twice the time (zero stays zero).
    factor = float(os.environ.get("TIPPY_BUDGET_FACTOR", "1"))

    def over(label: str, value: float, budget: float) -> None:
        budget = budget * factor
        if value > budget:
            broken.append(f"{label}: {value} is over the budget of {budget}")

    over("start-up (seconds)", report["startup_seconds"], BUDGETS["startup_seconds"])
    for name, result in report["hammer"].items():
        over(f"{name} p95 (ms, 20 children at once)", result["p95_ms"], BUDGETS["hammer_p95_ms"])
        over(f"{name} error rate", result["errors"] / max(1, result["requests"]), BUDGETS["hammer_error_rate"])
    over("play session p95 (ms)", report["session"]["p95_ms"], BUDGETS["session_p95_ms"])
    over("play session errors", report["session"]["errors"], 0)
    over("dashboard after a year (ms)", report["dashboard_year_ms"], BUDGETS["dashboard_year_ms"])
    over("backup after a year (ms)", report["export_year_ms"], BUDGETS["export_year_ms"])
    over("memory growth (MB)", report["memory_growth_mb"], BUDGETS["memory_growth_mb"])
    return broken


def markdown(report: dict, broken: list[str]) -> str:
    lines = ["### Server performance", "", f"Start-up: **{report['startup_seconds']} s** (budget {BUDGETS['startup_seconds']} s)", "",
             "| Endpoint (20 children at once) | requests/s | p50 ms | p95 ms | p99 ms | errors |", "| --- | ---: | ---: | ---: | ---: | ---: |"]
    for name, r in report["hammer"].items():
        lines.append(f"| {name} | {r['rps']} | {r['p50_ms']} | {r['p95_ms']} | {r['p99_ms']} | {r['errors']} |")
    s = report["session"]
    lines += ["", f"Play session (5 children): p50 **{s['p50_ms']} ms**, p95 **{s['p95_ms']} ms**, {s['requests']} requests, {s['errors']} errors", "",
              f"After a year of play: dashboard **{report['dashboard_year_ms']} ms**, backup **{report['export_year_ms']} ms** ({report['export_kilobytes']} KB), "
              f"progress {report['progress_year_ms']} ms", "",
              f"Memory: {report['memory_mb_before']} MB before, {report['memory_mb_after']} MB after (**+{report['memory_growth_mb']} MB**, budget {BUDGETS['memory_growth_mb']} MB)", ""]
    lines.append("**Budgets broken:**" if broken else "All budgets kept.")
    lines += [f"- {b}" for b in broken]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--report", help="write the numbers as JSON to this file")
    parser.add_argument("--summary", help="write a Markdown summary to this file (CI shows it on the job page)")
    args = parser.parse_args()
    report = run()
    broken = check(report)
    text = markdown(report, broken)
    print(text)
    if args.report:
        Path(args.report).write_text(json.dumps({**report, "budgets": BUDGETS, "broken": broken}, indent=1))
    if args.summary:
        Path(args.summary).write_text(text)
    sys.exit(1 if broken else 0)


if __name__ == "__main__":
    main()
