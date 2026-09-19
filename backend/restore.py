"""Restoring a backup file (the JSON the parent saved in the Data tab).

A backup file is treated as untrusted input, because it may come from an email or another
computer. Nothing is copied blindly: every table, column and value is checked against what Tippy
itself could have written, unknown or invalid items are skipped (and counted), and secrets such as
the PIN can never come in this way. The replacement runs in one database transaction, so it either
completes fully or changes nothing, and a safety copy of the current data is kept first.
"""
import re
import sqlite3
from contextlib import closing
from datetime import date, datetime
from pathlib import Path

from backend import bank, db, difficulty, progress

MAX_BACKUP_BYTES = 5 * 1024 * 1024
MAX_ROWS = 20_000

# What comes back from a backup. Everything else (llm_usage, sessions, the cache, ...) is ignored.
DATA_TABLES = ("progress", "stickers", "keystroke_stats", "daily_stats", "play_time", "play_days")
# Settings that are known but deliberately not restored (internal counters, household secrets): ignored without counting.
IGNORED_SETTINGS = {"letters_changed_at", "weekly_summary", "pin_hash", "openrouter_model"}
_KEY = re.compile(r"^([A-ZÄÖÜ]|[0-9]|SPACE|ENTER|BACKSPACE|SHIFT)$")


class RestoreError(ValueError):
    """The file cannot be used. The message is safe to show to the parent."""


def _int(value, low: int, high: int):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or int(value) != value:
        return None
    return int(value) if low <= value <= high else None


def _day(value):
    try:
        return date.fromisoformat(value).isoformat() if isinstance(value, str) else None
    except ValueError:
        return None


def _name_ok(value, longest: int, allow_space: bool) -> bool:
    return isinstance(value, str) and len(value) <= longest and all(c.isalpha() or (allow_space and c in " '-") for c in value)


# Settings a child owns. Each has a check that returns the cleaned text, or None to skip it.
def _setting(key: str, value):
    text = str(value) if not isinstance(value, bool) else ("1" if value else "0")
    checks = {
        "language": lambda: text if text in ("en", "de") else None,
        "keyboard_layout": lambda: text if text in ("qwerty", "qwertz") else None,
        "letter_case": lambda: text if text in ("upper", "lower") else None,
        "voice_on": lambda: text if text in ("0", "1") else None,
        "sound_on": lambda: text if text in ("0", "1") else None,
        "ask_tippy": lambda: text if text in ("0", "1") else None,
        "reduce_motion": lambda: text if text in ("0", "1") else None,
        "has_numpad": lambda: text if text in ("0", "1") else None,
        "child_name": lambda: text if _name_ok(text, 20, True) else None,
        "favorite_word": lambda: text if _name_ok(text, 15, False) else None,
        "session_minutes": lambda: str(n) if (n := _int(_num(text), 0, 60)) is not None else None,
        "daily_limit_minutes": lambda: str(n) if (n := _int(_num(text), 0, 480)) is not None else None,
        "font_scale": lambda: text if text in ("1", "1.0", "1.125", "1.25") else None,
        "letters_unlocked": lambda: str(n) if (n := _int(_num(text), difficulty.MIN_UNLOCKED, len(difficulty.LETTER_ORDER))) is not None else None,
        "unlocked_worlds": lambda: text if text == "all" or all(w in progress.WORLD_ORDER for w in text.split(",") if w) else None,
    }
    check = checks.get(key)
    return check() if check else None


def _num(text):
    try:
        return float(text)
    except ValueError:
        return None


def prepare(backup) -> dict:
    """Validate a parsed backup and return a plan: what will be restored, plus counts of what was skipped."""
    if not isinstance(backup, dict) or backup.get("app") != "tippy" or not isinstance(backup.get("tables"), dict):
        raise RestoreError("bad-file")
    tables = backup["tables"]
    plan = {"settings": {}, "interests": None, "rows": {t: [] for t in DATA_TABLES}, "skipped": 0}
    ids = {s["id"] for s in progress.CATALOG}

    for name in [*DATA_TABLES, "settings", "child_profile"]:
        rows = tables.get(name, [])
        if not isinstance(rows, list) or len(rows) > MAX_ROWS or not all(isinstance(r, dict) for r in rows):
            raise RestoreError("bad-file")

    for row in tables.get("settings", []):
        if row.get("key") in IGNORED_SETTINGS:
            continue
        cleaned = _setting(str(row.get("key")), row.get("value"))
        if cleaned is None:
            plan["skipped"] += 1
        else:
            plan["settings"][str(row["key"])] = cleaned

    for row in tables.get("child_profile", []):
        chosen = [x for x in str(row.get("interests", "")).split(",") if x in bank.THEMES]
        if chosen:
            plan["interests"] = ",".join(dict.fromkeys(chosen))

    def keep(table: str, values: tuple | None) -> None:
        if values is None:
            plan["skipped"] += 1
        else:
            plan["rows"][table].append(values)

    for r in tables.get("progress", []):
        world, level, stars = r.get("world"), r.get("level"), _int(r.get("stars"), 0, 3)
        ok = world in progress.LEVEL_COUNTS and _int(level, 1, progress.max_level(world)) and stars is not None and r.get("status") == "done"
        keep("progress", (world, int(level), "done", stars) if ok else None)
    for r in tables.get("stickers", []):
        at = r.get("earned_at")
        keep("stickers", (r["id"], at[:40]) if r.get("id") in ids and isinstance(at, str) else None)
    for r in tables.get("keystroke_stats", []):
        attempts, correct = _int(r.get("attempts"), 0, 10**7), _int(r.get("correct"), 0, 10**7)
        avg = r.get("avg_ms")
        ok = isinstance(r.get("key"), str) and _KEY.match(r["key"]) and attempts is not None and correct is not None \
            and correct <= attempts and isinstance(avg, (int, float)) and not isinstance(avg, bool) and 0 <= avg <= 10**7
        keep("keystroke_stats", (r["key"], attempts, correct, float(avg)) if ok else None)
    for r in tables.get("daily_stats", []):
        day, attempts, correct = _day(r.get("day")), _int(r.get("attempts"), 0, 10**7), _int(r.get("correct"), 0, 10**7)
        keep("daily_stats", (day, attempts, correct) if day and attempts is not None and correct is not None and correct <= attempts else None)
    for r in tables.get("play_time", []):
        day, seconds = _day(r.get("day")), _int(r.get("seconds"), 0, 86_400)
        keep("play_time", (day, seconds) if day and seconds is not None else None)
    for r in tables.get("play_days", []):
        day = _day(r.get("day"))
        keep("play_days", (day,) if day else None)

    if not plan["settings"] and plan["interests"] is None and not any(plan["rows"].values()):
        raise RestoreError("empty")
    return plan


def suggested_name(plan: dict) -> str:
    return plan["settings"].get("child_name", "")


def apply(db_path: Path, plan: dict) -> dict:
    """Replace the child's data with the plan. Returns what was restored and where the safety copy is."""
    safety = db_path.with_name(f"{db_path.stem}.before-restore-{datetime.now():%Y%m%d-%H%M%S}.db")
    with closing(sqlite3.connect(db_path)) as source, closing(sqlite3.connect(safety)) as target:
        source.backup(target)                                     # a consistent copy of the current data
    with db.connect(db_path) as conn:                             # one transaction: all or nothing
        for table in (*DATA_TABLES, "keystroke_log"):
            conn.execute(f"DELETE FROM {table}")
        conn.execute("DELETE FROM settings WHERE key IN ('letters_unlocked', 'letters_changed_at', 'unlocked_worlds', 'weekly_summary')")
        for key, value in plan["settings"].items():
            conn.execute("INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value", (key, value))
        if "letters_unlocked" in plan["settings"]:
            conn.execute("INSERT INTO settings (key, value) VALUES ('letters_changed_at', '0') ON CONFLICT(key) DO UPDATE SET value = '0'")
        if plan["interests"]:
            conn.execute("UPDATE child_profile SET interests = ? WHERE id = 1", (plan["interests"],))
        sql = {
            "progress": "INSERT INTO progress (world, level, status, stars) VALUES (?, ?, ?, ?)",
            "stickers": "INSERT INTO stickers (id, earned_at) VALUES (?, ?)",
            "keystroke_stats": "INSERT INTO keystroke_stats (key, attempts, correct, avg_ms) VALUES (?, ?, ?, ?)",
            "daily_stats": "INSERT INTO daily_stats (day, attempts, correct) VALUES (?, ?, ?)",
            "play_time": "INSERT INTO play_time (day, seconds) VALUES (?, ?)",
            "play_days": "INSERT INTO play_days (day) VALUES (?)",
        }
        for table, statement in sql.items():
            conn.executemany(statement.replace("INSERT INTO", "INSERT OR REPLACE INTO"), plan["rows"][table])   # duplicates in the file: last one wins
    return {"restored": {t: len(rows) for t, rows in plan["rows"].items()}, "skipped": plan["skipped"], "safety_copy": safety.name}
