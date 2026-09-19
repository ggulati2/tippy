"""Keystroke scoring and adaptive difficulty for Letter Land.

The idea in plain words: the child starts with just two letters. Once he gets
about 80% of the last 20 key presses right, we add one more letter. If he is
really struggling (under 50%), we quietly take the newest letter away again so
he can get back to feeling successful. No message, no penalty.
"""
import re
from datetime import date
from pathlib import Path

from backend import db

# Home row first, then the most useful letters, then the rest.
LETTER_ORDER = list("ASDFJKLEIRUTGHONMWYCBPQVXZ")
MIN_UNLOCKED = 2
WINDOW = 20             # how many recent key presses we look at
ADVANCE_AT = 0.8        # this accuracy or better -> add a letter
STEP_BACK_BELOW = 0.5   # worse than this -> remove the newest letter
MAX_MS = 10_000         # a longer pause means "looked away", so it is not counted as speed
LOG_KEEP = 500          # how many recent key presses we remember

_LETTER = re.compile(r"^[A-Z]$")


def accuracy(window: list[bool]) -> float:
    return sum(window) / len(window) if window else 0.0


def decide(window: list[bool], unlocked: int) -> str:
    """Return "advance", "step_back" or "stay" for the recent presses."""
    if len(window) < WINDOW:
        return "stay"  # not enough evidence yet
    acc = accuracy(window)
    if acc >= ADVANCE_AT and unlocked < len(LETTER_ORDER):
        return "advance"
    if acc < STEP_BACK_BELOW and unlocked > MIN_UNLOCKED:
        return "step_back"
    return "stay"


def letters_for(unlocked: int) -> list[str]:
    return LETTER_ORDER[:unlocked]


def _get_int(conn, key: str, default: int) -> int:
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return int(row["value"]) if row else default


def _put(conn, key: str, value) -> None:
    conn.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, str(value)),
    )


def get_letters(db_path: Path) -> dict:
    with db.connect(db_path) as conn:
        unlocked = _get_int(conn, "letters_unlocked", MIN_UNLOCKED)
    return {"unlocked": unlocked, "letters": letters_for(unlocked)}


def record_keystrokes(db_path: Path, events: list[dict], adaptive: bool = False) -> dict:
    """Save key presses, then (for Letter Land) decide whether to change the difficulty.

    Each event is {"key": target key, "correct": bool, "ms": how long it took}.
    A wrong press counts against the key the child was *supposed* to press,
    so the parent later sees which keys are hard.
    """
    change = None
    with db.connect(db_path) as conn:
        for event in events:
            key, correct = event["key"], bool(event["correct"])
            ms = min(int(event["ms"]), MAX_MS)
            row = conn.execute("SELECT attempts, correct, avg_ms FROM keystroke_stats WHERE key = ?", (key,)).fetchone()
            attempts, right, avg = (row["attempts"], row["correct"], row["avg_ms"]) if row else (0, 0, 0.0)
            new_avg = (avg * attempts + ms) / (attempts + 1)  # running average
            conn.execute(
                "INSERT INTO keystroke_stats (key, attempts, correct, avg_ms) VALUES (?, ?, ?, ?) "
                "ON CONFLICT(key) DO UPDATE SET attempts = excluded.attempts, correct = excluded.correct, avg_ms = excluded.avg_ms",
                (key, attempts + 1, right + (1 if correct else 0), new_avg),
            )
            conn.execute(
                "INSERT INTO daily_stats (day, attempts, correct) VALUES (?, 1, ?) "
                "ON CONFLICT(day) DO UPDATE SET attempts = attempts + 1, correct = correct + excluded.correct",
                (date.today().isoformat(), 1 if correct else 0),
            )
            if adaptive and _LETTER.match(key):
                conn.execute("INSERT INTO keystroke_log (key, correct, ms) VALUES (?, ?, ?)", (key, int(correct), ms))
        conn.execute("DELETE FROM keystroke_log WHERE id <= (SELECT MAX(id) FROM keystroke_log) - ?", (LOG_KEEP,))

        unlocked = _get_int(conn, "letters_unlocked", MIN_UNLOCKED)
        if adaptive:
            changed_at = _get_int(conn, "letters_changed_at", 0)
            rows = conn.execute(
                "SELECT correct FROM keystroke_log WHERE id > ? ORDER BY id DESC LIMIT ?", (changed_at, WINDOW)
            ).fetchall()
            change = decide([bool(r["correct"]) for r in rows], unlocked)
            if change != "stay":
                unlocked += 1 if change == "advance" else -1
                # Start a fresh window so the next decision uses only presses at the new level.
                latest = conn.execute("SELECT COALESCE(MAX(id), 0) FROM keystroke_log").fetchone()[0]
                _put(conn, "letters_unlocked", unlocked)
                _put(conn, "letters_changed_at", latest)
    return {"unlocked": unlocked, "letters": letters_for(unlocked), "change": None if change in (None, "stay") else change}
