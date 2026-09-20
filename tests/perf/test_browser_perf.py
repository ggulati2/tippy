"""Speed and memory in a real browser, in real time. Run:  python -m pytest -m perf -v

What a 6-year-old notices: does the screen appear quickly, does a key press react at once (the project goal is
under 50 ms), do animations stay smooth, does the page stay fast after a long session (no memory leak)?
The budgets are generous, because CI machines are slow and noisy; they catch real regressions (something 3 times
slower, a leak), not small differences. Every test also records its numbers in the report (PERF_REPORT=file.json).
"""
import statistics

import pytest

from tests.perf.conftest import REPORT

pytestmark = pytest.mark.perf

# All times in milliseconds. "p95" = 95 of 100 were faster.
BUDGET = {
    "first_contentful_paint_ms": 2500,
    "play_button_visible_ms": 3000,
    "first_load_kilobytes": 1200,
    "key_to_frame_p95_ms": 100,           # the project goal is 50 ms on a normal laptop; CI gets twice that
    "key_to_frame_max_ms": 250,
    "animation_min_fps": 24,
    "animation_slow_frame_share": 0.10,   # at most 10% of frames slower than 50 ms
    "startup_long_task_ms": 1000,         # the one freeze while the page's scripts load
    "first_tap_ms": 500,                  # tapping Play: from the tap until the world map is drawn
    "long_task_max_ms": 300,              # any freeze while playing
    "long_tasks_allowed": 3,
    "leak_nodes": 300,
    "leak_listeners": 200,
    "leak_heap_mb": 12,
}


def best_of(times: int, measure, good) -> dict:
    """Timing on a shared machine is noisy: another program can steal a moment. Measure up to `times` times
    and keep the first result that is good enough, or the best one. A real slowdown fails every time."""
    results = []
    for _ in range(times):
        result = measure()
        results.append(result)
        if good(result):
            return result
    return min(results, key=lambda r: r["p95_ms"] if "p95_ms" in r else r.get("slow_frame_share", 0))


def record(name: str, numbers: dict) -> None:
    REPORT[name] = numbers
    print(f"\n[perf] {name}: {numbers}")


def percentile(values, pct):
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(len(ordered) * pct / 100))] if ordered else 0.0


def test_page_load_is_quick_and_small(page):
    sizes = []
    page.on("response", lambda r: sizes.append(int(r.headers.get("content-length", "0") or 0)))
    page.goto(page.tippy_url, wait_until="load")
    page.wait_for_selector(".play-btn", state="visible")
    numbers = page.evaluate("""() => { const nav = performance.getEntriesByType("navigation")[0];
        const fcp = performance.getEntriesByName("first-contentful-paint")[0];
        return { dom_content_loaded_ms: Math.round(nav.domContentLoadedEventEnd), load_ms: Math.round(nav.loadEventEnd),
                 first_contentful_paint_ms: fcp ? Math.round(fcp.startTime) : null, play_button_visible_ms: Math.round(performance.now()) }; }""")
    numbers["first_load_kilobytes"] = round(sum(sizes) / 1024)
    numbers["requests"] = len(sizes)
    record("page_load", numbers)
    assert numbers["first_contentful_paint_ms"] is not None and numbers["first_contentful_paint_ms"] <= BUDGET["first_contentful_paint_ms"]
    assert numbers["play_button_visible_ms"] <= BUDGET["play_button_visible_ms"]
    assert numbers["first_load_kilobytes"] <= BUDGET["first_load_kilobytes"], "the app got heavier: check for a new big file"


def test_key_presses_are_answered_within_a_frame_or_two(page):
    page.goto(page.tippy_url)
    page.wait_for_selector(".play-btn")

    def measure() -> dict:
        page.evaluate("() => { window.__perf.keyLatencies = []; }")
        page.evaluate("async () => { await loadProgress(); openWorld('free'); }")
        page.wait_for_selector(".keyboard")
        for i in range(60):                                        # a child typing fast: about 20 keys a second
            page.keyboard.press("abcdefghij"[i % 10])
            page.wait_for_timeout(45)
        page.evaluate("async () => { await loadProgress(); openWorld('letters'); }")
        page.click(".world.level")                                  # Letter Land level 1: each key also talks to the server
        page.wait_for_selector(".big-letter")
        for _ in range(12):
            goal = page.evaluate("() => document.querySelector('.key.goal')?.textContent.trim() || 'a'")
            page.keyboard.press(goal.lower())
            page.wait_for_timeout(400)
        latencies = page.evaluate("() => window.__perf.keyLatencies")
        return {"presses": len(latencies), "p50_ms": round(statistics.median(latencies), 1), "p95_ms": round(percentile(latencies, 95), 1),
                "max_ms": round(max(latencies), 1),
                "slowest_five": [(i, round(v)) for i, v in sorted(enumerate(latencies), key=lambda x: -x[1])[:5]]}   # (which press, ms)

    numbers = best_of(2, measure, lambda r: r["p95_ms"] <= BUDGET["key_to_frame_p95_ms"] and r["max_ms"] <= BUDGET["key_to_frame_max_ms"])
    record("key_to_frame", numbers)
    assert numbers["presses"] >= 60
    assert numbers["p95_ms"] <= BUDGET["key_to_frame_p95_ms"], "a key press takes too long to show on screen"
    assert numbers["max_ms"] <= BUDGET["key_to_frame_max_ms"]


def test_animations_stay_smooth(page):
    page.goto(page.tippy_url)
    page.wait_for_selector(".play-btn")                       # the welcome screen: the mascot bobs and blinks, the button pulses

    def measure() -> dict:
        frames = page.evaluate("""() => new Promise((resolve) => { const deltas = []; let last = performance.now(); const end = last + 3000;
            const tick = (now) => { deltas.push(now - last); last = now; if (now < end) requestAnimationFrame(tick); else resolve(deltas); };
            requestAnimationFrame(tick); })""")[2:]                # the first frames are start-up
        return {"frames": len(frames), "avg_fps": round(1000 / statistics.mean(frames), 1), "p95_frame_ms": round(percentile(frames, 95), 1),
                "slow_frame_share": round(sum(1 for f in frames if f > 50) / len(frames), 3)}

    numbers = best_of(2, measure, lambda r: r["avg_fps"] >= BUDGET["animation_min_fps"] and r["slow_frame_share"] <= BUDGET["animation_slow_frame_share"])
    record("animation", numbers)
    assert numbers["avg_fps"] >= BUDGET["animation_min_fps"]
    assert numbers["slow_frame_share"] <= BUDGET["animation_slow_frame_share"]


def test_no_long_freezes_while_playing(page):
    page.goto(page.tippy_url)
    page.wait_for_selector(".play-btn")
    startup = page.evaluate("() => { const t = window.__perf.longtasks.slice(); window.__perf.longtasks = []; return t; }")   # the page's own start-up
    for world in ("mouse", "keyboard", "words", "numbers"):
        page.evaluate(f"async () => {{ await loadProgress(); openWorld('{world}'); }}")
        page.wait_for_timeout(300)
        page.click(".world.level")
        page.wait_for_timeout(500)
        for key in "asdfjkl":
            page.keyboard.press(key)
            page.wait_for_timeout(60)
        page.click("#home-btn")
        page.wait_for_timeout(200)
    tasks = page.evaluate("() => window.__perf.longtasks")
    numbers = {"startup_longest_ms": round(max(startup or [0])), "long_tasks_over_50ms": len(tasks), "longest_ms": round(max(tasks or [0]))}
    record("long_tasks", numbers)
    assert numbers["startup_longest_ms"] <= BUDGET["startup_long_task_ms"], "loading the page's scripts freezes it for too long"
    assert numbers["longest_ms"] <= BUDGET["long_task_max_ms"], "the page froze for a moment"
    assert len(tasks) <= BUDGET["long_tasks_allowed"]


def test_going_back_and_forth_between_levels_leaks_nothing(page):
    page.goto(page.tippy_url)
    page.wait_for_selector(".play-btn")
    cdp = page.context.new_cdp_session(page)
    cdp.send("Performance.enable")

    def snapshot():
        page.evaluate("() => window.gc && window.gc()")
        metrics = {m["name"]: m["value"] for m in cdp.send("Performance.getMetrics")["metrics"]}
        return {"nodes": int(metrics["Nodes"]), "listeners": int(metrics["JSEventListeners"]), "heap_mb": metrics["JSHeapUsedSize"] / 1048576}

    cycle = """async () => { const wait = (ms) => new Promise((r) => setTimeout(r, ms));
        for (const [world, index] of [["words", 0], ["mouse", 0], ["keyboard", 0], ["letters", 0], ["numbers", 0]]) {
            await loadProgress(); openWorld(world); await wait(120);
            document.querySelectorAll(".world.level")[index].click(); await wait(220);
            document.querySelector("#home-btn").click(); await wait(80);
        } }"""
    for _ in range(2):                                          # warm-up: caches, fonts, the first sounds
        page.evaluate(cycle)
    before = snapshot()
    for _ in range(12):                                         # 60 level starts and exits
        page.evaluate(cycle)
    after = snapshot()
    growth = {key: round(after[key] - before[key], 1) for key in before}
    record("memory_leak_check", {"before": {k: round(v, 1) for k, v in before.items()}, "after": {k: round(v, 1) for k, v in after.items()}, "growth": growth})
    assert growth["nodes"] <= BUDGET["leak_nodes"], "DOM nodes pile up: a screen is not cleaned up"
    assert growth["listeners"] <= BUDGET["leak_listeners"], "event listeners pile up: something is not removed"
    assert growth["heap_mb"] <= BUDGET["leak_heap_mb"], "the page keeps growing in memory"


def test_the_first_tap_is_not_frozen_by_setting_up_sound(page):
    """Creating the browser's audio engine takes about 0.65 s on a Mac and freezes the page while it happens.
    It must happen while the welcome screen is idle, not when the child first taps something and the first sound plays."""
    page.goto(page.tippy_url)
    page.wait_for_selector(".play-btn")
    page.wait_for_timeout(2500)                                   # the welcome screen has been showing for a while
    page.evaluate("() => { window.__perf.longtasks = []; window.__t0 = performance.now(); }")
    page.click(".play-btn", force=True)                          # the button pulses, so Playwright never sees it as "stable"
    page.wait_for_selector(".worlds")
    tap_to_map = page.evaluate("() => Math.round(performance.now() - window.__t0)")
    page.wait_for_timeout(500)
    tasks = page.evaluate("() => window.__perf.longtasks")
    numbers = {"tap_to_world_map_ms": tap_to_map, "long_tasks_after_tap": [round(t) for t in tasks]}
    record("first_tap", numbers)
    assert tap_to_map <= BUDGET["first_tap_ms"], "the first tap froze the page (audio set-up?)"
    assert not tasks or max(tasks) <= 150
