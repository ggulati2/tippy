"""SQLite storage. Uses only Python's built-in sqlite3 module.

All tables are created with "IF NOT EXISTS", so starting the app is always safe
and no separate migration tool is needed. If a table changes later, add a new
column with ALTER TABLE inside init_db().
"""
import logging
import sqlite3
from datetime import datetime
from pathlib import Path

log = logging.getLogger("tippy.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS child_profile (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    first_name TEXT NOT NULL DEFAULT '',
    interests TEXT NOT NULL DEFAULT 'animals,space,dinosaurs,vehicles'
);
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    seconds_played INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS keystroke_stats (
    key TEXT PRIMARY KEY,
    attempts INTEGER NOT NULL DEFAULT 0,
    correct INTEGER NOT NULL DEFAULT 0,
    avg_ms REAL NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS keystroke_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT NOT NULL,
    correct INTEGER NOT NULL,
    ms INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS progress (
    world TEXT NOT NULL,
    level INTEGER NOT NULL DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'locked',
    stars INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (world, level)
);
CREATE TABLE IF NOT EXISTS play_days (
    day TEXT PRIMARY KEY
);
CREATE TABLE IF NOT EXISTS play_time (
    day TEXT PRIMARY KEY,
    seconds INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS daily_stats (
    day TEXT PRIMARY KEY,
    attempts INTEGER NOT NULL DEFAULT 0,
    correct INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS stickers (
    id TEXT PRIMARY KEY,
    earned_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS content_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,
    level INTEGER NOT NULL,
    json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    used INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS llm_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    day TEXT NOT NULL,
    model TEXT NOT NULL,
    prompt_tokens INTEGER NOT NULL DEFAULT 0,
    completion_tokens INTEGER NOT NULL DEFAULT 0,
    est_cost_usd REAL NOT NULL DEFAULT 0
);
"""

# Values the parent can change. Used when nothing has been saved yet.
DEFAULT_SETTINGS = {
    "language": "en",
    "keyboard_layout": "qwerty",  # or "qwertz"
    "voice_on": "1",
    "sound_on": "1",
    "letter_case": "upper",  # or "lower"
    "child_name": "",       # set by the parent; used only in the browser
    "favorite_word": "",
    "session_minutes": "10",       # Tippy suggests a break after this many minutes (0 = never)
    "daily_limit_minutes": "0",    # 0 = no daily limit
    "font_scale": "1",             # text size: 1, 1.125 or 1.25
    "reduce_motion": "0",          # 1 = no animations
    "ask_tippy": "0",              # the picture Q&A is off unless the parent turns it on
    "openrouter_model": "",        # parent override; empty = use the model from .env
    "weekly_summary": "",          # cached weekly summary (JSON), parent area only
}


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Path, default_language: str = "en") -> None:
    """Create the tables if needed. A damaged database file (for example after a power cut) is moved
    aside, not deleted, and Tippy starts fresh, so the app never gets stuck unable to start."""
    try:
        _init_db(db_path, default_language)
    except sqlite3.DatabaseError:
        aside = db_path.with_name(f"{db_path.name}.damaged-{datetime.now():%Y%m%d-%H%M%S}")
        log.error("Database is damaged. Moving it to %s and starting fresh.", aside)
        db_path.rename(aside)
        _init_db(db_path, default_language)


def _init_db(db_path: Path, default_language: str = "en") -> None:
    with connect(db_path) as conn:
        conn.executescript(SCHEMA)
        conn.execute("INSERT OR IGNORE INTO child_profile (id) VALUES (1)")
        defaults = dict(DEFAULT_SETTINGS, language=default_language)
        for key, value in defaults.items():
            conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, value))
        # A German UI should start with the German keyboard shape.
        if default_language == "de":
            conn.execute(
                "UPDATE settings SET value = 'qwertz' WHERE key = 'keyboard_layout' "
                "AND NOT EXISTS (SELECT 1 FROM sessions)"
            )


def get_settings(db_path: Path) -> dict:
    with connect(db_path) as conn:
        rows = conn.execute("SELECT key, value FROM settings").fetchall()
    return {row["key"]: row["value"] for row in rows}


def set_setting(db_path: Path, key: str, value: str) -> None:
    with connect(db_path) as conn:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )


# Settings the child's browser may see. Everything else (summary text, model,
# progress counters...) stays on the server and is only shown in the parent area.
CHILD_SETTINGS = ("language", "keyboard_layout", "voice_on", "sound_on", "letter_case", "child_name",
                  "favorite_word", "session_minutes", "daily_limit_minutes", "ask_tippy",
                  "font_scale", "reduce_motion")
